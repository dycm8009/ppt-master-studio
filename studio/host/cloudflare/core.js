export const SESSION_TTL_SECONDS = 86400;
export const BOOTSTRAP_SCHEMA = 'ppt-master-hosted-official-bootstrap/v1';
export const RECORD_SCHEMA = 'ppt-master-hosted-official-session/v1';

export function jsonHeaders(extra = {}) {
  return {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
    ...extra,
  };
}

export function reply(data, status = 200, extra = {}) {
  return new Response(JSON.stringify(data), { status, headers: jsonHeaders(extra) });
}

export function makeToken(bytes = 24) {
  const value = new Uint8Array(bytes);
  crypto.getRandomValues(value);
  return Array.from(value, x => x.toString(16).padStart(2, '0')).join('');
}

export function validToken(value) {
  return /^[0-9a-f]{48}$/.test(String(value || ''));
}

export function validHostKey(value) {
  return /^[0-9a-f]{64}$/.test(String(value || ''));
}

function assertObject(value, message) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(message);
  return value;
}

function assertBootstrap(payload) {
  assertObject(payload, 'payload object required');
  if (payload.schema !== BOOTSTRAP_SCHEMA) throw new Error('unsupported hosted bootstrap schema');
  if (!/^[0-9a-f]{40}$/.test(String(payload.harness_commit || ''))) {
    throw new Error('harness_commit must be a full 40-hex commit');
  }
  const snapshot = assertObject(payload.api_snapshot, 'api_snapshot object required');
  assertObject(snapshot.session, 'api_snapshot.session object required');
  const recommendations = assertObject(snapshot.recommendations, 'api_snapshot.recommendations object required');
  if (!['stage1', 'stage2'].includes(String(recommendations.stage || ''))) {
    throw new Error('recommendations.stage must be stage1 or stage2');
  }
  return payload;
}

export class OfficialSessionStore {
  constructor(storage, now = () => Date.now()) {
    this.storage = storage;
    this.now = now;
  }

  async _load({ allowClosed = true } = {}) {
    const record = await this.storage.get('record');
    if (!record) return null;
    if (Date.parse(record.expires_at) <= this.now()) {
      await this.storage.deleteAll();
      return null;
    }
    if (!allowClosed && record.status === 'closed') return null;
    return record;
  }

  async _checkHost(hostKey) {
    const stored = await this.storage.get('host_key');
    return validHostKey(hostKey) && hostKey === stored;
  }

  async create(payload) {
    const source = assertBootstrap(payload);
    if (await this._load()) return { ok: false, status: 409, error: 'session already exists' };
    const now = new Date(this.now());
    const expiresAt = now.getTime() + SESSION_TTL_SECONDS * 1000;
    const record = {
      schema: RECORD_SCHEMA,
      harness_commit: source.harness_commit,
      status: 'open',
      active_stage: source.api_snapshot.recommendations.stage,
      api_snapshot: source.api_snapshot,
      captures: [],
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
      expires_at: new Date(expiresAt).toISOString(),
    };
    await this.storage.put('record', record);
    await this.storage.setAlarm(expiresAt);
    return { ok: true, record };
  }

  async get() {
    const record = await this._load();
    return record ? { ok: true, record } : { ok: false, status: 404, error: 'session missing or expired' };
  }

  async getOfficial(pathname) {
    const record = await this._load();
    if (!record) return { ok: false, status: 404, error: 'session missing or expired' };
    if (pathname === '/api/session') return { ok: true, value: record.api_snapshot.session };
    if (pathname === '/api/recommendations') return { ok: true, value: record.api_snapshot.recommendations };
    return { ok: false, status: 404, error: 'unsupported session API' };
  }

  async captureConfirm(payload) {
    const record = await this._load({ allowClosed: false });
    if (!record) return { ok: false, status: 404, error: 'session missing, closed or expired' };
    assertObject(payload, 'confirm payload object required');
    const stage = String(record.active_stage || '');
    const capturedAt = new Date(this.now()).toISOString();
    record.captures.push({ stage, payload, captured_at: capturedAt });
    record.status = stage === 'stage1' ? 'waiting-agent' : 'captured';
    if (stage === 'stage1') {
      record.api_snapshot.session = {
        ...record.api_snapshot.session,
        status: 'waiting_agent',
        current_stage: 'stage1',
      };
    }
    record.updated_at = capturedAt;
    await this.storage.put('record', record);
    return {
      ok: true,
      value: {
        schema: 'ppt-master-hosted-official-capture-ack/v1',
        status: 'captured-not-validated',
        harness_status: 'not-validated',
        stage,
        captured_at: capturedAt,
      },
    };
  }

  async advance(hostKey, snapshot) {
    const record = await this._load({ allowClosed: false });
    if (!record) return { ok: false, status: 404, error: 'session missing, closed or expired' };
    if (!await this._checkHost(hostKey)) {
      return { ok: false, status: 403, error: 'invalid host key' };
    }
    assertObject(snapshot, 'api_snapshot object required');
    assertObject(snapshot.session, 'api_snapshot.session object required');
    const recommendations = assertObject(snapshot.recommendations, 'api_snapshot.recommendations object required');
    if (recommendations.stage !== 'stage2') {
      return { ok: false, status: 400, error: 'host advance currently accepts stage2 only' };
    }
    record.api_snapshot = snapshot;
    record.active_stage = 'stage2';
    record.status = 'open';
    record.updated_at = new Date(this.now()).toISOString();
    await this.storage.put('record', record);
    return { ok: true, record };
  }

  async setHostKey(hostKey) {
    if (!validHostKey(hostKey)) throw new Error('invalid generated host key');
    await this.storage.put('host_key', hostKey);
  }

  async close(reason = 'confirmed') {
    const record = await this._load();
    if (!record) return { ok: false, status: 404, error: 'session missing or expired' };
    record.status = 'closed';
    record.closed_reason = String(reason || 'confirmed');
    record.updated_at = new Date(this.now()).toISOString();
    await this.storage.put('record', record);
    return { ok: true, record };
  }

  async closeHost(hostKey, reason = 'host-complete') {
    const record = await this._load();
    if (!record) return { ok: false, status: 404, error: 'session missing or expired' };
    if (!await this._checkHost(hostKey)) {
      return { ok: false, status: 403, error: 'invalid host key' };
    }
    return this.close(reason);
  }

  async getCaptured() {
    const record = await this._load();
    if (!record) return { ok: false, status: 404, error: 'session missing or expired' };
    return {
      ok: true,
      value: {
        schema: 'ppt-master-hosted-official-captured/v1',
        status: 'captured-not-validated',
        harness_status: 'not-validated',
        harness_commit: record.harness_commit,
        active_stage: record.active_stage,
        captures: record.captures,
        session_status: record.status,
      },
    };
  }

  async expire() {
    await this.storage.deleteAll();
  }
}
