import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const worker = fs.readFileSync(path.join(here, 'worker_production.js'), 'utf8');
const core = fs.readFileSync(path.join(here, 'core.js'), 'utf8');
const editorCore = fs.readFileSync(path.join(here, 'editor_core.js'), 'utf8');
const prod = fs.readFileSync(path.join(here, 'wrangler.production.jsonc'), 'utf8');
const config = JSON.parse(fs.readFileSync(path.join(here, 'HOSTED_UI.json'), 'utf8'));

for (const forbidden of [
  '/accept/stage2',
  '/accept/editor',
  'ACCEPTANCE_STAGE2',
  'ACCEPTANCE_EDITOR',
  'resetEditor',
]) {
  if (worker.includes(forbidden)) throw new Error(`production Worker contains acceptance-only surface: ${forbidden}`);
}

for (const required of [
  "response|advance|close",
  'stub.closeHost(hostKey',
  'stub.editorCloseHost(hostKey',
  '/api/editor-sessions',
  '/api/save-all',
  '/official-confirm.html',
  '/official-editor.html',
  'SameSite=Strict',
]) {
  if (!worker.includes(required)) throw new Error(`production Worker contract missing: ${required}`);
}

if (!core.includes("status: 'captured-not-validated'") || !core.includes("harness_status: 'not-validated'")) {
  throw new Error('Confirm capture layer crossed the Harness authority boundary');
}
if (!editorCore.includes("status: 'captured-not-applied'") || !editorCore.includes("harness_status: 'not-validated'")) {
  throw new Error('SVG Editor capture layer crossed the Harness authority boundary');
}
if (!core.includes('async closeHost(hostKey')) throw new Error('Confirm host close is not authenticated');

if (!prod.includes('"name": "ppt-master-hosted-confirm"')) throw new Error('production Worker name mismatch');
if (!prod.includes('"main": "worker_production.js"')) throw new Error('production config does not use clean Worker');
if (!prod.includes('"/e/*"') || !prod.includes('"/images/*"')) throw new Error('production run_worker_first misses editor routes');

if (config.schema !== 'ppt-master-studio-hosted-ui-config/v1') throw new Error('Hosted UI config schema mismatch');
if (config.production_base !== 'https://ppt-master-hosted-confirm.dycm-lab.workers.dev') throw new Error('production base mismatch');
if (config.authority.confirm !== 'local-pinned-official-confirm-ui') throw new Error('Confirm authority moved remote');
if (config.authority.svg_editor !== 'local-pinned-official-svg-editor') throw new Error('SVG Editor authority moved remote');
if (config.motion_review_surface !== false) throw new Error('Motion Review surface must remain disabled');

console.log('hosted production authority contract: passed');
