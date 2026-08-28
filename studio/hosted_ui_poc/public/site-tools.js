export const SITE_TOOL_NAMES = Object.freeze([
  'create_confirm_session',
  'get_confirm_session',
  'get_confirm_response'
]);

const SURFACES = ['stage1', 'stage2', 'deck-review', 'motion-review'];
const TOKEN_RE = /^[0-9a-f]{48}$/;

async function requestJson(fetchImpl, url, options = {}) {
  const response = await fetchImpl(url, options);
  let body;
  try {
    body = await response.json();
  } catch {
    body = { error: `HTTP ${response.status}` };
  }
  return { response, body };
}

function errorMessage(body, fallback) {
  return String(body?.error || fallback);
}

function requireToken(session) {
  if (!TOKEN_RE.test(String(session || ''))) {
    throw new Error('session must be a 48-character lowercase hex token');
  }
  return String(session);
}

export function buildPptMasterSiteTools({
  fetchImpl = globalThis.fetch?.bind(globalThis),
  origin = globalThis.location?.origin || '',
  onCreated = () => {}
} = {}) {
  if (typeof fetchImpl !== 'function') throw new Error('fetch implementation required');
  if (!origin) throw new Error('site origin required');

  return [
    {
      name: 'create_confirm_session',
      description:
        'Create a temporary PPT Master Hosted Confirm session from a Harness-derived surface payload. Returns a confirmation URL for the user. This tool never creates an accepted Harness receipt.',
      inputSchema: {
        type: 'object',
        properties: {
          surface: { type: 'string', enum: SURFACES },
          payload: {
            type: 'object',
            description: 'Harness-derived confirmation payload including the exact recommendation/options hashes required by the local validator.',
            additionalProperties: true
          }
        },
        required: ['surface', 'payload'],
        additionalProperties: false
      },
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      async execute(input = {}) {
        const { surface, payload } = input;
        if (!SURFACES.includes(surface)) throw new Error('unsupported surface');
        if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
          throw new Error('payload object required');
        }
        const { response, body } = await requestJson(fetchImpl, `${origin}/api/sessions`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ surface, payload })
        });
        if (!response.ok) throw new Error(errorMessage(body, 'session create failed'));
        const value = {
          schema: 'ppt-master-site-tools-host-session/v1',
          status: 'created',
          session: body.session,
          surface: body.surface,
          confirm_url: new URL(body.path, origin).toString(),
          expires_at: body.expires_at,
          harness_status: 'not-validated'
        };
        onCreated(value);
        return JSON.stringify(value);
      }
    },
    {
      name: 'get_confirm_session',
      description:
        'Read the status of a PPT Master Hosted Confirm session. This is read-only and intentionally omits the private session payload.',
      inputSchema: {
        type: 'object',
        properties: {
          session: { type: 'string', pattern: '^[0-9a-f]{48}$' }
        },
        required: ['session'],
        additionalProperties: false
      },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      async execute(input = {}) {
        const session = requireToken(input.session);
        const { response, body } = await requestJson(fetchImpl, `${origin}/api/sessions/${session}`);
        if (response.status === 404) {
          return JSON.stringify({
            schema: 'ppt-master-site-tools-host-session-status/v1',
            status: 'missing-or-expired',
            session,
            harness_status: 'not-validated'
          });
        }
        if (!response.ok) throw new Error(errorMessage(body, 'session lookup failed'));
        return JSON.stringify({
          schema: 'ppt-master-site-tools-host-session-status/v1',
          status: body.response ? 'captured' : 'open',
          session,
          surface: body.surface,
          confirm_url: `${origin}/s/${session}`,
          expires_at: body.expires_at,
          response_available: Boolean(body.response),
          harness_status: 'not-validated'
        });
      }
    },
    {
      name: 'get_confirm_response',
      description:
        'Read the user-confirmed response for a Hosted Confirm session. Returns pending until the user confirms. The caller must still run the local PPT Master Harness validator before treating the response as accepted.',
      inputSchema: {
        type: 'object',
        properties: {
          session: { type: 'string', pattern: '^[0-9a-f]{48}$' }
        },
        required: ['session'],
        additionalProperties: false
      },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      async execute(input = {}) {
        const session = requireToken(input.session);
        const { response, body } = await requestJson(fetchImpl, `${origin}/api/sessions/${session}/response`);
        if (response.status === 404 && body?.error === 'response not captured') {
          return JSON.stringify({
            schema: 'ppt-master-site-tools-host-response/v1',
            status: 'pending',
            session,
            harness_status: 'not-validated'
          });
        }
        if (response.status === 404) {
          return JSON.stringify({
            schema: 'ppt-master-site-tools-host-response/v1',
            status: 'missing-or-expired',
            session,
            harness_status: 'not-validated'
          });
        }
        if (!response.ok) throw new Error(errorMessage(body, 'response lookup failed'));
        return JSON.stringify({
          schema: 'ppt-master-site-tools-host-response/v1',
          status: 'captured',
          session,
          surface: body.surface,
          response: body.response,
          captured_at: body.captured_at,
          harness_status: 'not-validated'
        });
      }
    }
  ];
}

export function registerPptMasterSiteTools({ modelContext, ...options } = {}) {
  const mc =
    modelContext ||
    globalThis.document?.modelContext ||
    globalThis.navigator?.modelContext;

  if (!mc || typeof mc.registerTool !== 'function') {
    return { available: false, names: [] };
  }

  const tools = buildPptMasterSiteTools(options);
  for (const tool of tools) mc.registerTool(tool);
  return { available: true, names: [...SITE_TOOL_NAMES] };
}
