(function () {
  'use strict';

  const tokenMatch = location.pathname.match(/^\/s\/([0-9a-f]{48})$/);
  const session = tokenMatch ? tokenMatch[1] : null;
  if (!session) return;

  function showHandoff(stage) {
    let bar = document.getElementById('ppt-master-hosted-handoff');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'ppt-master-hosted-handoff';
      Object.assign(bar.style, {
        position: 'fixed',
        left: '18px',
        right: '18px',
        bottom: '18px',
        zIndex: '99999',
        padding: '11px 14px',
        borderRadius: '12px',
        background: 'rgba(20,20,23,.96)',
        border: '1px solid rgba(255,255,255,.16)',
        color: '#f5f5f5',
        font: '13px/1.45 Inter,system-ui,sans-serif',
        boxShadow: '0 12px 30px rgba(0,0,0,.28)',
      });
      document.body.appendChild(bar);
    }
    bar.textContent = stage === 'stage1'
      ? 'Stage 1 已捕获。请返回聊天，让 PPT Master Harness 获取并验证当前 session 的响应，再准备 Stage 2；此页面会保留当前 session。'
      : 'Stage 2 已捕获。请返回聊天，让 PPT Master Harness 获取并验证当前 session 的响应后继续。';
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = async function (input, init) {
    const requestUrl = typeof input === 'string' ? input : (input && input.url) || '';
    const method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    const response = await nativeFetch(input, init);

    if (requestUrl === '/api/confirm' && method === 'POST' && response.ok) {
      try {
        let body = init && init.body;
        if (!body && input instanceof Request) body = await input.clone().text();
        const payload = typeof body === 'string' ? JSON.parse(body) : body;
        const stage = payload && payload.stage === 'stage1' ? 'stage1' : 'stage2';
        // The Durable Object is the capture transport.  Keep the visible URL at
        // the short /s/<session> path instead of serializing the response into
        // a second browser fragment; the Host already knows this session token.
        history.replaceState(null, '', location.pathname + location.search);
        showHandoff(stage);
      } catch (error) {
        console.error('PPT Master hosted capture notice failed:', error);
      }
    }
    return response;
  };
})();
