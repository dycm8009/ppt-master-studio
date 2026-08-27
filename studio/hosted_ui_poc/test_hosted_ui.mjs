import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {handleApiWithNamespace,SessionStore,SESSION_TTL_SECONDS} from './core.js';
import {registerPptMasterSiteTools,SITE_TOOL_NAMES} from './public/site-tools.js';

class MemoryStorage {
  constructor(now){this.map=new Map();this.alarm=null;this.deleted=false;this.now=now}
  async put(k,v){this.map.set(k,structuredClone(v))}
  async get(k){const v=this.map.get(k);return v===undefined?undefined:structuredClone(v)}
  async setAlarm(ts){this.alarm=ts}
  async deleteAll(){this.map.clear();this.alarm=null;this.deleted=true}
}

class MemoryNamespace {
  constructor(now){this.now=now;this.objects=new Map()}
  getByName(name){
    if(!this.objects.has(name)){
      const storage=new MemoryStorage(this.now);
      const store=new SessionStore(storage,this.now);
      this.objects.set(name,{storage,store});
    }
    return this.objects.get(name).store;
  }
  object(name){return this.objects.get(name)}
}

let nowMs=Date.parse('2026-08-27T11:00:00.000Z');
const now=()=>nowMs;
const sessions=new MemoryNamespace(now);
const post=(url,body)=>new Request(url,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});

const created=await handleApiWithNamespace(post('https://poc.example/api/sessions',{surface:'stage1',payload:{recommendation_sha256:'a'.repeat(64),options_sha256:'b'.repeat(64),recommendation:{audience:'工程团队'}}}),sessions);
assert.equal(created.status,201);
assert.equal(created.headers.get('cache-control'),'no-store');
const c=await created.json();
assert.match(c.session,/^[0-9a-f]{48}$/);
assert.equal(c.surface,'stage1');
assert.equal(sessions.object(c.session).storage.alarm,nowMs+SESSION_TTL_SECONDS*1000);

const got=await handleApiWithNamespace(new Request(`https://poc.example/api/sessions/${c.session}`),sessions);
assert.equal(got.status,200);
const session=await got.json();
assert.equal(session.schema,'ppt-master-hosted-session/v1');
assert.equal(session.status,'open');
assert.equal(session.payload.recommendation.audience,'工程团队');

const missingResponse=await handleApiWithNamespace(new Request(`https://poc.example/api/sessions/${c.session}/response`),sessions);
assert.equal(missingResponse.status,404);

const mismatch=await handleApiWithNamespace(post(`https://poc.example/api/sessions/${c.session}/response`,{surface:'stage2'}),sessions);
assert.equal(mismatch.status,400);

const response={schema:'ppt-master-chat-confirm/v1',surface:'stage1',status:'user-confirmed',recommendation_sha256:'a'.repeat(64),options_sha256:'b'.repeat(64),values:{stage:'stage1',template_selection:{mode:'free_design',selection_keys:[]}}};
const cap=await handleApiWithNamespace(post(`https://poc.example/api/sessions/${c.session}/response`,response),sessions);
assert.equal(cap.status,200);
const ack=await cap.json();
assert.equal(ack.status,'captured-not-validated');

const duplicate=await handleApiWithNamespace(post(`https://poc.example/api/sessions/${c.session}/response`,response),sessions);
assert.equal(duplicate.status,409);

const fetched=await handleApiWithNamespace(new Request(`https://poc.example/api/sessions/${c.session}/response`),sessions);
assert.equal(fetched.status,200);
const fr=await fetched.json();
assert.deepEqual(fr.response,response);

const badToken=await handleApiWithNamespace(new Request('https://poc.example/api/sessions/not-a-token'),sessions);
assert.equal(badToken.status,404);
const method=await handleApiWithNamespace(new Request(`https://poc.example/api/sessions/${c.session}`,{method:'DELETE'}),sessions);
assert.equal(method.status,405);

nowMs+=SESSION_TTL_SECONDS*1000+1;
const expired=await handleApiWithNamespace(new Request(`https://poc.example/api/sessions/${c.session}`),sessions);
assert.equal(expired.status,404);
assert.equal(sessions.object(c.session).storage.deleted,true);

// Plus / Site Tools Host Bridge contract.
const registered=new Map();
const modelContext={registerTool(tool){registered.set(tool.name,tool)}};
const siteToken='c'.repeat(48);
let capturedReady=false;
let createdNotice=null;
const siteFetch=async (url,opts={})=>{
  const path=new URL(url).pathname;
  if(path==='/api/sessions'&&opts.method==='POST'){
    const body=JSON.parse(opts.body);
    assert.equal(body.surface,'stage1');
    assert.equal(body.payload.recommendation_sha256,'d'.repeat(64));
    return new Response(JSON.stringify({schema:'ppt-master-hosted-session-created/v1',session:siteToken,surface:'stage1',path:`/s/${siteToken}`,expires_at:'2026-08-28T11:00:00.000Z'}),{status:201,headers:{'content-type':'application/json'}});
  }
  if(path===`/api/sessions/${siteToken}`){
    return new Response(JSON.stringify({schema:'ppt-master-hosted-session/v1',surface:'stage1',payload:{secret:'must-not-leak'},status:capturedReady?'captured':'open',expires_at:'2026-08-28T11:00:00.000Z',response:capturedReady?response:null}),{status:200,headers:{'content-type':'application/json'}});
  }
  if(path===`/api/sessions/${siteToken}/response`){
    if(!capturedReady)return new Response(JSON.stringify({error:'response not captured'}),{status:404,headers:{'content-type':'application/json'}});
    return new Response(JSON.stringify({schema:'ppt-master-hosted-captured/v1',surface:'stage1',response,captured_at:'2026-08-27T11:10:00.000Z'}),{status:200,headers:{'content-type':'application/json'}});
  }
  return new Response(JSON.stringify({error:'not found'}),{status:404,headers:{'content-type':'application/json'}});
};

const registration=registerPptMasterSiteTools({modelContext,fetchImpl:siteFetch,origin:'https://poc.example',onCreated:value=>{createdNotice=value}});
assert.equal(registration.available,true);
assert.deepEqual(registration.names,[...SITE_TOOL_NAMES]);
assert.deepEqual([...registered.keys()],[...SITE_TOOL_NAMES]);
assert.equal(registered.get('create_confirm_session').annotations.readOnlyHint,false);
assert.equal(registered.get('get_confirm_session').annotations.readOnlyHint,true);
assert.equal(registered.get('get_confirm_response').annotations.readOnlyHint,true);

const siteCreated=JSON.parse(await registered.get('create_confirm_session').execute({surface:'stage1',payload:{recommendation_sha256:'d'.repeat(64)}}));
assert.equal(siteCreated.status,'created');
assert.equal(siteCreated.confirm_url,`https://poc.example/s/${siteToken}`);
assert.equal(siteCreated.harness_status,'not-validated');
assert.deepEqual(createdNotice,siteCreated);

const siteStatus=JSON.parse(await registered.get('get_confirm_session').execute({session:siteToken}));
assert.equal(siteStatus.status,'open');
assert.equal(siteStatus.response_available,false);
assert.equal('payload' in siteStatus,false);

const pending=JSON.parse(await registered.get('get_confirm_response').execute({session:siteToken}));
assert.equal(pending.status,'pending');
capturedReady=true;
const siteCaptured=JSON.parse(await registered.get('get_confirm_response').execute({session:siteToken}));
assert.equal(siteCaptured.status,'captured');
assert.deepEqual(siteCaptured.response,response);
assert.equal(siteCaptured.harness_status,'not-validated');

const here=dirname(fileURLToPath(import.meta.url));
const html=await readFile(join(here,'public/index.html'),'utf8');
assert.match(html,/Site Tools Host Bridge/);
assert.match(html,/registerPptMasterSiteTools/);
assert.match(html,/template_selection:\{mode:'free_design',selection_keys:\[\]\}/);
assert.doesNotMatch(html,/value="templates"/);

console.log('hosted ui durable-object + site-tools transport: passed');
