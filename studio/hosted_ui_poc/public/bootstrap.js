const SURFACES = Object.freeze(['stage1', 'stage2', 'deck-review', 'motion-review']);
const BOOTSTRAP_SCHEMA = 'ppt-master-browser-bootstrap/v1';
const CAPTURE_SCHEMA = 'ppt-master-browser-capture/v1';
export const BOOTSTRAP_PREFIX = '#ppt-master-bootstrap=';
export const CAPTURE_PREFIX = '#ppt-master-captured=';
export const MAX_HANDOFF_BYTES = 24576;

function assertSurface(surface) {
  if (!SURFACES.includes(surface)) throw new Error('unsupported surface');
  return surface;
}

function assertPayload(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('payload object required');
  }
  return payload;
}

function encodeBase64UrlUtf8(text) {
  const bytes = new TextEncoder().encode(text);
  let binary = '';
  for (let i = 0; i < bytes.length; i += 0x4000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x4000));
  }
  const base64 = typeof btoa === 'function'
    ? btoa(binary)
    : Buffer.from(binary, 'binary').toString('base64');
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function decodeBase64UrlUtf8(value) {
  if (!/^[A-Za-z0-9_-]+$/.test(value || '')) throw new Error('invalid handoff encoding');
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
  const binary = typeof atob === 'function'
    ? atob(padded)
    : Buffer.from(padded, 'base64').toString('binary');
  const bytes = Uint8Array.from(binary, char => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function encodeEnvelope(value) {
  const json = JSON.stringify(value);
  const byteLength = new TextEncoder().encode(json).byteLength;
  if (byteLength > MAX_HANDOFF_BYTES) {
    throw new Error(`browser handoff exceeds ${MAX_HANDOFF_BYTES} bytes`);
  }
  return encodeBase64UrlUtf8(json);
}

function decodeEnvelope(encoded) {
  const json = decodeBase64UrlUtf8(encoded);
  if (new TextEncoder().encode(json).byteLength > MAX_HANDOFF_BYTES) {
    throw new Error('browser handoff too large');
  }
  const value = JSON.parse(json);
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('browser handoff object required');
  }
  return value;
}

export function buildBootstrapHash({ surface, payload }) {
  return `${BOOTSTRAP_PREFIX}${encodeEnvelope({
    schema: BOOTSTRAP_SCHEMA,
    surface: assertSurface(surface),
    payload: assertPayload(payload)
  })}`;
}

export function buildBootstrapUrl({ origin, surface, payload }) {
  if (!origin) throw new Error('origin required');
  return `${String(origin).replace(/\/$/, '')}/${buildBootstrapHash({ surface, payload })}`;
}

export function decodeBootstrapHash(hash) {
  if (!String(hash || '').startsWith(BOOTSTRAP_PREFIX)) return null;
  const value = decodeEnvelope(String(hash).slice(BOOTSTRAP_PREFIX.length));
  if (value.schema !== BOOTSTRAP_SCHEMA) throw new Error('unsupported bootstrap schema');
  return {
    schema: value.schema,
    surface: assertSurface(value.surface),
    payload: assertPayload(value.payload)
  };
}

export function buildCaptureHash({ session, surface, response, captured_at }) {
  if (!/^[0-9a-f]{48}$/.test(String(session || ''))) throw new Error('invalid session');
  if (!response || typeof response !== 'object' || Array.isArray(response)) {
    throw new Error('response object required');
  }
  return `${CAPTURE_PREFIX}${encodeEnvelope({
    schema: CAPTURE_SCHEMA,
    status: 'captured-not-validated',
    session: String(session),
    surface: assertSurface(surface),
    response,
    captured_at: captured_at || null,
    harness_status: 'not-validated'
  })}`;
}

export function decodeCaptureHash(hash) {
  if (!String(hash || '').startsWith(CAPTURE_PREFIX)) return null;
  const value = decodeEnvelope(String(hash).slice(CAPTURE_PREFIX.length));
  if (value.schema !== CAPTURE_SCHEMA) throw new Error('unsupported capture schema');
  if (!/^[0-9a-f]{48}$/.test(String(value.session || ''))) throw new Error('invalid session');
  if (!value.response || typeof value.response !== 'object' || Array.isArray(value.response)) {
    throw new Error('response object required');
  }
  return {
    ...value,
    surface: assertSurface(value.surface)
  };
}
