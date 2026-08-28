(function () {
  'use strict';

  const CAPTURE_PREFIX = '#ppt-master-official-captured=';
  const MAX_HANDOFF_BYTES = 131072;
  const tokenMatch = location.pathname.match(/^\/s\/([0-9a-f]{48})$/);
  const session = tokenMatch ? tokenMatch[1] : null;
  if (!session) return;

  function encodeBase64UrlUtf8(text) {
    const bytes = new TextEncoder().encode(text);
    let binary = '';
    for (let i = 0; i < bytes.length; i += 0x4000) {
      binary += String.fromCharCode(...bytes.subarray(i, i + 0x4000));
    }
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
  }

  function encodeEnvelope(value) {
    const json = JSON.stringify(value);
    const size = new TextEncoder().encode(json).byteLength;
    if (size > MAX_HANDOFF_BYTES) throw new Error(`capture handoff exceeds ${MAX_HANDOFF_BYTES} bytes`);
    return encodeBase64UrlUtf8(json);
  }

  function captureHash(payload) {
    const stage = payload && payload.stage === 'stage1' ? 'stage1' : 'stage2';
    const hostKey = sessionStorage.getItem(`ppt-master-host-key:${session}`) || null;
    return `${CAPTURE_PREFIX}${encodeEnvelope({
      schema: 'ppt-master-hosted-official-browser-capture/v1',
      status: 'captured-not-validated',
      harness_status: 'not-validated',
      session,
      host_key: hostKey,
      stage,
      response: payload,
      captured_at: new Date().toISOString(),
    })}`;
  }

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
      ? 'Stage 1 已捕获。请返回聊天，让 PPT Master Harness 验证并准备 Stage 2；此页面会保留当前 session。'
      : 'Stage 2 已捕获。请返回聊天，让 PPT Master Harness 完成最终验证并继续。';
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
        history.replaceState(null, '', location.pathname + location.search + captureHash(payload));
        showHandoff(stage);
      } catch (error) {
        console.error('PPT Master hosted capture handoff failed:', error);
      }
    }
    return response;
  };
})();
