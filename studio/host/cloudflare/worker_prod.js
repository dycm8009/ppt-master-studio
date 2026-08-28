import worker from './worker.js';
export { HostedSession } from './worker.js';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    // Manual acceptance fixtures are deliberately unreachable on production.
    if (url.pathname.startsWith('/accept/')) {
      return new Response(JSON.stringify({ error: 'not found' }), {
        status: 404,
        headers: {
          'content-type': 'application/json; charset=utf-8',
          'cache-control': 'no-store',
        },
      });
    }
    return worker.fetch(request, env, ctx);
  },
};
