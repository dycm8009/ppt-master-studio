const BOOTSTRAP_PREFIX = '#ppt-master-official-bootstrap=';
const ADVANCE_PREFIX = '#ppt-master-official-advance=';
export const MAX_HANDOFF_BYTES = 131072;

function encodeBase64UrlUtf8(text) {
  const bytes = new TextEncoder().encode(text);
  let binary = '';
  for (let i = 0; i < bytes.length; i += 0x4000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x4000));
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function decodeBase64UrlUtf8(value) {
  if (!/^[A-Za-z0-9_-]+$/.test(value || '')) throw new Error('invalid handoff encoding');
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = Uint8Array.from(binary, char => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function encodeEnvelope(value) {
  const json = JSON.stringify(value);
  const size = new TextEncoder().encode(json).byteLength;
  if (size > MAX_HANDOFF_BYTES) throw new Error(`browser handoff exceeds ${MAX_HANDOFF_BYTES} bytes`);
  return encodeBase64UrlUtf8(json);
}

function decodeEnvelope(encoded) {
  const json = decodeBase64UrlUtf8(encoded);
  if (new TextEncoder().encode(json).byteLength > MAX_HANDOFF_BYTES) throw new Error('browser handoff too large');
  const value = JSON.parse(json);
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('browser handoff object required');
  return value;
}

export function buildBootstrapHash(payload) {
  return `${BOOTSTRAP_PREFIX}${encodeEnvelope({ schema: 'ppt-master-hosted-official-bootstrap-handoff/v1', payload })}`;
}

export function buildAdvanceHash({ session, host_key, api_snapshot }) {
  return `${ADVANCE_PREFIX}${encodeEnvelope({
    schema: 'ppt-master-hosted-official-advance-handoff/v1',
    session,
    host_key,
    api_snapshot,
  })}`;
}

function decodeCurrentHash(hash) {
  const text = String(hash || '');
  if (text.startsWith(BOOTSTRAP_PREFIX)) {
    const value = decodeEnvelope(text.slice(BOOTSTRAP_PREFIX.length));
    if (value.schema !== 'ppt-master-hosted-official-bootstrap-handoff/v1') throw new Error('unsupported bootstrap handoff');
    return { kind: 'bootstrap', ...value };
  }
  if (text.startsWith(ADVANCE_PREFIX)) {
    const value = decodeEnvelope(text.slice(ADVANCE_PREFIX.length));
    if (value.schema !== 'ppt-master-hosted-official-advance-handoff/v1') throw new Error('unsupported advance handoff');
    return { kind: 'advance', ...value };
  }
  return null;
}

async function postJson(path, body, headers = {}) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...headers },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `request failed: ${response.status}`);
  return data;
}

export async function runBootstrapPage() {
  const status = document.getElementById('status');
  try {
    const handoff = decodeCurrentHash(location.hash);
    if (!handoff) throw new Error('PPT Master hosted handoff is missing');
    history.replaceState(null, '', location.pathname + location.search);

    if (handoff.kind === 'bootstrap') {
      status.textContent = 'Creating hosted Confirm UI session…';
      const created = await postJson('/api/sessions', { payload: handoff.payload });
      sessionStorage.setItem(`ppt-master-host-key:${created.session}`, created.host_key);
      location.replace(created.path);
      return;
    }

    if (!/^[0-9a-f]{48}$/.test(handoff.session || '')) throw new Error('invalid session');
    if (!/^[0-9a-f]{64}$/.test(handoff.host_key || '')) throw new Error('invalid host key');
    status.textContent = 'Updating the existing session with Stage 2…';
    await postJson(`/api/sessions/${handoff.session}/advance`, { api_snapshot: handoff.api_snapshot }, {
      'x-ppt-master-host-key': handoff.host_key,
    });
    sessionStorage.setItem(`ppt-master-host-key:${handoff.session}`, handoff.host_key);
    location.replace(`/s/${handoff.session}`);
  } catch (error) {
    status.textContent = String(error?.message || error);
    status.className = 'error';
  }
}
