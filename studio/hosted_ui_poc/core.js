export const SESSION_TTL_SECONDS = 86400;
export const SURFACES = new Set(['stage1','stage2','deck-review','motion-review']);

export function headers(extra={}) {
  return {'content-type':'application/json; charset=utf-8','cache-control':'no-store',...extra};
}

export function reply(data,status=200,extra={}) {
  return new Response(JSON.stringify(data),{status,headers:headers(extra)});
}

export function makeToken() {
  const b=new Uint8Array(24);
  crypto.getRandomValues(b);
  return Array.from(b,x=>x.toString(16).padStart(2,'0')).join('');
}

async function readJson(req) {
  try { return await req.json(); }
  catch { throw new Error('invalid JSON'); }
}

function validToken(t){ return /^[0-9a-f]{48}$/.test(t); }

export class SessionStore {
  constructor(storage, now=()=>Date.now()) {
    this.storage=storage;
    this.now=now;
  }

  async _loadLive() {
    const record=await this.storage.get('record');
    if (!record) return null;
    if (Date.parse(record.expires_at)<=this.now()) {
      await this.storage.deleteAll();
      return null;
    }
    return record;
  }

  async createSession(surface,payload) {
    if (!SURFACES.has(surface)) return {ok:false,status:400,error:'unsupported surface'};
    if (!payload || typeof payload!=='object' || Array.isArray(payload)) return {ok:false,status:400,error:'payload object required'};
    if (await this._loadLive()) return {ok:false,status:409,error:'session already exists'};
    const now=new Date(this.now());
    const expiresAt=now.getTime()+SESSION_TTL_SECONDS*1000;
    const record={schema:'ppt-master-hosted-session/v1',surface,payload,status:'open',created_at:now.toISOString(),expires_at:new Date(expiresAt).toISOString(),response:null};
    await this.storage.put('record',record);
    await this.storage.setAlarm(expiresAt);
    return {ok:true,record};
  }

  async getSession() {
    const record=await this._loadLive();
    return record ? {ok:true,record} : {ok:false,status:404,error:'session missing or expired'};
  }

  async captureResponse(response) {
    const record=await this._loadLive();
    if (!record) return {ok:false,status:404,error:'session missing or expired'};
    if (!response || typeof response!=='object' || Array.isArray(response) || response.surface!==record.surface) {
      return {ok:false,status:400,error:'response surface mismatch'};
    }
    if (record.response) return {ok:false,status:409,error:'response already captured'};
    record.response=response;
    record.status='captured';
    record.captured_at=new Date(this.now()).toISOString();
    await this.storage.put('record',record);
    return {ok:true,record};
  }

  async getResponse() {
    const record=await this._loadLive();
    if (!record) return {ok:false,status:404,error:'session missing or expired'};
    if (!record.response) return {ok:false,status:404,error:'response not captured'};
    return {ok:true,record};
  }

  async expire() {
    await this.storage.deleteAll();
  }
}

export async function handleApiWithNamespace(request,sessions) {
  if (!sessions || typeof sessions.getByName!=='function') return reply({error:'SESSIONS Durable Object binding missing'},500);
  const url=new URL(request.url);

  if (url.pathname==='/api/sessions' && request.method==='POST') {
    const body=await readJson(request);
    if (!SURFACES.has(body.surface)) return reply({error:'unsupported surface'},400);
    if (!body.payload || typeof body.payload!=='object' || Array.isArray(body.payload)) return reply({error:'payload object required'},400);
    const t=makeToken();
    const result=await sessions.getByName(t).createSession(body.surface,body.payload);
    if (!result?.ok) return reply({error:result?.error||'session create failed'},result?.status||500);
    const record=result.record;
    return reply({schema:'ppt-master-hosted-session-created/v1',session:t,surface:record.surface,path:`/s/${t}`,expires_at:record.expires_at},201);
  }

  const m=url.pathname.match(/^\/api\/sessions\/([0-9a-f]{48})(\/response)?$/);
  if (!m || !validToken(m[1])) return reply({error:'not found'},404);
  const stub=sessions.getByName(m[1]);

  if (!m[2] && request.method==='GET') {
    const result=await stub.getSession();
    return result?.ok ? reply(result.record) : reply({error:result?.error||'session missing or expired'},result?.status||404);
  }
  if (m[2] && request.method==='GET') {
    const result=await stub.getResponse();
    if (!result?.ok) return reply({error:result?.error||'response not captured'},result?.status||404);
    const record=result.record;
    return reply({schema:'ppt-master-hosted-captured/v1',surface:record.surface,response:record.response,captured_at:record.captured_at});
  }
  if (m[2] && request.method==='POST') {
    const body=await readJson(request);
    const result=await stub.captureResponse(body);
    if (!result?.ok) return reply({error:result?.error||'capture failed'},result?.status||400);
    const record=result.record;
    return reply({schema:'ppt-master-hosted-capture-ack/v1',status:'captured-not-validated',surface:record.surface,captured_at:record.captured_at});
  }
  return reply({error:'method not allowed'},405,{allow:'GET, POST'});
}
