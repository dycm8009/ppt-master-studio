import { DurableObject } from 'cloudflare:workers';
import {
  OfficialSessionStore,
  validHostKey,
  validToken,
  reply,
} from './core.js';
import {
  ACCEPTANCE_STAGE2_SESSION,
  ACCEPTANCE_STAGE2_HOST_KEY,
  ACCEPTANCE_STAGE2_SNAPSHOT,
} from './acceptance_stage2.js';

const COOKIE_NAME = 'ppt_master_session';
const ACCEPTANCE_STAGE2_PATH = '/accept/stage2';

function cookieToken(request) {
  const raw = request.headers.get('cookie') || '';
  for (const part of raw.split(';')) {
    const [name, ...rest] = part.trim().split('=');
    if (name === COOKIE_NAME) {
      const value = rest.join('=');
      return validToken(value) ? value : null;
    }
  }
  return null;
}

async function readJson(request) {
  try { return await request.json(); }
  catch { throw new Error('invalid JSON'); }
}

async function assetJson(env, requestUrl, assetPath) {
  const url = new URL(requestUrl);
  url.pathname = assetPath;
  url.search = '';
  url.hash = '';
  const response = await env.ASSETS.fetch(new Request(url));
  if (!response.ok) return reply({ error: `hosted asset missing: ${assetPath}` }, 500);
  const data = await response.json();
  return reply(data, 200);
}

export class HostedSession extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.store = new OfficialSessionStore(this.ctx.storage);
  }
  async create(payload, hostKey) {
    const result = await this.store.create(payload);
    if (result.ok) await this.store.setHostKey(hostKey);
    return result;
  }
  async get() { return this.store.get(); }
  async getOfficial(pathname) { return this.store.getOfficial(pathname); }
  async captureConfirm(payload) { return this.store.captureConfirm(payload); }
  async advance(hostKey, snapshot) { return this.store.advance(hostKey, snapshot); }
  async close(reason) { return this.store.close(reason); }
  async getCaptured() { return this.store.getCaptured(); }
  async alarm() { await this.store.expire(); }
}

async function sessionStub(env, token) {
  if (!validToken(token)) throw new Error('invalid session token');
  return env.SESSIONS.getByName(token);
}

async function createHostedSession(request, env) {
  const body = await readJson(request);
  const token = String(body.session || '');
  const hostKey = String(body.host_key || '');
  if (!validToken(token)) return reply({ error: 'valid host-known session token required' }, 400);
  if (!validHostKey(hostKey)) return reply({ error: 'valid host-known host key required' }, 400);

  const stub = await sessionStub(env, token);
  const result = await stub.create(body.payload, hostKey);
  if (!result?.ok) return reply({ error: result?.error || 'session create failed' }, result?.status || 400);
  return reply({
    schema: 'ppt-master-hosted-official-session-created/v2',
    session: token,
    path: `/s/${token}`,
    expires_at: result.record.expires_at,
    harness_commit: result.record.harness_commit,
  }, 201);
}

async function handleHostSessionApi(request, env, url) {
  if (url.pathname === '/api/sessions' && request.method === 'POST') {
    return createHostedSession(request, env);
  }

  const match = url.pathname.match(/^\/api\/sessions\/([0-9a-f]{48})(?:\/(response|advance))?$/);
  if (!match) return null;
  const [, token, action] = match;
  const stub = await sessionStub(env, token);

  if (!action && request.method === 'GET') {
    const result = await stub.get();
    return result?.ok ? reply(result.record) : reply({ error: result?.error || 'session missing' }, result?.status || 404);
  }
  if (action === 'response' && request.method === 'GET') {
    const result = await stub.getCaptured();
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'response missing' }, result?.status || 404);
  }
  if (action === 'advance' && request.method === 'POST') {
    const hostKey = request.headers.get('x-ppt-master-host-key') || '';
    if (!validHostKey(hostKey)) return reply({ error: 'host key required' }, 403);
    const body = await readJson(request);
    const result = await stub.advance(hostKey, body.api_snapshot);
    return result?.ok
      ? reply({ schema: 'ppt-master-hosted-official-advanced/v1', status: 'ready', stage: 'stage2' })
      : reply({ error: result?.error || 'advance failed' }, result?.status || 400);
  }
  return reply({ error: 'method not allowed' }, 405);
}

async function handleOfficialApi(request, env, url) {
  if (url.pathname === '/api/catalogs' && request.method === 'GET') {
    return assetJson(env, request.url, '/static/catalogs.json');
  }
  if (url.pathname === '/api/icon-previews' && request.method === 'GET') {
    return assetJson(env, request.url, '/generated/icon-previews.json');
  }
  if (url.pathname === '/api/ai-image-comparison' && request.method === 'GET') {
    return assetJson(env, request.url, '/generated/ai-image-comparison.json');
  }

  const token = cookieToken(request);
  if (!token) return reply({ error: 'hosted Confirm UI session cookie missing' }, 401);
  const stub = await sessionStub(env, token);

  if ((url.pathname === '/api/session' || url.pathname === '/api/recommendations') && request.method === 'GET') {
    const result = await stub.getOfficial(url.pathname);
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'session API failed' }, result?.status || 404);
  }
  if (url.pathname === '/api/confirm' && request.method === 'POST') {
    const payload = await readJson(request);
    const result = await stub.captureConfirm(payload);
    return result?.ok ? reply(result.value) : reply({ error: result?.error || 'confirm capture failed' }, result?.status || 400);
  }
  if (url.pathname === '/api/shutdown' && request.method === 'POST') {
    const body = await readJson(request).catch(() => ({}));
    const result = await stub.close(body?.reason || 'confirmed');
    return result?.ok
      ? reply({ schema: 'ppt-master-hosted-official-close/v1', status: 'closed' })
      : reply({ error: result?.error || 'close failed' }, result?.status || 404);
  }
  return null;
}

async function serveSessionPage(request, env, token) {
  const stub = await sessionStub(env, token);
  const state = await stub.get();
  if (!state?.ok) return reply({ error: state?.error || 'session missing or expired' }, state?.status || 404);

  const assetUrl = new URL(request.url);
  assetUrl.pathname = '/official-confirm.html';
  assetUrl.search = '';
  assetUrl.hash = '';
  const response = await env.ASSETS.fetch(new Request(assetUrl));
  if (!response.ok) return reply({ error: 'official Confirm UI asset missing' }, 500);

  const headers = new Headers(response.headers);
  headers.set('cache-control', 'no-store');
  headers.append('set-cookie', `${COOKIE_NAME}=${token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=86400`);
  return new Response(response.body, { status: response.status, headers });
}

async function handleAcceptanceStage2(request, env) {
  if (request.method !== 'GET') return reply({ error: 'method not allowed' }, 405);
  const stub = await sessionStub(env, ACCEPTANCE_STAGE2_SESSION);
  const result = await stub.advance(ACCEPTANCE_STAGE2_HOST_KEY, ACCEPTANCE_STAGE2_SNAPSHOT);
  if (!result?.ok) {
    const current = await stub.get();
    if (!current?.ok || current.record?.active_stage !== 'stage2') {
      return reply({ error: result?.error || 'Stage 2 acceptance advance failed' }, result?.status || 400);
    }
  }
  return Response.redirect(new URL(`/s/${ACCEPTANCE_STAGE2_SESSION}`, request.url), 302);
}

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);

      if (url.pathname === ACCEPTANCE_STAGE2_PATH) {
        return handleAcceptanceStage2(request, env);
      }

      const hostApi = await handleHostSessionApi(request, env, url);
      if (hostApi) return hostApi;

      if (url.pathname.startsWith('/api/')) {
        const official = await handleOfficialApi(request, env, url);
        if (official) return official;
        return reply({ error: 'not found' }, 404);
      }

      const sessionMatch = url.pathname.match(/^\/s\/([0-9a-f]{48})$/);
      if (sessionMatch) return serveSessionPage(request, env, sessionMatch[1]);

      return env.ASSETS.fetch(request);
    } catch (error) {
      return reply({ error: String(error?.message || error) }, 400);
    }
  },
};
