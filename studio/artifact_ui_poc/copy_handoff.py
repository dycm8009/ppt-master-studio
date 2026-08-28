from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CopyHandoffSpec:
    root_id: str
    capture_property: str
    model_marker: str


SPECS = {
    "stage1": CopyHandoffSpec(
        root_id="pm-stage1-real",
        capture_property="__pptMasterStage1Capture",
        model_marker='id="pm-s1-model"',
    ),
    "stage2": CopyHandoffSpec(
        root_id="pm-stage2-parity",
        capture_property="__pptMasterStage2Capture",
        model_marker='id="pm-s2-model"',
    ),
    "deck-review": CopyHandoffSpec(
        root_id="pm-deck-real",
        capture_property="__pptMasterDeckReviewCapture",
        model_marker='id="pm-dr-model"',
    ),
    "motion-review": CopyHandoffSpec(
        root_id="pm-motion-parity",
        capture_property="__pptMasterMotionReviewCapture",
        model_marker='id="pm-motion-model"',
    ),
}


def add_copy_and_continue(content: str, surface: str) -> str:
    """Add the zero-interpretation fallback handoff to an inline artifact fragment.

    The host currently exposes no artifact -> assistant callback. This enhancer keeps
    the canonical payload unchanged and only makes the existing manual handoff one
    action: copy, paste, send.

    The chat artifact host has been empirically more reliable with a single script
    element, so this function injects a second IIFE *inside* the existing script tag
    instead of adding another script element.
    """
    spec = SPECS.get(surface)
    if spec is None:
        raise ValueError(f"unsupported copy handoff surface: {surface}")
    if content.count("<script") != 1 or content.count("</script>") != 1:
        raise ValueError("copy handoff enhancer requires exactly one script element")

    # Stage 2 already has the official-parity copy panel in its renderer. Keep it.
    if "复制并继续" in content:
        return content

    marker = spec.model_marker
    marker_index = content.find(marker)
    if marker_index < 0:
        raise ValueError(f"artifact fragment is missing model marker for {surface}")
    textarea_start = content.rfind("<textarea", 0, marker_index + len(marker))
    if textarea_start < 0:
        raise ValueError(f"artifact fragment cannot locate model textarea for {surface}")

    panel = '''<div id="pm-copy-handoff" class="hidden" style="margin-top:12px;border:1px solid var(--viz-accent);background:var(--viz-accent-bg);border-radius:11px;padding:10px">
  <div style="font-size:13px;font-weight:700">Canonical JSON 已冻结</div>
  <div style="font-size:11px;color:var(--viz-muted);margin-top:3px">点击“复制并继续”，然后粘贴到聊天并发送；validator 仍是唯一 accepted authority。</div>
  <textarea id="pm-copy-output" readonly spellcheck="false" style="width:100%;min-height:108px;margin-top:8px;border:1px solid var(--viz-border);background:var(--viz-panel);color:var(--viz-text);border-radius:9px;padding:8px;font:11px ui-monospace,monospace;resize:vertical"></textarea>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:8px"><button id="pm-copy-button" type="button" style="min-height:40px;border-radius:9px;padding:8px 12px;font-size:13px;font-weight:700;cursor:pointer;border:1px solid var(--viz-accent);background:var(--viz-accent);color:white">复制并继续</button><span id="pm-copy-status" style="font-size:11px;color:var(--viz-muted)"></span></div>
</div>
'''
    content = content[:textarea_start] + panel + content[textarea_start:]

    injection = f'''
;(()=>{{
  const host=document.getElementById({spec.root_id!r});
  if(!host||host.dataset.copyHandoffReady==='1')return;
  host.dataset.copyHandoffReady='1';
  const panel=host.querySelector('#pm-copy-handoff');
  const output=host.querySelector('#pm-copy-output');
  const button=host.querySelector('#pm-copy-button');
  const status=host.querySelector('#pm-copy-status');
  function capture(){{return host[{spec.capture_property!r}]||null}}
  function sync(){{
    const payload=capture();
    const ready=host.dataset.captureStatus==='captured'&&!!payload;
    panel?.classList.toggle('hidden',!ready);
    if(ready&&output)output.value=JSON.stringify(payload,null,2);
    if(!ready&&output)output.value='';
    if(!ready&&status)status.textContent='';
  }}
  async function copy(){{
    const payload=capture();
    if(!payload)return;
    const raw=JSON.stringify(payload,null,2);
    if(output)output.value=raw;
    try{{
      if(!navigator.clipboard?.writeText)throw new Error('clipboard unavailable');
      await navigator.clipboard.writeText(raw);
      if(status)status.textContent='已复制；粘贴到聊天并发送即可。';
    }}catch(_err){{
      if(output){{output.focus();output.select();}}
      try{{document.execCommand?.('copy')}}catch(_ignored){{}}
      if(status)status.textContent='已选择/尝试复制；请粘贴到聊天。';
    }}
  }}
  button?.addEventListener('click',copy);
  new MutationObserver(sync).observe(host,{{attributes:true,attributeFilter:['data-capture-status']}});
  host.addEventListener('click',()=>setTimeout(sync,0));
  sync();
}})();
'''
    script_end = content.rfind("</script>")
    return content[:script_end] + injection + content[script_end:]
