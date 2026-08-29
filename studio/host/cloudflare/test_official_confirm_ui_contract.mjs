import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../..');
const appPath = path.join(root, 'skills/ppt-master/scripts/confirm_ui/static/app.js');
const serverPath = path.join(root, 'skills/ppt-master/scripts/confirm_ui/server.py');
const contractPath = path.join(here, 'official_confirm_ui_contract.json');
const hostBridgePath = path.join(here, 'public/host_bridge.js');

const app = fs.readFileSync(appPath, 'utf8');
const server = fs.readFileSync(serverPath, 'utf8');
const hostBridge = fs.readFileSync(hostBridgePath, 'utf8');
const contract = JSON.parse(fs.readFileSync(contractPath, 'utf8'));

const expectedBrowserApi = new Set(contract.frontend_api.map(x => x.path));
const appApi = new Set([...app.matchAll(/["'](\/api\/[A-Za-z0-9_./-]+)["']/g)].map(m => m[1]));

for (const endpoint of expectedBrowserApi) {
  if (!appApi.has(endpoint)) {
    throw new Error(`official app.js no longer references mapped endpoint: ${endpoint}`);
  }
}

for (const endpoint of appApi) {
  if (!expectedBrowserApi.has(endpoint)) {
    throw new Error(`official app.js gained unmapped endpoint: ${endpoint}`);
  }
}

for (const item of contract.frontend_api) {
  const quoted = `@app.route('${item.path}'`;
  if (!server.includes(quoted)) {
    throw new Error(`official server.py no longer exposes mapped endpoint: ${item.method} ${item.path}`);
  }
}

if (!app.includes('/static/catalogs.json')) throw new Error('official static catalogs fallback missing');
if (!app.includes('/static/style_previews/')) throw new Error('official visual-style preview route missing');
if (!server.includes("@app.route('/ai-image-comparison/<kind>/<filename>')")) {
  throw new Error('official generated-image comparison asset route missing');
}
if (!app.includes('pollForStage(nextStage)')) throw new Error('official Stage 1 -> Stage 2 polling flow missing');
if (!app.includes('recommendation_stage_number')) throw new Error('official session stage readiness field missing');
if (!server.includes("data['template_options'] = template_options")) {
  throw new Error('official Stage 1 recommendations no longer include browser-ready template_options');
}

if (contract.manual_return_contract?.schema !== 'ppt-master-hosted-confirm-return/v1') {
  throw new Error('manual Hosted return schema missing from contract');
}
if (!hostBridge.includes("const RETURN_SCHEMA = 'ppt-master-hosted-confirm-return/v1'")) {
  throw new Error('Hosted wrapper does not emit the contracted copy-JSON schema');
}
if (!hostBridge.includes('/api/sessions/${session}/response')) {
  throw new Error('Hosted wrapper does not read the captured response before copying JSON');
}
if (!hostBridge.includes('ppt-master-hosted-return-copy') || !hostBridge.includes('ppt-master-hosted-return-json')) {
  throw new Error('Hosted wrapper copy button or read-only JSON fallback is missing');
}

console.log('official Confirm UI compatibility + explicit return map: passed');
console.log([...appApi].sort().join('\n'));
