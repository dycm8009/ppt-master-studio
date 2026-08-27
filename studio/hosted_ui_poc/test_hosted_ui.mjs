import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {handleApiWithNamespace,SessionStore,SESSION_TTL_SECONDS} from './core.js';

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

const here=dirname(fileURLToPath(import.meta.url));
const html=await readFile(join(here,'public/index.html'),'utf8');
assert.match(html,/template_selection:\{mode:'free_design',selection_keys:\[\]\}/);
assert.doesNotMatch(html,/value="templates"/);

console.log('hosted ui durable-object transport: passed');
