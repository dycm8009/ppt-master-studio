import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../..');
const officialDir = path.join(root, 'skills/ppt-master/scripts/svg_editor/static');
const serverFile = path.join(root, 'skills/ppt-master/scripts/svg_editor/server.py');
const dist = path.join(here, 'dist');

function sha(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

const app = fs.readFileSync(path.join(officialDir, 'app.js'), 'utf8');
const server = fs.readFileSync(serverFile, 'utf8');

for (const marker of [
  'fetch("/api/slides")',
  'fetch("/api/slide/" + encodeURIComponent(name))',
  '"/annotate"',
  '"/edit"',
  '"/undo"',
  'fetch("/api/save-all", { method: "POST" })',
  'fetch("/api/config")',
  'fetch("/api/shutdown"',
]) {
  if (!app.includes(marker)) throw new Error(`official SVG Editor frontend API drift: missing ${marker}`);
}

for (const route of [
  "@app.route('/api/config')",
  "@app.route('/api/slides')",
  "@app.route('/api/slide/<name>')",
  "@app.route('/api/slide/<name>/annotate', methods=['POST'])",
  "@app.route('/api/slide/<name>/annotate/<element_id>', methods=['DELETE'])",
  "@app.route('/api/slide/<name>/edit', methods=['POST'])",
  "@app.route('/api/slide/<name>/undo', methods=['POST'])",
  "@app.route('/api/save-all', methods=['POST'])",
  "@app.route('/api/shutdown', methods=['POST'])",
]) {
  if (!server.includes(route)) throw new Error(`official SVG Editor backend contract drift: missing ${route}`);
}

const copiedApp = path.join(dist, 'editor-static/app.js');
const copiedCss = path.join(dist, 'editor-static/style.css');
const wrapper = path.join(dist, 'official-editor.html');
for (const file of [copiedApp, copiedCss, wrapper, path.join(dist, 'editor_host_bridge.js')]) {
  if (!fs.existsSync(file)) throw new Error(`hosted SVG Editor asset missing: ${path.relative(dist, file)}`);
}
if (sha(copiedApp) !== sha(path.join(officialDir, 'app.js'))) throw new Error('official SVG Editor app.js was modified');
if (sha(copiedCss) !== sha(path.join(officialDir, 'style.css'))) throw new Error('official SVG Editor style.css was modified');

const html = fs.readFileSync(wrapper, 'utf8');
if (!html.includes('/editor-static/style.css') || !html.includes('/editor-static/app.js')) {
  throw new Error('hosted SVG Editor wrapper does not namespace official assets');
}
if (!html.includes('/editor_host_bridge.js')) throw new Error('hosted SVG Editor authority bridge missing');

console.log('official SVG Editor hosted contract: passed');
