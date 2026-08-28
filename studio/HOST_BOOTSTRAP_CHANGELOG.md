# Host Bootstrap Changelog

## v3.2.5

This patch reduces fresh-chat routing ambiguity by shrinking ChatGPT Project Instructions into a router-only contract.

- Any PPT/PPTX/slide-deck/presentation task is classified as `PPT_MASTER_TASK` immediately; users no longer need to say “初始化环境”.
- NEW/RESUME classification happens before bootstrap: only explicit continuation or valid project-state/recovery evidence becomes RESUME; ordinary PPTX/PDF/source ZIP/handoff inputs remain NEW.
- Host-mandated slide/artifact handoff may occur, but generic/system slides are never an authoring fallback; PPT Master bootstrap must take over immediately after the handoff.
- Project Instructions now carry only routing, bootstrap, source-authority and UI-entry rules. Detailed workflow/template/enforcement/regression/host behavior is loaded from the pinned Studio commit instead of being duplicated in the Project prompt.
- Chat-inline artifact UI remains artifact-first. Project Instructions point to the pinned repo contracts rather than duplicating direct-response serialization details that can drift across patch releases.
- `studio_version` is `3.2.5`; project-state/recovery contract remains compatible with `3.2.0`.

## v3.2.1

This patch fixes a serverless-host bootstrap ambiguity discovered in a fresh ChatGPT conversation.

- Separates NEW project startup from RESUME/recovery startup.
- NEW projects never require `*.ppt-recovery.zip`.
- SHA resolution order is GitHub Connector first, then public GitHub Web/API fallback.
- Ordinary source/handoff ZIPs are never treated as Recovery Bundles unless they contain a supported `PPT_MASTER_RECOVERY_MANIFEST.json`.
- Stable `studio-main` pushes automatically publish a commit-bound Runtime Release ZIP so a fresh host can materialize and execute the exact Harness commit without a manually uploaded ZIP.
- Runtime Release ZIPs are executable Harness distributions, not project recovery authority.
- Project-state/recovery schema remains compatible with the v3.2.0 contract; this patch changes host bootstrap behavior rather than project evidence semantics.
