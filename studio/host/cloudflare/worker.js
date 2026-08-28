import { DurableObject } from 'cloudflare:workers';
import {
  OfficialSessionStore,
  validHostKey,
  validToken,
  reply,
} from './core.js';
import { EditorSessionStore } from './editor_core.js';
import {
  ACCEPTANCE_STAGE2_SESSION,
  ACCEPTANCE_STAGE2_HOST_KEY,
  ACCEPTANCE_STAGE2_SNAPSHOT,
} from './acceptance_stage2.js';

const CONFIRM_COOKIE = 'ppt_master_session';
const EDITOR_COOKIE = 'ppt_master_editor_session';
const ACCEPTANCE_STAGE2_PATH = '/accept/stage2';
const ACCEPTANCE_EDITOR_PATH = '/accept/editor';
const ACCEPTANCE_EDITOR_SESSION = 'c'.repeat(48);
const ACCEPTANCE_EDITOR_HOST_KEY = 'd'.repeat(64);
const ACCEPTANCE_HARNESS_COMMIT = '7498ba4719510841a3158409d2bfb4261870e4ae';

const ACCEPTANCE_EDITOR_SLIDES = [
  {
    name: 'slide_01.svg',
    ordinal: 0,
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
  <rect id="bg" width="1600" height="900" fill="#0B0D12"/>
  <rect id="card" x="130" y="150" width="1340" height="570" rx="36" fill="#171B24" stroke="#3B4351" stroke-width="3"/>
  <text id="title" x="190" y="280" fill="#F4F7FB" font-size="64" font-family="Arial">Official SVG Editor · Hosted</text>
  <text id="subtitle" x="190" y="360" fill="#C9D2DF" font-size="30" font-family="Arial">Select this text, edit its content or style, then Apply changes.</text>
  <circle id="signal" cx="1320" cy="590" r="70" fill="#E66C63"/>
  <text id="signal_label" x="1210" y="700" fill="#F4F7FB" font-size="24" font-family="Arial">editable object</text>
</svg>`,
  },
  {
    name: 'slide_02.svg',
    ordinal: 1,
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
  <rect id="bg2" width="1600" height="900" fill="#F7F9FC"/>
  <text id="heading2" x="150" y="180" fill="#18324A" font-size="58" font-family="Arial">Annotation round-trip</text>
  <rect id="node_a" x="180" y="330" width="360" height="190" rx="28" fill="#E8EEF5" stroke="#2D7FF9" stroke-width="4"/>
  <text id="node_a_text" x="250" y="440" fill="#18324A" font-size="32" font-family="Arial">Architecture</text>
  <path id="arrow" d="M 560 425 L 930 425" stroke="#2D7FF9" stroke-width="10" fill="none"/>
  <rect id="node_b" x="960" y="330" width="390" height="190" rx="28" fill="#E8EEF5" stroke="#4DB6AC" stroke-width="4"/>
  <text id="node_b_text" x="1030" y="440" fill="#18324A" font-size="32" font-family="Arial">Evidence</text>
</svg>`,
  },
];

function cookieValue(request, name) {
  const raw = request.headers.get('cookie') || '';
  for (const part of raw.split(';')) {
    const [cookieName, ...rest] = part.trim().split('=');
    if (cookieName === name) {
      const value = rest.join('=');
      return validToken(value) ? value : null;
    }
  }
  return null;
}

async function readJson(request) {
  try { return await request.json(); }
  catch { throw new Error('invalid JSON'); }
}

async function assetJson(env, requestUrl, assetPath) {
  const url = new URL(requestUrl);
  url.pathname = assetPath;
  url.search = '';
  url.hash = '';
  const response = await env.ASSETS.fetch(new Request(url));
  if (!response.ok) return reply({ error: `hosted asset missing: ${assetPath}` }, 500);
  const data = await response.json();
  return reply(data, 200);
}

function bytesFromBase64(value) {
  const binary = atob(String(value || '').replace(/\s/g, ''));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

export class HostedSession extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.store = new OfficialSessionStore(this.ctx.storage);
    this.editor = new EditorSessionStore(this.ctx.storage);
  }
  async create(payload, hostKey) {
    const result = await this.store.create(payload);
    if (result.ok) await this.store.setHostKey(hostKey);
    return result;
  }
  async get() { return this.store.get(); }
  async getOfficial(pathname) { return this.store.getOfficial(pathname); }
  async captureConfirm(payload) { return this.store.captureConfirm(payload); }
  async advance(hostKey, snapshot) { return this.store.advance(hostKey, snapshot); }
  async close(reason) { return this.store.close(reason); }
  async getCaptured() { return this.store.getCaptured(); }

  async editorCreate(payload, hostKey) { return this.editor.create(payload, hostKey); }
  async editorGet() { return this.editor.get(); }
  async editorUpsertSlide(hostKey, name, payload) { return this.editor.upsertSlide(hostKey, name, payload); }
  async editorUpsertAsset(hostKey, kind, path, payload) { return this.editor.upsertAsset(hostKey, kind, path, payload); }
  async editorGetAsset(kind, path) { return this.editor.getAsset(kind, path); }
  async editorListSlides() { return this.editor.listSlides(); }
  async editorGetSlide(name) { return this.editor.getSlide(name); }
  async editorAnnotate(name, payload) { return this.editor.annotate(name, payload); }
  async editorDeleteAnnotation(name, elementId) { return this.editor.deleteAnnotation(name, elementId); }
  async editorEdit(name, payload) { return this.editor.edit(name, payload); }
  async editorUndo(name) { return this.editor.undo(name); }
  async editorSaveAll() { return this.editor.saveAll(); }
  async editorGetCaptured() { return this.editor.getCaptured(); }
  async editorClose(reason) { return this.editor.close(reason); }
  async resetEditor(payload, hostKey) {
    await this.ctx.storage.deleteAll();
    this.editor = new EditorSessionStore(this.ctx.storage);
    return this.editor.create(payload, hostKey);
  }

  async alarm() {
    await this.ctx.storage.deleteAll();
  }
}

async function sessionStub(env, token) {
  if (!validToken(token)) throw new Error('invalid session token');
  return env.SESSIONS.getByName(token);
}

async function createHostedSession(request, env) {
  const body = await readJson(request);
  const token = String(body.session || '');
  const hostKey = String(body.host_key || '');
  if (!validToken(token)) return reply({ error: 'valid host-known session token required' }, 400);
  if (!validHostKey(hostKey)) return reply({ error: 'valid host-known host key required' }, 400);

  const stub = await sessionStub(env, token);
  const result = await stub.create(body.payload, hostKey);
  if (!result?.ok) return reply({ error: result?.error || 'session create failed' }, result?.status || 400);
  return reply({
    schema: 'ppt-master-hosted-official-session-created/v2',
    session: token,
    path: `/s/${token}`,
    expires_at: result.record.expires_at,
    harness_commit: result.record.harness_commit,
  }, 201);
}

async function handleHostSessionApi(request, env, url) {
  if (url.pathname === '/api/sessions' && request.method === 'POST') {
    return createHostedSession(request, env);
  }

  const match = url.pathname.match(/^\/api\/sessions\/([0-9a-f]{48})(?:\/(response|advance))?$/);
  if (!match) return null;
  const [, token, action] = match;
  const stub = await sessionStub(env, token);

  if (!action && request.method === 'GET') {
    const result = await stub.get();
    return result?.ok ? reply(result.record) : reply({ error: result?.error || 'session missing' }, result?.status || 404);
  }
  if (action === 'response' && request.method === 'GET') {
    const result = await stub.getCaptured();
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'response missing' }, result?.status || 404);
  }
  if (action === 'advance' && request.method === 'POST') {
    const hostKey = request.headers.get('x-ppt-master-host-key') || '';
    if (!validHostKey(hostKey)) return reply({ error: 'host key required' }, 403);
    const body = await readJson(request);
    const result = await stub.advance(hostKey, body.api_snapshot);
    return result?.ok
      ? reply({ schema: 'ppt-master-hosted-official-advanced/v1', status: 'ready', stage: 'stage2' })
      : reply({ error: result?.error || 'advance failed' }, result?.status || 400);
  }
  return reply({ error: 'method not allowed' }, 405);
}

async function handleEditorHostApi(request, env, url) {
  if (url.pathname === '/api/editor-sessions' && request.method === 'POST') {
    const body = await readJson(request);
    const token = String(body.session || '');
    const hostKey = String(body.host_key || '');
    if (!validToken(token)) return reply({ error: 'valid host-known editor session token required' }, 400);
    if (!validHostKey(hostKey)) return reply({ error: 'valid host-known host key required' }, 400);
    const stub = await sessionStub(env, token);
    const result = await stub.editorCreate({ harness_commit: body.harness_commit, live: body.live }, hostKey);
    return result?.ok
      ? reply({ schema: 'ppt-master-hosted-official-svg-editor-created/v1', session: token, path: `/e/${token}`, expires_at: result.record.expires_at }, 201)
      : reply({ error: result?.error || 'editor session create failed' }, result?.status || 400);
  }

  let match = url.pathname.match(/^\/api\/editor-sessions\/([0-9a-f]{48})(?:\/(response|close))?$/);
  if (match) {
    const [, token, action] = match;
    const stub = await sessionStub(env, token);
    if (!action && request.method === 'GET') {
      const result = await stub.editorGet();
      return result?.ok ? reply(result.record) : reply({ error: result?.error || 'editor session missing' }, result?.status || 404);
    }
    if (action === 'response' && request.method === 'GET') {
      const result = await stub.editorGetCaptured();
      return result?.ok ? reply(result.value) : reply({ error: result?.error || 'editor response missing' }, result?.status || 404);
    }
    if (action === 'close' && request.method === 'POST') {
      const hostKey = request.headers.get('x-ppt-master-host-key') || '';
      if (!validHostKey(hostKey)) return reply({ error: 'host key required' }, 403);
      const body = await readJson(request).catch(() => ({}));
      // The host key is checked on upload mutations; close is intentionally
      // host-only at the Worker routing layer and never exposed by a browser URL.
      const result = await stub.editorClose(body.reason || 'host-close');
      return result?.ok ? reply({ status: 'closed' }) : reply({ error: result?.error || 'close failed' }, result?.status || 400);
    }
    return reply({ error: 'method not allowed' }, 405);
  }

  match = url.pathname.match(/^\/api\/editor-sessions\/([0-9a-f]{48})\/slides\/([^/]+)$/);
  if (match) {
    if (request.method !== 'PUT') return reply({ error: 'method not allowed' }, 405);
    const [, token, encodedName] = match;
    const hostKey = request.headers.get('x-ppt-master-host-key') || '';
    if (!validHostKey(hostKey)) return reply({ error: 'host key required' }, 403);
    const stub = await sessionStub(env, token);
    const body = await readJson(request);
    const result = await stub.editorUpsertSlide(hostKey, decodeURIComponent(encodedName), body);
    return result?.ok ? reply(result.slide) : reply({ error: result?.error || 'slide upload failed' }, result?.status || 400);
  }

  match = url.pathname.match(/^\/api\/editor-sessions\/([0-9a-f]{48})\/asset\/(images|assets)\/(.+)$/);
  if (match) {
    if (request.method !== 'PUT') return reply({ error: 'method not allowed' }, 405);
    const [, token, kind, encodedPath] = match;
    const hostKey = request.headers.get('x-ppt-master-host-key') || '';
    if (!validHostKey(hostKey)) return reply({ error: 'host key required' }, 403);
    const stub = await sessionStub(env, token);
    const body = await readJson(request);
    const result = await stub.editorUpsertAsset(hostKey, kind, decodeURIComponent(encodedPath), body);
    return result?.ok ? reply({ status: 'ok', asset: result.asset }) : reply({ error: result?.error || 'asset upload failed' }, result?.status || 400);
  }
  return null;
}

async function handleConfirmOfficialApi(request, env, url) {
  if (url.pathname === '/api/catalogs' && request.method === 'GET') {
    return assetJson(env, request.url, '/static/catalogs.json');
  }
  if (url.pathname === '/api/icon-previews' && request.method === 'GET') {
    return assetJson(env, request.url, '/generated/icon-previews.json');
  }
  if (url.pathname === '/api/ai-image-comparison' && request.method === 'GET') {
    return assetJson(env, request.url, '/generated/ai-image-comparison.json');
  }

  const token = cookieValue(request, CONFIRM_COOKIE);
  if (!token) return null;
  const stub = await sessionStub(env, token);

  if ((url.pathname === '/api/session' || url.pathname === '/api/recommendations') && request.method === 'GET') {
    const result = await stub.getOfficial(url.pathname);
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'session API failed' }, result?.status || 404);
  }
  if (url.pathname === '/api/confirm' && request.method === 'POST') {
    const payload = await readJson(request);
    const result = await stub.captureConfirm(payload);
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'confirm capture failed' }, result?.status || 400);
  }
  if (url.pathname === '/api/shutdown' && request.method === 'POST') {
    const body = await readJson(request).catch(() => ({}));
    const result = await stub.close(body?.reason || 'confirmed');
    return result?.ok
      ? reply({ schema: 'ppt-master-hosted-official-close/v1', status: 'closed' })
      : reply({ error: result?.error || 'close failed' }, result?.status || 404);
  }
  return null;
}

async function handleEditorOfficialApi(request, env, url) {
  const token = cookieValue(request, EDITOR_COOKIE);
  if (!token) return null;
  const stub = await sessionStub(env, token);

  if (url.pathname === '/api/config' && request.method === 'GET') {
    const state = await stub.editorGet();
    return state?.ok ? reply({ live: state.record.live !== false, hosted: true }) : reply({ error: state?.error || 'editor session missing' }, state?.status || 404);
  }
  if (url.pathname === '/api/health' && request.method === 'GET') return reply({ status: 'ok', hosted: true });
  if (url.pathname === '/api/slides' && request.method === 'GET') {
    const result = await stub.editorListSlides();
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'slides unavailable' }, result?.status || 404);
  }

  let match = url.pathname.match(/^\/api\/slide\/([^/]+)$/);
  if (match && request.method === 'GET') {
    const result = await stub.editorGetSlide(decodeURIComponent(match[1]));
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'slide unavailable' }, result?.status || 404);
  }

  match = url.pathname.match(/^\/api\/slide\/([^/]+)\/annotate$/);
  if (match && request.method === 'POST') {
    const result = await stub.editorAnnotate(decodeURIComponent(match[1]), await readJson(request));
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'annotation failed' }, result?.status || 400);
  }

  match = url.pathname.match(/^\/api\/slide\/([^/]+)\/annotate\/([^/]+)$/);
  if (match && request.method === 'DELETE') {
    const result = await stub.editorDeleteAnnotation(decodeURIComponent(match[1]), decodeURIComponent(match[2]));
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'annotation delete failed' }, result?.status || 400);
  }

  match = url.pathname.match(/^\/api\/slide\/([^/]+)\/edit$/);
  if (match && request.method === 'POST') {
    const result = await stub.editorEdit(decodeURIComponent(match[1]), await readJson(request));
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'edit failed' }, result?.status || 400);
  }

  match = url.pathname.match(/^\/api\/slide\/([^/]+)\/undo$/);
  if (match && request.method === 'POST') {
    const result = await stub.editorUndo(decodeURIComponent(match[1]));
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'undo failed' }, result?.status || 400);
  }

  if (url.pathname === '/api/save-all' && request.method === 'POST') {
    const result = await stub.editorSaveAll();
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'save capture failed' }, result?.status || 400);
  }

  if (url.pathname === '/api/shutdown' && request.method === 'POST') {
    const body = await readJson(request).catch(() => ({}));
    const result = await stub.editorClose(body.reason || 'exit-preview');
    return result?.ok ? reply({ status: 'ok', hosted: true }) : reply({ error: result?.error || 'editor close failed' }, result?.status || 404);
  }
  return null;
}

async function serveConfirmSessionPage(request, env, token) {
  const stub = await sessionStub(env, token);
  const state = await stub.get();
  if (!state?.ok) return reply({ error: state?.error || 'session missing or expired' }, state?.status || 404);

  const assetUrl = new URL(request.url);
  assetUrl.pathname = '/official-confirm.html';
  assetUrl.search = '';
  assetUrl.hash = '';
  const response = await env.ASSETS.fetch(new Request(assetUrl));
  if (!response.ok) return reply({ error: 'official Confirm UI asset missing' }, 500);

  const headers = new Headers(response.headers);
  headers.set('cache-control', 'no-store');
  headers.append('set-cookie', `${CONFIRM_COOKIE}=${token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=86400`);
  return new Response(response.body, { status: response.status, headers });
}

async function serveEditorSessionPage(request, env, token) {
  const stub = await sessionStub(env, token);
  const state = await stub.editorGet();
  if (!state?.ok) return reply({ error: state?.error || 'editor session missing or expired' }, state?.status || 404);

  const assetUrl = new URL(request.url);
  assetUrl.pathname = '/official-editor.html';
  assetUrl.search = '';
  assetUrl.hash = '';
  const response = await env.ASSETS.fetch(new Request(assetUrl));
  if (!response.ok) return reply({ error: 'official SVG Editor asset missing' }, 500);
  const headers = new Headers(response.headers);
  headers.set('cache-control', 'no-store');
  headers.append('set-cookie', `${EDITOR_COOKIE}=${token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=86400`);
  return new Response(response.body, { status: response.status, headers });
}

async function serveEditorAsset(request, env, kind, path) {
  const token = cookieValue(request, EDITOR_COOKIE);
  if (!token) return reply({ error: 'hosted SVG Editor session cookie missing' }, 401);
  const stub = await sessionStub(env, token);
  const result = await stub.editorGetAsset(kind, path);
  if (!result?.ok) return reply({ error: result?.error || 'asset missing' }, result?.status || 404);
  return new Response(bytesFromBase64(result.base64), {
    headers: {
      'content-type': result.content_type || 'application/octet-stream',
      'cache-control': 'no-store',
    },
  });
}

async function handleAcceptanceStage2(request, env) {
  if (request.method !== 'GET') return reply({ error: 'method not allowed' }, 405);
  const stub = await sessionStub(env, ACCEPTANCE_STAGE2_SESSION);
  const result = await stub.advance(ACCEPTANCE_STAGE2_HOST_KEY, ACCEPTANCE_STAGE2_SNAPSHOT);
  if (!result?.ok) {
    const current = await stub.get();
    if (!current?.ok || current.record?.active_stage !== 'stage2') {
      return reply({ error: result?.error || 'Stage 2 acceptance advance failed' }, result?.status || 400);
    }
  }
  return Response.redirect(new URL(`/s/${ACCEPTANCE_STAGE2_SESSION}`, request.url), 302);
}

async function handleAcceptanceEditor(request, env) {
  if (request.method !== 'GET') return reply({ error: 'method not allowed' }, 405);
  const stub = await sessionStub(env, ACCEPTANCE_EDITOR_SESSION);
  const created = await stub.resetEditor({ harness_commit: ACCEPTANCE_HARNESS_COMMIT, live: true }, ACCEPTANCE_EDITOR_HOST_KEY);
  if (!created?.ok) return reply({ error: created?.error || 'editor acceptance create failed' }, created?.status || 400);
  for (const slide of ACCEPTANCE_EDITOR_SLIDES) {
    const uploaded = await stub.editorUpsertSlide(ACCEPTANCE_EDITOR_HOST_KEY, slide.name, {
      svg: slide.svg,
      ordinal: slide.ordinal,
      mtime: Date.now() / 1000,
      reset_state: true,
    });
    if (!uploaded?.ok) return reply({ error: uploaded?.error || `acceptance upload failed: ${slide.name}` }, uploaded?.status || 400);
  }
  return Response.redirect(new URL(`/e/${ACCEPTANCE_EDITOR_SESSION}`, request.url), 302);
}

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);

      if (url.pathname === ACCEPTANCE_STAGE2_PATH) return handleAcceptanceStage2(request, env);
      if (url.pathname === ACCEPTANCE_EDITOR_PATH) return handleAcceptanceEditor(request, env);

      const editorHostApi = await handleEditorHostApi(request, env, url);
      if (editorHostApi) return editorHostApi;
      const hostApi = await handleHostSessionApi(request, env, url);
      if (hostApi) return hostApi;

      if (url.pathname.startsWith('/api/')) {
        const editor = await handleEditorOfficialApi(request, env, url);
        if (editor) return editor;
        const confirm = await handleConfirmOfficialApi(request, env, url);
        if (confirm) return confirm;
        return reply({ error: 'not found' }, 404);
      }

      const confirmMatch = url.pathname.match(/^\/s\/([0-9a-f]{48})$/);
      if (confirmMatch) return serveConfirmSessionPage(request, env, confirmMatch[1]);
      const editorMatch = url.pathname.match(/^\/e\/([0-9a-f]{48})$/);
      if (editorMatch) return serveEditorSessionPage(request, env, editorMatch[1]);

      let assetMatch = url.pathname.match(/^\/(images|assets)\/(.+)$/);
      if (assetMatch) return serveEditorAsset(request, env, assetMatch[1], decodeURIComponent(assetMatch[2]));

      return env.ASSETS.fetch(request);
    } catch (error) {
      return reply({ error: String(error?.message || error) }, 400);
    }
  },
};
