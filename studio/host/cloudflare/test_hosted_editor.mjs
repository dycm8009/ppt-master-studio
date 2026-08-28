import { EditorSessionStore } from './editor_core.js';

class MemoryStorage {
  constructor() { this.map = new Map(); this.alarm = null; }
  async get(key) { return this.map.get(key); }
  async put(key, value) { this.map.set(key, structuredClone(value)); }
  async delete(key) { this.map.delete(key); }
  async deleteAll() { this.map.clear(); this.alarm = null; }
  async setAlarm(value) { this.alarm = value; }
}

const SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900">
  <rect id="bg" width="1600" height="900" fill="#111111"/>
  <text id="title" x="100" y="150" fill="#ffffff">Original title</text>
  <rect x="100" y="250" width="300" height="180" fill="#333333"/>
</svg>`;

async function main() {
  const storage = new MemoryStorage();
  let now = Date.parse('2026-08-29T08:00:00Z');
  const store = new EditorSessionStore(storage, () => now);
  const hostKey = 'a'.repeat(64);

  const created = await store.create({ harness_commit: 'b'.repeat(40), live: true }, hostKey);
  if (!created.ok || created.record.status !== 'open') throw new Error('editor create failed');

  const badUpload = await store.upsertSlide('f'.repeat(64), 'slide_01.svg', { svg: SVG });
  if (badUpload.ok || badUpload.status !== 403) throw new Error('invalid editor host key accepted');

  const uploaded = await store.upsertSlide(hostKey, 'slide_01.svg', { svg: SVG, ordinal: 0, reset_state: true });
  if (!uploaded.ok) throw new Error('slide upload failed');

  const list = await store.listSlides();
  if (!list.ok || list.value.slides.length !== 1 || list.value.slides[0].name !== 'slide_01.svg') {
    throw new Error('slide roster mismatch');
  }

  const initial = await store.getSlide('slide_01.svg');
  if (!initial.ok || !initial.value.content.includes('Original title')) throw new Error('initial slide render failed');
  if (!initial.value.content.includes('_edit_0')) throw new Error('temporary editor ids were not assigned');

  const editText = await store.edit('slide_01.svg', { element_id: 'title', text: 'Hosted title' });
  if (!editText.ok || editText.value.undo_depth !== 1) throw new Error('text edit was not staged');
  const editedText = await store.getSlide('slide_01.svg');
  if (!editedText.value.content.includes('Hosted title')) throw new Error('staged text edit not visible in preview');

  const editFill = await store.edit('slide_01.svg', { element_id: 'title', attrs: { fill: '#E66C63' } });
  if (!editFill.ok || editFill.value.undo_depth !== 2) throw new Error('attribute edit was not staged');
  const undo = await store.undo('slide_01.svg');
  if (!undo.ok || undo.value.undo_depth !== 1) throw new Error('undo failed');
  const afterUndo = await store.getSlide('slide_01.svg');
  if (!afterUndo.value.content.includes('Hosted title') || afterUndo.value.content.includes('fill="#E66C63"')) {
    throw new Error('undo did not restore the previous hosted preview state');
  }

  const annotation = await store.annotate('slide_01.svg', { element_id: 'bg', annotation: 'Increase contrast and reduce visual noise.' });
  if (!annotation.ok || annotation.value.annotations_count !== 1) throw new Error('annotation staging failed');
  const annotated = await store.getSlide('slide_01.svg');
  if (!annotated.value.content.includes('data-edit-target="true"')) throw new Error('annotation not rendered in hosted SVG');

  const saved = await store.saveAll();
  if (!saved.ok || saved.value.hosted_status !== 'captured-not-applied') throw new Error('hosted save authority boundary failed');
  const capture = await store.getCaptured();
  if (!capture.ok || capture.value.harness_status !== 'not-validated') throw new Error('hosted editor claimed Harness validation');
  if (capture.value.captures.length !== 1 || capture.value.captures[0].changes.length !== 1) throw new Error('editor capture history mismatch');
  if (capture.value.captures[0].changes[0].direct_edits[0].text !== 'Hosted title') throw new Error('direct edit missing from capture');

  const committedMirror = await store.getSlide('slide_01.svg');
  if (committedMirror.value.undo_depth !== 0 || !committedMirror.value.content.includes('Hosted title')) {
    throw new Error('Cloudflare mirror did not retain captured direct edits');
  }

  const assetPayload = btoa('hosted-asset');
  const assetPut = await store.upsertAsset(hostKey, 'images', 'sample.txt', { base64: assetPayload, content_type: 'text/plain' });
  if (!assetPut.ok) throw new Error('asset upload failed');
  const asset = await store.getAsset('images', 'sample.txt');
  if (!asset.ok || asset.base64 !== assetPayload || asset.content_type !== 'text/plain') throw new Error('asset round-trip failed');

  const removed = await store.deleteAnnotation('slide_01.svg', 'bg');
  if (!removed.ok || removed.value.annotations_count !== 0) throw new Error('annotation delete failed');

  now += 86401 * 1000;
  const expired = await store.get();
  if (expired.ok) throw new Error('expired editor session remained live');

  console.log('hosted official SVG Editor lifecycle: passed');
}

await main();
