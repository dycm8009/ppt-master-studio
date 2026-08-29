import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(path.join(here, 'public/host_bridge.js'), 'utf8');
const session = 'a'.repeat(48);
const commit = 'b'.repeat(40);

class FakeElement {
  constructor(tag, registry) {
    this.tagName = tag.toUpperCase();
    this.registry = registry;
    this.children = [];
    this.style = {};
    this.dataset = {};
    this.listeners = {};
    this.textContent = '';
    this.value = '';
    this.readOnly = false;
    this.rows = 0;
    this.selected = false;
    this.focused = false;
    this._id = '';
  }
  set id(value) {
    this._id = value;
    if (value) this.registry.set(value, this);
  }
  get id() { return this._id; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = [...children]; }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  focus() { this.focused = true; }
  select() { this.selected = true; }
  setSelectionRange(start, end) { this.selection = [start, end]; }
  click() { return this.listeners.click?.({ currentTarget: this }); }
}

function responseData(captures) {
  return {
    schema: 'ppt-master-hosted-official-captured/v1',
    status: 'captured-not-validated',
    harness_status: 'not-validated',
    harness_commit: commit,
    active_stage: captures.at(-1).stage,
    captures,
    session_status: captures.at(-1).stage === 'stage1' ? 'waiting-agent' : 'captured',
  };
}

async function main() {
  const registry = new Map();
  const body = new FakeElement('body', registry);
  let currentResponse = responseData([
    { stage: 'stage1', payload: { stage: 'stage1', canvas: 'ppt169' } },
  ]);
  const calls = [];
  let copied = null;
  let replacedUrl = null;

  const nativeFetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input.url;
    calls.push([url, String(init.method || 'GET').toUpperCase()]);
    if (url === '/api/confirm') {
      return new Response(JSON.stringify({ status: 'captured-not-validated' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    }
    if (url === `/api/sessions/${session}/response`) {
      return new Response(JSON.stringify(currentResponse), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const document = {
    body,
    createElement: tag => new FakeElement(tag, registry),
    getElementById: id => registry.get(id) || null,
    execCommand: () => false,
  };
  const context = {
    console,
    document,
    location: { pathname: `/s/${session}`, search: '' },
    history: { replaceState: (_a, _b, url) => { replacedUrl = url; } },
    navigator: { clipboard: { writeText: async text => { copied = text; } } },
    window: { fetch: nativeFetch },
    Request,
    Response,
    JSON,
    Object,
    Array,
    String,
    Error,
  };
  context.globalThis = context;

  vm.runInNewContext(source, context, { filename: 'host_bridge.js' });

  await context.window.fetch('/api/confirm', {
    method: 'POST',
    body: JSON.stringify({ stage: 'stage1' }),
  });
  if (replacedUrl !== `/s/${session}`) throw new Error('short session URL was not preserved');
  const textarea1 = registry.get('ppt-master-hosted-return-json');
  const copy1 = registry.get('ppt-master-hosted-return-copy');
  if (!textarea1 || !copy1) throw new Error('copy JSON UI was not rendered');
  const envelope1 = JSON.parse(textarea1.value);
  if (envelope1.schema !== 'ppt-master-hosted-confirm-return/v1') throw new Error('return schema mismatch');
  if (envelope1.session !== session || envelope1.stage !== 'stage1') throw new Error('Stage 1 return identity mismatch');
  if (envelope1.response.harness_commit !== commit) throw new Error('Harness commit missing from return');
  await copy1.click();
  if (copied !== textarea1.value) throw new Error('Clipboard did not receive exact return JSON');

  currentResponse = responseData([
    ...currentResponse.captures,
    { stage: 'stage2', payload: { stage: 'final', page_count: '12-15' } },
  ]);
  await context.window.fetch('/api/confirm', {
    method: 'POST',
    body: JSON.stringify({ stage: 'final' }),
  });
  const textarea2 = registry.get('ppt-master-hosted-return-json');
  const envelope2 = JSON.parse(textarea2.value);
  if (envelope2.stage !== 'stage2' || envelope2.response.captures.length !== 2) {
    throw new Error('Stage 2 return history mismatch');
  }

  context.navigator.clipboard = undefined;
  document.execCommand = () => false;
  const copy2 = registry.get('ppt-master-hosted-return-copy');
  await copy2.click();
  if (!textarea2.selected) throw new Error('manual selection fallback was not activated');
  if (!registry.get('ppt-master-hosted-return-status').textContent.includes('全选复制')) {
    throw new Error('manual copy fallback instructions missing');
  }

  const responseGets = calls.filter(([url]) => url.endsWith('/response'));
  if (responseGets.length !== 2) throw new Error('return endpoint was not read after each capture');
  console.log('hosted Confirm copy-JSON return bridge: passed');
}

await main();
