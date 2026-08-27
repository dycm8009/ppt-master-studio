import { McpServer } from '@modelcontextprotocol/server';
import { createMcpHandler } from 'agents/mcp/server';
import { z } from 'zod';
import { makeToken } from './core.js';

const SURFACE_SCHEMA = z.enum(['stage1', 'stage2', 'deck-review', 'motion-review']);
const TOKEN_SCHEMA = z.string().regex(/^[0-9a-f]{48}$/, 'session must be a 48-character lowercase hex token');
const PAYLOAD_SCHEMA = z.record(z.string(), z.unknown());

function resultJson(value, isError = false) {
  return {
    ...(isError ? { isError: true } : {}),
    content: [{ type: 'text', text: JSON.stringify(value) }]
  };
}

function ensureSessions(env) {
  if (!env?.SESSIONS || typeof env.SESSIONS.getByName !== 'function') {
    throw new Error('SESSIONS Durable Object binding missing');
  }
  return env.SESSIONS;
}

export function createConfirmMcpServer(env, origin) {
  const server = new McpServer({
    name: 'PPT Master Hosted Confirm',
    version: '0.3.0'
  });

  server.registerTool(
    'create_confirm_session',
    {
      title: 'Create PPT confirmation session',
      description:
        'Create a temporary Hosted Confirm session from a PPT Master Harness-derived surface payload. Returns a confirm_url for the user. This tool never creates an accepted Harness receipt.',
      inputSchema: {
        surface: SURFACE_SCHEMA,
        payload: PAYLOAD_SCHEMA
      },
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: false
      }
    },
    async ({ surface, payload }) => {
      try {
        const sessions = ensureSessions(env);
        const token = makeToken();
        const created = await sessions.getByName(token).createSession(surface, payload);
        if (!created?.ok) {
          return resultJson(
            { status: 'error', error: created?.error || 'session create failed' },
            true
          );
        }
        return resultJson({
          schema: 'ppt-master-chatgpt-host-session/v1',
          status: 'created',
          session: token,
          surface: created.record.surface,
          confirm_url: `${origin}/s/${token}`,
          expires_at: created.record.expires_at,
          harness_status: 'not-validated'
        });
      } catch (error) {
        return resultJson({ status: 'error', error: String(error?.message || error) }, true);
      }
    }
  );

  server.registerTool(
    'get_confirm_session',
    {
      title: 'Get PPT confirmation session status',
      description:
        'Read the state of a Hosted Confirm session without returning its private payload. Use this to check whether the user has captured a response.',
      inputSchema: { session: TOKEN_SCHEMA },
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false
      }
    },
    async ({ session }) => {
      try {
        const recordResult = await ensureSessions(env).getByName(session).getSession();
        if (!recordResult?.ok) {
          return resultJson({
            schema: 'ppt-master-chatgpt-host-session-status/v1',
            status: 'missing-or-expired',
            session
          });
        }
        const record = recordResult.record;
        return resultJson({
          schema: 'ppt-master-chatgpt-host-session-status/v1',
          status: record.response ? 'captured' : 'open',
          session,
          surface: record.surface,
          confirm_url: `${origin}/s/${session}`,
          expires_at: record.expires_at,
          response_available: Boolean(record.response),
          harness_status: 'not-validated'
        });
      } catch (error) {
        return resultJson({ status: 'error', error: String(error?.message || error) }, true);
      }
    }
  );

  server.registerTool(
    'get_confirm_response',
    {
      title: 'Get captured PPT confirmation response',
      description:
        'Return the user-confirmed response for a Hosted Confirm session. If the user has not confirmed yet, returns status=pending. The caller must still run the local PPT Master Harness validator before treating the response as accepted.',
      inputSchema: { session: TOKEN_SCHEMA },
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false
      }
    },
    async ({ session }) => {
      try {
        const recordResult = await ensureSessions(env).getByName(session).getSession();
        if (!recordResult?.ok) {
          return resultJson({
            schema: 'ppt-master-chatgpt-host-response/v1',
            status: 'missing-or-expired',
            session
          });
        }
        const record = recordResult.record;
        if (!record.response) {
          return resultJson({
            schema: 'ppt-master-chatgpt-host-response/v1',
            status: 'pending',
            session,
            surface: record.surface,
            expires_at: record.expires_at,
            harness_status: 'not-validated'
          });
        }
        return resultJson({
          schema: 'ppt-master-chatgpt-host-response/v1',
          status: 'captured',
          session,
          surface: record.surface,
          response: record.response,
          captured_at: record.captured_at,
          harness_status: 'not-validated'
        });
      } catch (error) {
        return resultJson({ status: 'error', error: String(error?.message || error) }, true);
      }
    }
  );

  return server;
}

export function handleMcp(request, env, ctx) {
  const origin = new URL(request.url).origin;
  return createMcpHandler(() => createConfirmMcpServer(env, origin), {
    route: '/mcp'
  })(request, env, ctx);
}
