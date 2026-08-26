# Host Bootstrap Changelog

## v3.2.1

This patch fixes a serverless-host bootstrap ambiguity discovered in a fresh ChatGPT conversation.

- Separates NEW project startup from RESUME/recovery startup.
- NEW projects never require `*.ppt-recovery.zip`.
- SHA resolution order is GitHub Connector first, then public GitHub Web/API fallback.
- Ordinary source/handoff ZIPs are never treated as Recovery Bundles unless they contain a supported `PPT_MASTER_RECOVERY_MANIFEST.json`.
- Stable `studio-main` pushes automatically publish a commit-bound Runtime Release ZIP so a fresh host can materialize and execute the exact Harness commit without a manually uploaded ZIP.
- Runtime Release ZIPs are executable Harness distributions, not project recovery authority.
- Project-state/recovery schema remains compatible with the v3.2.0 contract; this patch changes host bootstrap behavior rather than project evidence semantics.
