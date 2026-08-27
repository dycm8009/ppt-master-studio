import assert from 'node:assert/strict';
import {handleApi,SESSION_TTL_SECONDS} from './worker.js';

class MemoryKV {
  constructor(){this.map=new Map();this.puts=[]}
  async put(k,v,opts){this.map.set(k,v);this.puts.push({k,opts})}
  async get(k){return this.map.get(k)??null}
}

const env={SESSIONS:new MemoryKV()};
const post=(url,body)=>new Request(url,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});

const created=await handleApi(post('https://poc.example/api/sessions',{surface:'stage1',payload:{recommendation_sha256:'a'.repeat(64),options_sha256:'b'.repeat(64),recommendation:{audience:'工程团队'}}}),env);
assert.equal(created.status,201);
const c=await created.json();
assert.match(c.session,/^[0-9a-f]{48}$/);
assert.equal(c.surface,'stage1');
assert.equal(env.SESSIONS.puts[0].opts.expirationTtl,SESSION_TTL_SECONDS);

const got=await handleApi(new Request(`https://poc.example/api/sessions/${c.session}`),env);
assert.equal(got.status,200);
const session=await got.json();
assert.equal(session.schema,'ppt-master-hosted-session/v1');
assert.equal(session.status,'open');
assert.equal(session.payload.recommendation.audience,'工程团队');

const response={schema:'ppt-master-chat-confirm/v1',surface:'stage1',status:'user-confirmed',recommendation_sha256:'a'.repeat(64),options_sha256:'b'.repeat(64),values:{stage:'stage1'}};
const cap=await handleApi(post(`https://poc.example/api/sessions/${c.session}/response`,response),env);
assert.equal(cap.status,200);
const ack=await cap.json();
assert.equal(ack.status,'captured-not-validated');

const fetched=await handleApi(new Request(`https://poc.example/api/sessions/${c.session}/response`),env);
assert.equal(fetched.status,200);
const fr=await fetched.json();
assert.deepEqual(fr.response,response);

const bad=await handleApi(post(`https://poc.example/api/sessions/${c.session}/response`,{surface:'stage2'}),env);
assert.equal(bad.status,400);

console.log('hosted ui poc transport: passed');
