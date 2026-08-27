export const SESSION_TTL_SECONDS = 86400;
export const SURFACES = new Set(['stage1','stage2','deck-review','motion-review']);

function headers(extra={}) { return {'content-type':'application/json; charset=utf-8','cache-control':'no-store',...extra}; }
function reply(data,status=200,extra={}) { return new Response(JSON.stringify(data),{status,headers:headers(extra)}); }
function token() { const b=new Uint8Array(24); crypto.getRandomValues(b); return Array.from(b,x=>x.toString(16).padStart(2,'0')).join(''); }
async function readJson(req) { try { return await req.json(); } catch { throw new Error('invalid JSON'); } }
function key(t){ return `session:${t}`; }
function validToken(t){ return /^[0-9a-f]{48}$/.test(t); }

export async function handleApi(request, env) {
  const url=new URL(request.url);
  if (!env.SESSIONS) return reply({error:'SESSIONS KV binding missing'},500);

  if (url.pathname==='/api/sessions' && request.method==='POST') {
    const body=await readJson(request);
    if (!SURFACES.has(body.surface)) return reply({error:'unsupported surface'},400);
    if (!body.payload || typeof body.payload!=='object') return reply({error:'payload object required'},400);
    const t=token(); const now=new Date(); const exp=new Date(now.getTime()+SESSION_TTL_SECONDS*1000);
    const record={schema:'ppt-master-hosted-session/v1',surface:body.surface,payload:body.payload,status:'open',created_at:now.toISOString(),expires_at:exp.toISOString(),response:null};
    await env.SESSIONS.put(key(t),JSON.stringify(record),{expirationTtl:SESSION_TTL_SECONDS});
    return reply({schema:'ppt-master-hosted-session-created/v1',session:t,surface:body.surface,path:`/s/${t}`,expires_at:record.expires_at},201);
  }

  const m=url.pathname.match(/^\/api\/sessions\/([0-9a-f]{48})(\/response)?$/);
  if (!m || !validToken(m[1])) return reply({error:'not found'},404);
  const raw=await env.SESSIONS.get(key(m[1]));
  if (!raw) return reply({error:'session missing or expired'},404);
  const record=JSON.parse(raw);

  if (!m[2] && request.method==='GET') return reply(record);
  if (m[2] && request.method==='GET') {
    if (!record.response) return reply({error:'response not captured'},404);
    return reply({schema:'ppt-master-hosted-captured/v1',surface:record.surface,response:record.response,captured_at:record.captured_at});
  }
  if (m[2] && request.method==='POST') {
    const body=await readJson(request);
    if (!body || typeof body!=='object' || body.surface!==record.surface) return reply({error:'response surface mismatch'},400);
    record.response=body; record.status='captured'; record.captured_at=new Date().toISOString();
    const remaining=Math.max(60,Math.floor((Date.parse(record.expires_at)-Date.now())/1000));
    await env.SESSIONS.put(key(m[1]),JSON.stringify(record),{expirationTtl:remaining});
    return reply({schema:'ppt-master-hosted-capture-ack/v1',status:'captured-not-validated',surface:record.surface,captured_at:record.captured_at});
  }
  return reply({error:'method not allowed'},405,{allow:'GET, POST'});
}

export default {
  async fetch(request, env) {
    const url=new URL(request.url);
    if (url.pathname.startsWith('/api/')) {
      try { return await handleApi(request,env); } catch (e) { return reply({error:String(e?.message||e)},400); }
    }
    if (url.pathname.match(/^\/s\/[0-9a-f]{48}$/)) return env.ASSETS.fetch(new Request(new URL('/index.html',url),request));
    return env.ASSETS.fetch(request);
  }
};
