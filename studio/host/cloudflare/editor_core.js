import { DOMParser, XMLSerializer } from '@xmldom/xmldom';
import { SESSION_TTL_SECONDS, validHostKey } from './core.js';

export const EDITOR_RECORD_SCHEMA = 'ppt-master-hosted-official-svg-editor-session/v1';
export const EDITOR_CAPTURE_SCHEMA = 'ppt-master-hosted-official-svg-editor-capture/v1';
const CHUNK_SIZE = 96 * 1024;
const MAX_EDIT_TEXT = 5000;
const MAX_ATTR_VALUE = 256;
const SAFE_NAME_RE = /^[A-Za-z0-9_.-]+\.svg$/;
const SAFE_ASSET_RE = /^[A-Za-z0-9_.\-/]+$/;
const SAFE_ATTR_RE = /^[A-Za-z_][A-Za-z0-9_.:-]*$/;
const PROTECTED_ATTRS = new Set(['id', 'class', 'data-edit-target', 'data-edit-annotation']);

function assertObject(value, message) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(message);
  return value;
}

function safeSlideName(value) {
  const name = String(value || '');
  if (!SAFE_NAME_RE.test(name) || name.includes('..')) throw new Error('invalid SVG slide name');
  return name;
}

function safeAssetPath(kind, value) {
  const path = String(value || '');
  if (!['images', 'assets'].includes(kind)) throw new Error('invalid asset kind');
  if (!path || !SAFE_ASSET_RE.test(path) || path.startsWith('/') || path.includes('..')) {
    throw new Error('invalid asset path');
  }
  return `${kind}/${path}`;
}

function parseSvg(svg) {
  const errors = [];
  const parser = new DOMParser({
    errorHandler: {
      warning() {},
      error(message) { errors.push(String(message)); },
      fatalError(message) { errors.push(String(message)); },
    },
  });
  const doc = parser.parseFromString(String(svg || ''), 'image/svg+xml');
  const root = doc?.documentElement;
  if (!root || String(root.localName || root.nodeName).toLowerCase() !== 'svg' || errors.length) {
    throw new Error(`invalid SVG${errors.length ? `: ${errors[0]}` : ''}`);
  }
  return doc;
}

function elements(root) {
  const out = [];
  function visit(node) {
    if (node?.nodeType === 1) out.push(node);
    for (let child = node?.firstChild; child; child = child.nextSibling) visit(child);
  }
  visit(root);
  return out;
}

function prepareSvg(svg) {
  const doc = parseSvg(svg);
  const list = elements(doc.documentElement);
  for (const el of list) {
    const id = el.getAttribute?.('id') || '';
    if (id.startsWith('_edit_')) el.removeAttribute('id');
  }
  let counter = 0;
  for (const el of list.slice(1)) {
    if (!el.getAttribute('id')) el.setAttribute('id', `_edit_${counter++}`);
  }
  return new XMLSerializer().serializeToString(doc);
}

function findById(doc, id) {
  return elements(doc.documentElement).find(el => el.getAttribute?.('id') === id) || null;
}

function localName(node) {
  return String(node?.localName || node?.nodeName || '').replace(/^.*:/, '').toLowerCase();
}

function hasTspanChild(el) {
  for (let child = el.firstChild; child; child = child.nextSibling) {
    if (child.nodeType === 1 && localName(child) === 'tspan') return true;
  }
  return false;
}

function validateAttrs(attrs, target) {
  if (!attrs || typeof attrs !== 'object' || Array.isArray(attrs)) return;
  for (const [key, raw] of Object.entries(attrs)) {
    const lower = key.toLowerCase();
    if (!SAFE_ATTR_RE.test(key) || PROTECTED_ATTRS.has(lower) || lower.startsWith('on') || lower === 'href' || lower.endsWith(':href')) {
      throw new Error(`attribute not editable: ${key}`);
    }
    if (raw === null) continue;
    if (typeof raw !== 'string' || raw.length > MAX_ATTR_VALUE) throw new Error(`invalid attribute value: ${key}`);
    if (/[<>\"]/.test(raw) || /javascript\s*:|data\s*:|url\s*\(/i.test(raw)) {
      throw new Error(`unsafe attribute value: ${key}`);
    }
    if (!target.hasAttribute(key) && !['fill', 'stroke', 'opacity', 'font-size', 'font-family', 'font-weight', 'text-anchor', 'x', 'y', 'transform'].includes(lower)) {
      throw new Error(`attribute does not exist on element: ${key}`);
    }
  }
}

function applyEdit(doc, edit) {
  const payload = assertObject(edit, 'edit payload object required');
  const elementId = String(payload.element_id || '');
  const target = findById(doc, elementId);
  if (!target) throw new Error(`element not found: ${elementId}`);

  if (payload.promote_tspan && typeof payload.promote_tspan === 'object') {
    const x = payload.promote_tspan.x;
    const y = payload.promote_tspan.y;
    if (x !== undefined) target.setAttribute('x', String(x));
    if (y !== undefined) target.setAttribute('y', String(y));
    target.removeAttribute('dx');
    target.removeAttribute('dy');
  }

  if (payload.text !== undefined) {
    const text = String(payload.text ?? '');
    if (text.length > MAX_EDIT_TEXT) throw new Error('edit text too long');
    if (hasTspanChild(target)) throw new Error('cannot replace text on element with tspan children');
    while (target.firstChild) target.removeChild(target.firstChild);
    target.appendChild(doc.createTextNode(text));
  }

  if (payload.attrs !== undefined) {
    validateAttrs(payload.attrs, target);
    for (const [key, value] of Object.entries(payload.attrs || {})) {
      if (value === null) target.removeAttribute(key);
      else target.setAttribute(key, String(value));
    }
  }
}

function applyAnnotations(doc, annotations) {
  for (const el of elements(doc.documentElement)) {
    el.removeAttribute?.('data-edit-target');
    el.removeAttribute?.('data-edit-annotation');
  }
  for (const [elementId, annotation] of Object.entries(annotations || {})) {
    const target = findById(doc, elementId);
    if (!target) continue;
    target.setAttribute('data-edit-target', 'true');
    target.setAttribute('data-edit-annotation', String(annotation));
  }
}

export function renderEditorSvg(baseSvg, edits = [], annotations = {}) {
  const doc = parseSvg(prepareSvg(baseSvg));
  for (const edit of edits) applyEdit(doc, edit);
  applyAnnotations(doc, annotations);
  return new XMLSerializer().serializeToString(doc);
}

async function writeLarge(storage, prefix, text, oldChunks = 0) {
  const value = String(text ?? '');
  const chunks = [];
  for (let i = 0; i < value.length; i += CHUNK_SIZE) chunks.push(value.slice(i, i + CHUNK_SIZE));
  if (!chunks.length) chunks.push('');
  for (let i = 0; i < chunks.length; i++) await storage.put(`${prefix}:${i}`, chunks[i]);
  for (let i = chunks.length; i < oldChunks; i++) await storage.delete(`${prefix}:${i}`);
  return chunks.length;
}

async function readLarge(storage, prefix, count) {
  const parts = [];
  for (let i = 0; i < Number(count || 0); i++) {
    const part = await storage.get(`${prefix}:${i}`);
    if (typeof part !== 'string') throw new Error(`missing hosted chunk ${prefix}:${i}`);
    parts.push(part);
  }
  return parts.join('');
}

function nowIso(now) { return new Date(now()).toISOString(); }

export class EditorSessionStore {
  constructor(storage, now = () => Date.now()) {
    this.storage = storage;
    this.now = now;
  }

  async _load({ allowClosed = true } = {}) {
    const record = await this.storage.get('editor_record');
    if (!record) return null;
    if (Date.parse(record.expires_at) <= this.now()) {
      await this.storage.deleteAll();
      return null;
    }
    if (!allowClosed && record.status === 'closed') return null;
    return record;
  }

  async _checkHost(hostKey) {
    const stored = await this.storage.get('editor_host_key');
    return validHostKey(hostKey) && hostKey === stored;
  }

  async create(payload, hostKey) {
    assertObject(payload, 'editor session payload required');
    if (!/^[0-9a-f]{40}$/.test(String(payload.harness_commit || ''))) throw new Error('harness_commit must be full 40-hex commit');
    if (!validHostKey(hostKey)) throw new Error('valid host key required');
    if (await this._load()) return { ok: false, status: 409, error: 'editor session already exists' };
    const created = this.now();
    const expires = created + SESSION_TTL_SECONDS * 1000;
    const record = {
      schema: EDITOR_RECORD_SCHEMA,
      harness_commit: payload.harness_commit,
      live: payload.live !== false,
      status: 'open',
      slides: {},
      assets: {},
      captures: [],
      created_at: new Date(created).toISOString(),
      updated_at: new Date(created).toISOString(),
      expires_at: new Date(expires).toISOString(),
    };
    await this.storage.put('editor_record', record);
    await this.storage.put('editor_host_key', hostKey);
    await this.storage.setAlarm(expires);
    return { ok: true, record };
  }

  async get() {
    const record = await this._load();
    return record ? { ok: true, record } : { ok: false, status: 404, error: 'editor session missing or expired' };
  }

  async upsertSlide(hostKey, nameValue, payload) {
    const record = await this._load({ allowClosed: false });
    if (!record) return { ok: false, status: 404, error: 'editor session missing, closed or expired' };
    if (!await this._checkHost(hostKey)) return { ok: false, status: 403, error: 'invalid host key' };
    const name = safeSlideName(nameValue);
    const body = assertObject(payload, 'slide payload object required');
    const svg = prepareSvg(String(body.svg || ''));
    const previous = record.slides[name] || {};
    const prefix = `editor:slide:${name}`;
    const chunks = await writeLarge(this.storage, prefix, svg, previous.chunks || 0);
    record.slides[name] = {
      chunks,
      mtime: Number.isFinite(Number(body.mtime)) ? Number(body.mtime) : this.now() / 1000,
      ordinal: Number.isFinite(Number(body.ordinal)) ? Number(body.ordinal) : (previous.ordinal ?? Object.keys(record.slides).length),
      annotations: body.reset_state ? {} : (previous.annotations || {}),
      annotation_ops: body.reset_state ? [] : (previous.annotation_ops || []),
      edits: body.reset_state ? [] : (previous.edits || []),
    };
    record.status = 'open';
    record.updated_at = nowIso(this.now);
    await this.storage.put('editor_record', record);
    return { ok: true, slide: { name, mtime: record.slides[name].mtime } };
  }

  async upsertAsset(hostKey, kind, pathValue, payload) {
    const record = await this._load({ allowClosed: false });
    if (!record) return { ok: false, status: 404, error: 'editor session missing, closed or expired' };
    if (!await this._checkHost(hostKey)) return { ok: false, status: 403, error: 'invalid host key' };
    const key = safeAssetPath(kind, pathValue);
    const body = assertObject(payload, 'asset payload object required');
    const base64 = String(body.base64 || '');
    if (!/^[A-Za-z0-9+/=\r\n]*$/.test(base64)) return { ok: false, status: 400, error: 'asset must be base64' };
    const previous = record.assets[key] || {};
    const chunks = await writeLarge(this.storage, `editor:asset:${key}`, base64, previous.chunks || 0);
    record.assets[key] = { chunks, content_type: String(body.content_type || 'application/octet-stream') };
    record.updated_at = nowIso(this.now);
    await this.storage.put('editor_record', record);
    return { ok: true, asset: key };
  }

  async getAsset(kind, pathValue) {
    const record = await this._load();
    if (!record) return { ok: false, status: 404, error: 'editor session missing or expired' };
    const key = safeAssetPath(kind, pathValue);
    const meta = record.assets[key];
    if (!meta) return { ok: false, status: 404, error: 'asset missing' };
    const base64 = await readLarge(this.storage, `editor:asset:${key}`, meta.chunks);
    return { ok: true, base64, content_type: meta.content_type };
  }

  async listSlides() {
    const record = await this._load();
    if (!record) return { ok: false, status: 404, error: 'editor session missing or expired' };
    const slides = Object.entries(record.slides)
      .sort((a, b) => (a[1].ordinal ?? 0) - (b[1].ordinal ?? 0) || a[0].localeCompare(b[0]))
      .map(([name, meta]) => ({ name, ok: true, mtime: meta.mtime, annotation_count: Object.keys(meta.annotations || {}).length }));
    return { ok: true, value: { slides } };
  }

  async getSlide(nameValue) {
    const record = await this._load();
    if (!record) return { ok: false, status: 404, error: 'editor session missing or expired' };
    const name = safeSlideName(nameValue);
    const meta = record.slides[name];
    if (!meta) return { ok: false, status: 404, error: 'slide missing' };
    const base = await readLarge(this.storage, `editor:slide:${name}`, meta.chunks);
    let content;
    try { content = renderEditorSvg(base, meta.edits || [], meta.annotations || {}); }
    catch (error) { return { ok: false, status: 400, error: String(error?.message || error) }; }
    return {
      ok: true,
      value: {
        content,
        annotations: Object.entries(meta.annotations || {}).map(([element_id, annotation]) => ({ element_id, annotation })),
        warnings: [],
        mtime: meta.mtime,
        undo_depth: (meta.edits || []).length,
      },
    };
  }

  async annotate(nameValue, payload) {
    const record = await this._load({ allowClosed: false });
    if (!record) return { ok: false, status: 404, error: 'editor session missing, closed or expired' };
    const name = safeSlideName(nameValue);
    const meta = record.slides[name];
    if (!meta) return { ok: false, status: 404, error: 'slide missing' };
    const body = assertObject(payload, 'annotation payload required');
    const elementId = String(body.element_id || '');
    const annotation = String(body.annotation || '').trim();
    if (!elementId || !annotation) return { ok: false, status: 400, error: 'element_id and annotation required' };
    meta.annotations ||= {};
    meta.annotation_ops ||= [];
    meta.annotations[elementId] = annotation;
    meta.annotation_ops.push({ action: 'set', element_id: elementId, annotation });
    record.updated_at = nowIso(this.now);
    await this.storage.put('editor_record', record);
    return { ok: true, value: { status: 'ok', annotations_count: Object.keys(meta.annotations).length } };
  }

  async deleteAnnotation(nameValue, elementIdValue) {
    const record = await this._load({ allowClosed: false });
    if (!record) return { ok: false, status: 404, error: 'editor session missing, closed or expired' };
    const name = safeSlideName(nameValue);
    const meta = record.slides[name];
    if (!meta) return { ok: false, status: 404, error: 'slide missing' };
    const elementId = String(elementIdValue || '');
    meta.annotations ||= {};
    meta.annotation_ops ||= [];
    delete meta.annotations[elementId];
    meta.annotation_ops.push({ action: 'delete', element_id: elementId });
    record.updated_at = nowIso(this.now);
    await this.storage.put('editor_record', record);
    return { ok: true, value: { status: 'ok', annotations_count: Object.keys(meta.annotations).length } };
  }

  async edit(nameValue, payload) {
    const record = await this._load({ allowClosed: false });
    if (!record) return { ok: false, status: 404, error: 'editor session missing, closed or expired' };
    const name = safeSlideName(nameValue);
    const meta = record.slides[name];
    if (!meta) return { ok: false, status: 404, error: 'slide missing' };
    const body = structuredClone(assertObject(payload, 'edit payload required'));
    const base = await readLarge(this.storage, `editor:slide:${name}`, meta.chunks);
    try { renderEditorSvg(base, [...(meta.edits || []), body], meta.annotations || {}); }
    catch (error) { return { ok: false, status: 400, error: String(error?.message || error) }; }
    meta.edits ||= [];
    meta.edits.push(body);
    record.updated_at = nowIso(this.now);
    await this.storage.put('editor_record', record);
    return { ok: true, value: { status: 'ok', undo_depth: meta.edits.length } };
  }

  async undo(nameValue) {
    const record = await this._load({ allowClosed: false });
    if (!record) return { ok: false, status: 404, error: 'editor session missing, closed or expired' };
    const name = safeSlideName(nameValue);
    const meta = record.slides[name];
    if (!meta) return { ok: false, status: 404, error: 'slide missing' };
    meta.edits ||= [];
    if (!meta.edits.length) return { ok: true, value: { status: 'empty', undo_depth: 0 } };
    meta.edits.pop();
    record.updated_at = nowIso(this.now);
    await this.storage.put('editor_record', record);
    return { ok: true, value: { status: 'ok', undo_depth: meta.edits.length } };
  }

  async saveAll() {
    const record = await this._load({ allowClosed: false });
    if (!record) return { ok: false, status: 404, error: 'editor session missing, closed or expired' };
    const changes = [];
    for (const [name, meta] of Object.entries(record.slides)) {
      const edits = meta.edits || [];
      const annotationOps = meta.annotation_ops || [];
      if (!edits.length && !annotationOps.length) continue;
      const base = await readLarge(this.storage, `editor:slide:${name}`, meta.chunks);
      const rendered = renderEditorSvg(base, edits, meta.annotations || {});
      meta.chunks = await writeLarge(this.storage, `editor:slide:${name}`, rendered, meta.chunks || 0);
      meta.mtime = this.now() / 1000;
      changes.push({
        slide: name,
        direct_edits: structuredClone(edits),
        annotation_ops: structuredClone(annotationOps),
        annotations_snapshot: structuredClone(meta.annotations || {}),
      });
      meta.edits = [];
      meta.annotation_ops = [];
    }
    const capturedAt = nowIso(this.now);
    const capture = {
      schema: EDITOR_CAPTURE_SCHEMA,
      status: 'captured-not-applied',
      harness_status: 'not-validated',
      captured_at: capturedAt,
      changes,
    };
    record.captures.push(capture);
    record.status = 'waiting-agent';
    record.updated_at = capturedAt;
    await this.storage.put('editor_record', record);
    return { ok: true, value: { status: 'ok', hosted_status: 'captured-not-applied', modified: changes.map(x => x.slide), failures: [] } };
  }

  async getCaptured() {
    const record = await this._load();
    if (!record) return { ok: false, status: 404, error: 'editor session missing or expired' };
    return {
      ok: true,
      value: {
        schema: 'ppt-master-hosted-official-svg-editor-captures/v1',
        status: record.captures.length ? 'captured-not-applied' : 'no-capture',
        harness_status: 'not-validated',
        harness_commit: record.harness_commit,
        session_status: record.status,
        captures: record.captures,
      },
    };
  }

  async close(reason = 'exit-preview') {
    const record = await this._load();
    if (!record) return { ok: false, status: 404, error: 'editor session missing or expired' };
    record.status = 'closed';
    record.closed_reason = String(reason || 'exit-preview');
    record.updated_at = nowIso(this.now);
    await this.storage.put('editor_record', record);
    return { ok: true, record };
  }
}
