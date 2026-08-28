import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { OfficialSessionStore } from './core.js';

class MemoryStorage {
  constructor() { this.map = new Map(); this.alarm = null; }
  async get(key) { return this.map.get(key); }
  async put(key, value) { this.map.set(key, structuredClone(value)); }
  async deleteAll() { this.map.clear(); this.alarm = null; }
  async setAlarm(value) { this.alarm = value; }
}

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.join(here, 'dist');

const stage1Snapshot = {
  session: {
    phase: 'strategist',
    status: 'active',
    current_stage: 'stage1',
    recommendation_stage: 'stage1',
    recommendation_stage_number: 1,
  },
  recommendations: {
    stage: 'stage1',
    lang: 'zh',
    primary_language: 'zh-CN',
    recommend: { canvas: 'ppt169' },
    audience: { value: '研发团队' },
    communication_intent: { value: '解释并形成技术决策' },
    audience_outcome: { value: '形成共识' },
    core_message: { value: '核心架构边界必须清晰' },
    delivery_context: { value: '20 分钟技术分享' },
    artifact_afterlife: { value: '设计评审参考' },
    content_divergence: { value: '' },
    template_options: {
      schema_version: 1,
      phase: 'template',
      default_mode: 'free_design',
      library: { brand: [], style: [], layout: [], deck: [] },
      explicit: [],
      preselected_keys: [],
      options_sha256: '1'.repeat(64),
    },
  },
};

const stage2Snapshot = {
  session: {
    phase: 'strategist',
    status: 'active',
    current_stage: 'stage2',
    recommendation_stage: 'stage2',
    recommendation_stage_number: 2,
  },
  recommendations: {
    stage: 'stage2',
    lang: 'zh',
    recommend: {
      delivery_purpose: 'balanced',
      mode: 'custom',
      visual_style: 'custom',
      image_strategy: 'custom',
      image_usage: ['none'],
      generation_mode: 'continuous',
    },
    page_count: { value: '12-15' },
    proactive_speaker_notes: { value: true },
    proactive_custom_animations: { value: false },
    proactive_narration_audio: { value: false },
    refine_spec: { value: false },
    design_directions: { selected: 0, candidates: [] },
  },
};

async function main() {
  const storage = new MemoryStorage();
  let now = Date.parse('2026-08-28T15:00:00Z');
  const store = new OfficialSessionStore(storage, () => now);
  const hostKey = 'a'.repeat(64);

  const created = await store.create({
    schema: 'ppt-master-hosted-official-bootstrap/v1',
    harness_commit: 'b'.repeat(40),
    api_snapshot: stage1Snapshot,
  });
  if (!created.ok) throw new Error(JSON.stringify(created));
  await store.setHostKey(hostKey);

  const rec1 = await store.getOfficial('/api/recommendations');
  if (!rec1.ok || rec1.value.stage !== 'stage1') throw new Error('Stage 1 recommendation not served');

  const stage1Payload = {
    stage: 'stage1',
    status: 'confirmed',
    primary_language: 'zh-CN',
    canvas: 'ppt169',
    audience: '研发团队',
    template_selection: { mode: 'free_design', selection_keys: [] },
  };
  const captured1 = await store.captureConfirm(stage1Payload);
  if (!captured1.ok || captured1.value.status !== 'captured-not-validated') throw new Error('Stage 1 capture authority boundary failed');
  const waiting = await store.getOfficial('/api/session');
  if (!waiting.ok || waiting.value.status !== 'waiting_agent') throw new Error('Stage 1 did not enter waiting_agent');

  const badAdvance = await store.advance('f'.repeat(64), stage2Snapshot);
  if (badAdvance.ok || badAdvance.status !== 403) throw new Error('invalid host key was accepted');

  const advanced = await store.advance(hostKey, stage2Snapshot);
  if (!advanced.ok || advanced.record.active_stage !== 'stage2') throw new Error('Stage 2 advance failed');
  const rec2 = await store.getOfficial('/api/recommendations');
  if (!rec2.ok || rec2.value.stage !== 'stage2') throw new Error('Stage 2 recommendation not served');

  const captured2 = await store.captureConfirm({ stage: 'final', status: 'confirmed', page_count: '12-15' });
  if (!captured2.ok || captured2.value.status !== 'captured-not-validated') throw new Error('Stage 2 capture authority boundary failed');

  const closed = await store.close('confirmed');
  if (!closed.ok || closed.record.status !== 'closed') throw new Error('remote session close failed');

  const captures = await store.getCaptured();
  if (!captures.ok || captures.value.captures.length !== 2) throw new Error('capture history mismatch');
  if (captures.value.harness_status !== 'not-validated') throw new Error('Hosted layer claimed Harness validation');

  const requiredAssets = [
    'official-confirm.html',
    'bootstrap.js',
    'host_bridge.js',
    'static/app.js',
    'static/style.css',
    'static/catalogs.json',
    'generated/icon-previews.json',
    'generated/ai-image-comparison.json',
    'generated/source-manifest.json',
  ];
  for (const rel of requiredAssets) {
    if (!fs.existsSync(path.join(dist, rel))) throw new Error(`built hosted asset missing: ${rel}`);
  }
  const officialHtml = fs.readFileSync(path.join(dist, 'official-confirm.html'), 'utf8');
  if (!officialHtml.includes('/host_bridge.js') || !officialHtml.includes('/static/app.js')) {
    throw new Error('host bridge was not injected ahead of official app.js');
  }
  const officialApp = fs.readFileSync(path.join(dist, 'static/app.js'), 'utf8');
  if (officialApp.includes('ppt-master-hosted-official')) {
    throw new Error('official app.js was modified instead of copied unchanged');
  }

  const bootstrap = fs.readFileSync(path.join(dist, 'bootstrap.js'), 'utf8');
  if (!bootstrap.includes('ppt-master-hosted-official-bootstrap-handoff/v2')) {
    throw new Error('host-known bootstrap handoff v2 missing');
  }
  if (!bootstrap.includes('session: handoff.session') || !bootstrap.includes('host_key: handoff.host_key')) {
    throw new Error('browser bootstrap no longer creates the predeclared host-known session');
  }
  const worker = fs.readFileSync(path.join(here, 'worker.js'), 'utf8');
  if (!worker.includes("const token = String(body.session || '')") || !worker.includes("const hostKey = String(body.host_key || '')")) {
    throw new Error('Worker no longer accepts host-known session identity');
  }
  if (worker.includes('makeToken(')) {
    throw new Error('Worker must not silently replace the host-known session identity');
  }

  now += 86401 * 1000;
  const expired = await store.get();
  if (expired.ok) throw new Error('expired session remained live');

  console.log('hosted official Confirm UI lifecycle: passed');
}

await main();
