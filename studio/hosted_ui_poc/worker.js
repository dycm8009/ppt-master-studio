import {DurableObject} from 'cloudflare:workers';
import {SessionStore,handleApiWithNamespace,reply} from './core.js';

export class HostedSession extends DurableObject {
  constructor(ctx,env) {
    super(ctx,env);
    this.store=new SessionStore(this.ctx.storage);
  }

  async createSession(surface,payload) { return this.store.createSession(surface,payload); }
  async getSession() { return this.store.getSession(); }
  async captureResponse(response) { return this.store.captureResponse(response); }
  async getResponse() { return this.store.getResponse(); }
  async alarm() { await this.store.expire(); }
}

export async function handleApi(request,env) {
  return handleApiWithNamespace(request,env?.SESSIONS);
}

export default {
  async fetch(request,env) {
    const url=new URL(request.url);
    if (url.pathname.startsWith('/api/')) {
      try { return await handleApi(request,env); }
      catch (e) { return reply({error:String(e?.message||e)},400); }
    }
    if (url.pathname.match(/^\/s\/[0-9a-f]{48}$/)) {
      // Fetch the root asset internally instead of /index.html. Workers Static
      // Assets canonicalizes /index.html to /, which would redirect the browser
      // and drop the bearer token from the visible /s/<token> URL.
      return env.ASSETS.fetch(new Request(new URL('/',url),request));
    }
    return env.ASSETS.fetch(request);
  }
};
