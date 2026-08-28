# ChatGPT Host Entry Point

Use this file only when a PPT/PPTX task enters PPT Master Studio. It adapts the ChatGPT host to the official PPT Master Harness; it does not redefine PPT authoring workflow.

## 1. Classify

- `RESUME` only when the user explicitly continues an existing Studio project or supplies `project_state.json` / a valid portable recovery bundle for continuation.
- Otherwise use `NEW`. Ordinary PPTX/PDF/DOCX/images/source ZIPs are inputs, not resume evidence.

## 2. Obtain the pinned Harness

For `NEW`, resolve the current `studio-main` 40-character SHA in this session, then pin it for the project. For `RESUME`, use the commit already recorded in project state/recovery; never silently upgrade it.

On ChatGPT, GitHub actions may exist through dynamic connector discovery even when they are absent from the initially visible tool list. Before declaring GitHub branch metadata, workflow artifacts, or artifact download unavailable, discover the relevant GitHub connector resources and actually invoke the discovered actions. For a NEW project, the authoritative current SHA is the value returned by current-session `studio-main` **branch metadata**. A code-search result, commit page, release tag, cached Web/search result, old chat value, or remembered SHA is not current branch metadata and must not define the pin. If connector branch metadata succeeds, do not replace it with a different Web/search value.

After pinning the SHA, discover workflow/artifact actions and look for the `ppt-master-studio-runtime` artifact on a Studio Runtime Release run whose `head_sha` exactly matches the pin. If a matching non-expired artifact exists and an artifact-download action is available, call that download action before considering artifact materialization unavailable. Do not report `artifact_download: unavailable/not exposed` merely because it was not preloaded.

Use host-native connector/Web/file-download capabilities only; execution-container networking (`git`, `curl`, `wget`, Python/Node HTTP) is not a substitute for Harness resolution/materialization.

Detailed host-only resolution/materialization rules are in `studio/enforcement/PPT_MASTER_HOST_CAPABILITY_RULES.md`. Load that file only while resolving or materializing the Harness.

## 3. Enter official PPT Master

After the exact Harness is local and verified:

1. Read `skills/ppt-master/SKILL.md`.
2. Run its `attribution_guard.py` exactly as required.
3. Read `skills/ppt-master/workflows/routing.md` and select exactly one top-level route.
4. Follow the selected official route. Load only that route and supporting documents it explicitly triggers.

Do not preload Studio workflow/template/UI/motion/QA policy because the official Harness owns those concerns.

## 4. ChatGPT Host adapters

Load an adapter only when the active official route reaches its surface. A Host adapter may change transport or persistence; it may not invent a second PPT workflow, Gate schema, template policy, image policy, motion policy, recovery policy, or QA authority.

### Stage 1 / Stage 2 — Cloudflare-hosted official Confirm UI

Prefer the **official pinned Confirm UI frontend** hosted through Cloudflare. Load `studio/host/cloudflare/HOSTED_UI.json` and resolve the immutable Worker URL for the project's pinned 40-hex commit with `studio/host/cloudflare/hosted_url.py`; never silently use a newer `latest` Hosted UI for a RESUME project.

Cloudflare is transport only. A remote `/api/confirm` response is `captured-not-validated` until the captured payload has passed through the pinned local official `skills/ppt-master/scripts/confirm_ui/server.py` implementation and that implementation has written the normal official receipts.

Use one of these Host transport paths without changing official Stage ordering:

- **Runtime outbound HTTPS available:** `studio/host/cloudflare/hosted_confirm_bridge.py` may mirror the official local `/api/session` + `/api/recommendations`, open the short Hosted session, pull captures, and replay them unchanged to the local official `/api/confirm`.
- **Runtime outbound HTTPS unavailable but host-native Web GET is available:** use `studio/host/cloudflare/hosted_confirm_handoff.py bootstrap-project`. It derives the browser-ready snapshot directly from the pinned official Flask API, gzip-compresses it into a browser handoff, and records the host-known session identity. After the user confirms, fetch the returned `response_url` with host-native Web GET, materialize that JSON locally, and run `apply-response --stage stage1`. After the official Harness completes template selection/application and Stage-2 recommendations are actually ready, run `advance-project`; after final confirmation fetch the same response URL and run `apply-response --stage stage2`.

The browser handoff erases its bearer fragment before entering `/s/<session>`, and confirmation leaves the visible URL short. Do not ask the user to copy a token, long JSON URL, or confirmation JSON when the host-native capture path is working.

### Executor Live Preview / Deck Review — Cloudflare-hosted official SVG Editor

The official Harness still owns Executor Live Preview and its local `skills/ppt-master/scripts/svg_editor/server.py` behavior. When the execution Runtime actually has outbound HTTPS, `studio/host/cloudflare/hosted_editor_bridge.py` may mirror current `svg_output/`, `images/`, and `assets/` to the immutable commit-bound Worker so the user can operate the **official pinned SVG Editor frontend** remotely.

Remote edits and annotations are only `captured-not-applied`. Pull them back through the bridge and replay them through the pinned local official SVG Editor API; only the local official server may write authoritative `svg_output`. If the remote session is still open, resync the locally applied result so the same page refreshes from authority.

If Runtime outbound HTTPS is unavailable, do not claim that the Hosted SVG Editor is synchronized and do not expose a stale/test Hosted editor. Preserve the official local Live Preview behavior and continue under the official route's own failure/fallback semantics.

There is **no separate Studio Motion Review page**. Motion remains entirely under the official Harness and appears only when its official route requires it.

### Frozen legacy transports

Interactive Code Block mini-app and Studio static-UI implementations remain repository history/experimental fallback source, but v3.4.x does not load or ship them as the default ChatGPT Runtime interaction path. Do not prefer them over the Hosted official UI.

### Human-confirmation invariant

A confirmation-surface failure may change only the transport, never the owner of the decision. Unless the user explicitly delegated that confirmation, switching from Hosted page to ordinary chat is a blocking human gate: present the current official Gate's unresolved confirmation items, wait for an explicit user confirmation or revision, and only then persist/continue through the official Harness. A fallback notice, recommendation summary, silence, Cloudflare capture acknowledgment, or assistant-authored choice is not user confirmation. Preserve any already-persisted valid official receipt exactly as the official route requires.

If required bootstrap material cannot be resolved or materialized after the supported host paths are genuinely exhausted, fail closed. Never fall back to generic slide authoring.
