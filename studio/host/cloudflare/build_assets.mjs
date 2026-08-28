import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const hostDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(hostDir, '../../..');
const dist = path.join(hostDir, 'dist');
const publicDir = path.join(hostDir, 'public');
const officialStatic = path.join(root, 'skills/ppt-master/scripts/confirm_ui/static');
const officialIndex = path.join(officialStatic, 'index.html');
const officialEditorStatic = path.join(root, 'skills/ppt-master/scripts/svg_editor/static');
const officialEditorIndex = path.join(officialEditorStatic, 'index.html');
const iconRoot = path.join(root, 'skills/ppt-master/templates/icons');
const aiRoot = path.join(root, 'skills/ppt-master/references/ai-image-comparison/rendering');

const ICON_PREVIEW_SAMPLES = {
  'chunk-filled': ['home', 'chart-line', 'users', 'target'],
  'tabler-filled': ['home', 'chart-dots', 'user', 'bulb'],
  'tabler-outline': ['home', 'chart-line', 'users', 'bulb'],
  'phosphor-duotone': ['house', 'chart-line', 'users', 'target'],
};

function ensureDir(dir) { fs.mkdirSync(dir, { recursive: true }); }
function writeJson(file, value) { ensureDir(path.dirname(file)); fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n'); }
function sha256(file) { return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'); }
function stripSvg(raw) {
  return raw.replace(/<\?xml[^>]*>\s*/g, '').replace(/<!--.*?-->\s*/gs, '').trim();
}

fs.rmSync(dist, { recursive: true, force: true });
ensureDir(dist);

for (const name of ['index.html', 'bootstrap.js', 'host_bridge.js', 'editor_host_bridge.js']) {
  fs.copyFileSync(path.join(publicDir, name), path.join(dist, name));
}

// Official Confirm UI: source files stay byte-for-byte pinned; only the wrapper
// index receives the Hosted bridge before the official app.js.
fs.cpSync(officialStatic, path.join(dist, 'static'), { recursive: true });
let indexHtml = fs.readFileSync(officialIndex, 'utf8');
const officialScript = '    <script src="/static/app.js"></script>';
if (!indexHtml.includes(officialScript)) throw new Error('official Confirm UI index.html app.js marker changed');
indexHtml = indexHtml.replace(
  officialScript,
  '    <script src="/host_bridge.js"></script>\n' + officialScript,
);
fs.writeFileSync(path.join(dist, 'official-confirm.html'), indexHtml);

// Official SVG Editor: copy the official frontend unchanged to a separate
// namespace. Rewrite only the wrapper index paths so Confirm UI /static and
// SVG Editor /editor-static can coexist in the same Worker.
fs.cpSync(officialEditorStatic, path.join(dist, 'editor-static'), { recursive: true });
let editorHtml = fs.readFileSync(officialEditorIndex, 'utf8');
const editorStyle = '    <link rel="stylesheet" href="/static/style.css">';
const editorScript = '    <script src="/static/app.js"></script>';
if (!editorHtml.includes(editorStyle) || !editorHtml.includes(editorScript)) {
  throw new Error('official SVG Editor index.html asset markers changed');
}
editorHtml = editorHtml
  .replace(editorStyle, '    <link rel="stylesheet" href="/editor-static/style.css">')
  .replace(
    editorScript,
    '    <script src="/editor_host_bridge.js"></script>\n    <script src="/editor-static/app.js"></script>',
  );
fs.writeFileSync(path.join(dist, 'official-editor.html'), editorHtml);

ensureDir(path.join(dist, 'generated'));
const iconPreviews = {};
for (const [library, names] of Object.entries(ICON_PREVIEW_SAMPLES)) {
  iconPreviews[library] = [];
  for (const name of names) {
    const file = path.join(iconRoot, library, `${name}.svg`);
    if (!fs.existsSync(file)) continue;
    iconPreviews[library].push({ name, svg: stripSvg(fs.readFileSync(file, 'utf8')) });
  }
}
writeJson(path.join(dist, 'generated/icon-previews.json'), iconPreviews);

const manifestFile = path.join(aiRoot, '_manifest.json');
const manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf8'));
const rendering = [];
for (const item of Array.isArray(manifest.items) ? manifest.items : []) {
  const filename = String(item.filename || '');
  if (!/^[A-Za-z0-9_.-]+\.png$/.test(filename)) continue;
  if (!fs.existsSync(path.join(aiRoot, filename))) continue;
  const id = path.basename(filename, '.png');
  rendering.push({
    id,
    label: item.type || id,
    filename,
    purpose: item.purpose || '',
    alt_text: item.alt_text || '',
  });
}
writeJson(path.join(dist, 'generated/ai-image-comparison.json'), { rendering });
fs.cpSync(aiRoot, path.join(dist, 'ai-image-comparison/rendering'), { recursive: true });

writeJson(path.join(dist, 'generated/source-manifest.json'), {
  schema: 'ppt-master-hosted-official-assets/v2',
  sources: {
    'confirm_ui/static/index.html': sha256(officialIndex),
    'confirm_ui/static/app.js': sha256(path.join(officialStatic, 'app.js')),
    'confirm_ui/static/style.css': sha256(path.join(officialStatic, 'style.css')),
    'confirm_ui/static/catalogs.json': sha256(path.join(officialStatic, 'catalogs.json')),
    'svg_editor/static/index.html': sha256(officialEditorIndex),
    'svg_editor/static/app.js': sha256(path.join(officialEditorStatic, 'app.js')),
    'svg_editor/static/style.css': sha256(path.join(officialEditorStatic, 'style.css')),
    'ai-image-comparison/rendering/_manifest.json': sha256(manifestFile),
  },
  host_injection: {
    confirm_ui: 'host_bridge.js inserted before the unmodified official Confirm UI app.js',
    svg_editor: 'editor_host_bridge.js inserted before the unmodified official SVG Editor app.js; only wrapper asset paths are namespaced',
  },
});

console.log(`hosted official Confirm UI + SVG Editor assets built: ${dist}`);
