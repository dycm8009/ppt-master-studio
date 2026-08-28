(function () {
  'use strict';

  function addHostedBanner() {
    if (document.getElementById('ppt-master-hosted-editor-banner')) return;
    var banner = document.createElement('div');
    banner.id = 'ppt-master-hosted-editor-banner';
    banner.textContent = 'Cloudflare Hosted Mirror · Apply changes captures edits for the pinned Harness; local svg_output remains authoritative until the Harness validates and applies them.';
    banner.style.cssText = [
      'position:fixed',
      'left:50%',
      'bottom:12px',
      'transform:translateX(-50%)',
      'z-index:99999',
      'max-width:min(920px,calc(100vw - 28px))',
      'padding:8px 12px',
      'border-radius:10px',
      'background:rgba(20,20,24,.94)',
      'border:1px solid rgba(255,255,255,.18)',
      'color:#ddd',
      'font:12px/1.4 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
      'box-shadow:0 8px 30px rgba(0,0,0,.3)',
      'pointer-events:none'
    ].join(';');
    document.body.appendChild(banner);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', addHostedBanner);
  else addHostedBanner();
})();
