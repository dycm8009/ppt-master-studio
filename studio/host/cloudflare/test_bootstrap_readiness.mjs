import { createHostedSessionWithRetry } from './public/bootstrap.js';

const session = '2'.repeat(48);
const hostKey = '3'.repeat(64);
const harnessCommit = '4'.repeat(40);
const handoff = {
  session,
  host_key: hostKey,
  payload: {
    schema: 'ppt-master-hosted-official-bootstrap/v1',
    harness_commit: harnessCommit,
    api_snapshot: {
      session: { status: 'active' },
      recommendations: { stage: 'stage1' },
    },
  },
};

function jsonResponse(value, status) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

async function retryThenCreate() {
  const calls = [];
  const retries = [];
  globalThis.fetch = async (path, init = {}) => {
    calls.push([path, init.method || 'GET']);
    if (calls.length === 1) {
      return jsonResponse({ error: 'internal error; reference = readiness-test' }, 400);
    }
    return jsonResponse({
      schema: 'ppt-master-hosted-official-session-created/v2',
      session,
      path: `/s/${session}`,
      harness_commit: harnessCommit,
    }, 201);
  };
  const result = await createHostedSessionWithRetry(handoff, {
    retryDelays: [0, 0],
    sleep: async () => {},
    onRetry: event => retries.push(event),
  });
  if (result.session !== session || calls.length !== 3 || retries.length !== 1) {
    throw new Error(`browser readiness retry failed: ${JSON.stringify({ result, calls, retries })}`);
  }
  if (calls[1][0] !== `/api/sessions/${session}` || calls[2][0] !== '/api/sessions') {
    throw new Error(`browser readiness probe/retry order failed: ${JSON.stringify(calls)}`);
  }
}

async function conflictReconciles() {
  const calls = [];
  globalThis.fetch = async (path, init = {}) => {
    calls.push([path, init.method || 'GET']);
    if ((init.method || 'GET') === 'POST') {
      return jsonResponse({ error: 'session already exists' }, 409);
    }
    return jsonResponse({
      harness_commit: harnessCommit,
      active_stage: 'stage1',
      expires_at: '2099-01-01T00:00:00Z',
    }, 200);
  };
  const result = await createHostedSessionWithRetry(handoff, {
    retryDelays: [0],
    sleep: async () => {},
  });
  if (!result.reconciled || calls.length !== 2 || calls[1][0] !== `/api/sessions/${session}`) {
    throw new Error(`browser session reconciliation failed: ${JSON.stringify({ result, calls })}`);
  }
}

async function mismatchedExistingSessionIsRejected() {
  let calls = 0;
  globalThis.fetch = async (_path, init = {}) => {
    calls += 1;
    if ((init.method || 'GET') === 'POST') {
      return jsonResponse({ error: 'session already exists' }, 409);
    }
    return jsonResponse({
      harness_commit: harnessCommit,
      active_stage: 'stage2',
      expires_at: '2099-01-01T00:00:00Z',
    }, 200);
  };
  let failed = false;
  try {
    await createHostedSessionWithRetry(handoff, {
      retryDelays: [0],
      sleep: async () => {},
    });
  } catch (error) {
    failed = error.status === 409;
  }
  if (!failed || calls !== 2) {
    throw new Error(`mismatched existing session was accepted: calls=${calls}`);
  }
}

async function invalidDoesNotRetry() {
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    return jsonResponse({ error: 'invalid payload' }, 400);
  };
  let failed = false;
  try {
    await createHostedSessionWithRetry(handoff, {
      retryDelays: [0, 0, 0],
      sleep: async () => {},
    });
  } catch (error) {
    failed = error.status === 400 && error.retryable === false;
  }
  if (!failed || calls !== 1) {
    throw new Error(`non-retryable browser error was retried: calls=${calls}`);
  }
}

const originalFetch = globalThis.fetch;
try {
  await retryThenCreate();
  await conflictReconciles();
  await mismatchedExistingSessionIsRejected();
  await invalidDoesNotRetry();
} finally {
  globalThis.fetch = originalFetch;
}

console.log('Hosted browser-bootstrap readiness retry: passed');
