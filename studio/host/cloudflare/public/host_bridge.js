(function () {
  'use strict';

  const RETURN_SCHEMA = 'ppt-master-hosted-confirm-return/v1';
  const tokenMatch = location.pathname.match(/^\/s\/([0-9a-f]{48})$/);
  const session = tokenMatch ? tokenMatch[1] : null;
  if (!session) return;

  function stageLabel(stage) {
    return stage === 'stage1' ? 'Stage 1' : 'Stage 2';
  }

  function createElement(tag, options = {}) {
    const element = document.createElement(tag);
    if (options.id) element.id = options.id;
    if (options.text) element.textContent = options.text;
    if (options.className) element.className = options.className;
    if (options.type) element.type = options.type;
    if (options.value !== undefined) element.value = options.value;
    if (options.readOnly !== undefined) element.readOnly = options.readOnly;
    if (options.rows !== undefined) element.rows = options.rows;
    if (options.title) element.title = options.title;
    if (options.onClick) element.addEventListener('click', options.onClick);
    if (options.style) Object.assign(element.style, options.style);
    return element;
  }

  function panel() {
    let root = document.getElementById('ppt-master-hosted-handoff');
    if (!root) {
      root = createElement('section', {
        id: 'ppt-master-hosted-handoff',
        style: {
          position: 'fixed',
          left: '18px',
          right: '18px',
          bottom: '18px',
          zIndex: '99999',
          maxWidth: '960px',
          maxHeight: '52vh',
          margin: '0 auto',
          overflow: 'auto',
          padding: '14px',
          borderRadius: '14px',
          background: 'rgba(20,20,23,.98)',
          border: '1px solid rgba(255,255,255,.18)',
          color: '#f5f5f5',
          font: '13px/1.45 Inter,system-ui,sans-serif',
          boxShadow: '0 14px 34px rgba(0,0,0,.34)',
        },
      });
      document.body.appendChild(root);
    }
    return root;
  }

  function clearPanel(root) {
    if (typeof root.replaceChildren === 'function') {
      root.replaceChildren();
      return;
    }
    while (root.firstChild) root.removeChild(root.firstChild);
  }

  async function copyText(text, textarea, button, status) {
    try {
      if (!navigator.clipboard || typeof navigator.clipboard.writeText !== 'function') {
        throw new Error('Clipboard API unavailable');
      }
      await navigator.clipboard.writeText(text);
      button.textContent = '已复制确认 JSON';
      status.textContent = '已复制。请返回聊天并粘贴该 JSON。';
      return true;
    } catch (clipboardError) {
      try {
        textarea.focus();
        textarea.select();
        textarea.setSelectionRange?.(0, textarea.value.length);
        if (typeof document.execCommand === 'function' && document.execCommand('copy')) {
          button.textContent = '已复制确认 JSON';
          status.textContent = '已复制。请返回聊天并粘贴该 JSON。';
          return true;
        }
      } catch (fallbackError) {
        console.error('PPT Master hosted copy fallback failed:', fallbackError);
      }
      button.textContent = '复制失败，请手动全选';
      status.textContent = '浏览器未允许自动复制。请从下方文本框全选复制，再返回聊天粘贴。';
      textarea.focus();
      textarea.select();
      return false;
    }
  }

  function validateCapturedResponse(data, stage) {
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      throw new Error('Cloudflare response is not a JSON object');
    }
    if (data.status !== 'captured-not-validated' || data.harness_status !== 'not-validated') {
      throw new Error('Cloudflare response crossed the Harness authority boundary');
    }
    if (!Array.isArray(data.captures) || data.captures.length === 0) {
      throw new Error('Cloudflare response does not contain the captured confirmation');
    }
    const latest = data.captures[data.captures.length - 1];
    if (!latest || latest.stage !== stage || !latest.payload || typeof latest.payload !== 'object') {
      throw new Error(`Cloudflare response does not contain the expected ${stage} capture`);
    }
    return data;
  }

  async function fetchReturnEnvelope(stage) {
    const response = await nativeFetch(`/api/sessions/${session}/response`, {
      method: 'GET',
      headers: { accept: 'application/json' },
      cache: 'no-store',
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `response fetch failed: ${response.status}`);
    validateCapturedResponse(data, stage);
    return {
      schema: RETURN_SCHEMA,
      session,
      stage,
      response: data,
    };
  }

  function renderError(stage, error) {
    const root = panel();
    clearPanel(root);
    root.dataset.status = 'error';
    root.appendChild(createElement('strong', {
      text: `${stageLabel(stage)} 已保存，但确认 JSON 暂时无法读取。`,
    }));
    root.appendChild(createElement('p', {
      text: String(error?.message || error),
      style: { margin: '8px 0', color: '#ffaaa3' },
    }));
    root.appendChild(createElement('button', {
      id: 'ppt-master-hosted-return-retry',
      type: 'button',
      text: '重新获取确认 JSON',
      onClick: () => prepareReturn(stage),
      style: {
        cursor: 'pointer',
        border: '1px solid rgba(255,255,255,.24)',
        borderRadius: '9px',
        padding: '8px 12px',
        background: '#26262b',
        color: '#fff',
      },
    }));
  }

  function renderReturn(stage, envelope) {
    const root = panel();
    clearPanel(root);
    root.dataset.status = 'ready';
    root.dataset.stage = stage;

    const json = JSON.stringify(envelope, null, 2);
    const heading = createElement('strong', {
      text: `${stageLabel(stage)} 已保存。`,
    });
    const instructions = createElement('p', {
      text: '优先点击“复制确认 JSON”，然后返回聊天粘贴。PPT Master Harness 仍会在本地验证该结果；Cloudflare 保存成功不等于 Harness 已接受。',
      style: { margin: '8px 0 10px', color: '#c9c9cf' },
    });
    const status = createElement('div', {
      id: 'ppt-master-hosted-return-status',
      text: '确认 JSON 已生成。',
      style: { marginBottom: '8px', color: '#aeb7ff' },
    });
    const textarea = createElement('textarea', {
      id: 'ppt-master-hosted-return-json',
      value: json,
      readOnly: true,
      rows: 8,
      title: 'PPT Master Hosted Confirm return JSON',
      style: {
        display: 'block',
        boxSizing: 'border-box',
        width: '100%',
        resize: 'vertical',
        border: '1px solid rgba(255,255,255,.18)',
        borderRadius: '9px',
        padding: '9px',
        background: '#0f0f11',
        color: '#e8e8ec',
        font: '12px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace',
      },
    });
    const controls = createElement('div', {
      style: { display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '10px' },
    });
    const copyButton = createElement('button', {
      id: 'ppt-master-hosted-return-copy',
      type: 'button',
      text: '复制确认 JSON',
      onClick: () => copyText(json, textarea, copyButton, status),
      style: {
        cursor: 'pointer',
        border: '1px solid #747cff',
        borderRadius: '9px',
        padding: '8px 12px',
        background: '#5058d8',
        color: '#fff',
        fontWeight: '600',
      },
    });
    const selectButton = createElement('button', {
      id: 'ppt-master-hosted-return-select',
      type: 'button',
      text: '全选文本',
      onClick: () => {
        textarea.focus();
        textarea.select();
        textarea.setSelectionRange?.(0, textarea.value.length);
        status.textContent = '已全选，请使用系统复制命令。';
      },
      style: {
        cursor: 'pointer',
        border: '1px solid rgba(255,255,255,.24)',
        borderRadius: '9px',
        padding: '8px 12px',
        background: '#26262b',
        color: '#fff',
      },
    });

    controls.appendChild(copyButton);
    controls.appendChild(selectButton);
    root.appendChild(heading);
    root.appendChild(instructions);
    root.appendChild(status);
    root.appendChild(textarea);
    root.appendChild(controls);
  }

  async function prepareReturn(stage) {
    const root = panel();
    clearPanel(root);
    root.dataset.status = 'loading';
    root.appendChild(createElement('strong', {
      text: `${stageLabel(stage)} 已保存，正在生成确认 JSON…`,
    }));
    try {
      const envelope = await fetchReturnEnvelope(stage);
      renderReturn(stage, envelope);
    } catch (error) {
      console.error('PPT Master hosted return preparation failed:', error);
      renderError(stage, error);
    }
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = async function (input, init) {
    const requestUrl = typeof input === 'string' ? input : (input && input.url) || '';
    const method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    const response = await nativeFetch(input, init);

    if (requestUrl === '/api/confirm' && method === 'POST' && response.ok) {
      try {
        let body = init && init.body;
        if (!body && typeof Request !== 'undefined' && input instanceof Request) {
          body = await input.clone().text();
        }
        const payload = typeof body === 'string' ? JSON.parse(body) : body;
        const stage = payload && payload.stage === 'stage1' ? 'stage1' : 'stage2';
        // Preserve the short Cloudflare /s/<session> URL. The page exposes an
        // explicit JSON return contract instead of depending on an implicit
        // ChatGPT browser callback that is not consistently available.
        history.replaceState(null, '', location.pathname + location.search);
        await prepareReturn(stage);
      } catch (error) {
        console.error('PPT Master hosted capture handoff failed:', error);
      }
    }
    return response;
  };
})();
