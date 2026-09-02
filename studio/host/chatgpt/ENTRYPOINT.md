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

Cloudflare is transport only. A remote `/api/confirm` response is `captured-not-validated` until the captured payload has passed through the pinned local official API core in `skills/ppt-master/scripts/confirm_ui/server.py` and that implementation has written the normal official receipts. The Hosted path invokes this API core headlessly; Flask is optional only for the localhost UI server.

Use one of these Host transport paths without changing official Stage ordering:

- **Runtime outbound HTTPS available:** invoke `studio/host/cloudflare/hosted_confirm_bridge.py open`. It creates the remote session before presentation and returns `transport_mode=direct-session`, with `launch_url` equal to the short `/s/<session>` Cloudflare URL. Present that `launch_url` directly. After confirmation, call the bridge `apply` path; only an actual successful pull-and-apply counts as automatic feedback.
- **Runtime outbound HTTPS unavailable:** invoke `studio/host/cloudflare/hosted_confirm_handoff.py bootstrap-project`. It returns `transport_mode=browser-bootstrap-manual-return`, a Cloudflare `launch_url` containing the compressed bootstrap fragment, the eventual short `session_url`, and `feedback_mode=copy-json`. Present `launch_url` directly as a normal Cloudflare hyperlink; the visible link label may use `session_url`, but the target must remain `launch_url`. Never generate, attach, or interpose a local/static HTML launcher or a second jump button.

The Hosted page must expose a **Copy confirmation JSON** action after every successful Stage 1 or Stage 2 capture. When automatic pull is unavailable or has not actually succeeded, ask the user to copy that JSON and paste it into chat. Materialize the pasted object unchanged and apply it with `hosted_confirm_bridge.py apply-return` for a direct session, or `hosted_confirm_handoff.py apply-response --stage stage1|stage2` for a browser-bootstrap session. The copy JSON is only a transport envelope; the pinned local official API core must still validate it and write the normal receipts.

Do not attempt to install Flask for Hosted Confirm. A missing Flask package is not a Hosted confirmation-surface failure and must not trigger ordinary-chat fallback; use the headless Cloudflare bridge or handoff above. Flask is required only when the official localhost Confirm UI server itself is explicitly requested.

The browser bootstrap erases its bearer fragment before entering `/s/<session>`, and confirmation leaves the visible URL short. Never claim that Cloudflare has fed a decision back to ChatGPT merely because the page says `captured-not-validated`; feedback is complete only after a successful pull/apply or after the copied JSON has passed local Harness validation. Do not ask the user to copy a token, long JSON URL, or confirmation JSON when automatic pull has actually succeeded; otherwise use the explicit **Copy confirmation JSON** fallback and never ask them to copy the bootstrap URL itself.

### Executor Live Preview — Cloudflare-hosted official SVG Editor

The official Harness still owns Executor Live Preview and its local `skills/ppt-master/scripts/svg_editor/server.py` behavior. When the execution Runtime actually has outbound HTTPS, `studio/host/cloudflare/hosted_editor_bridge.py` may mirror current `svg_output/`, `images/`, and `assets/` to the immutable commit-bound Worker so the user can operate the **official pinned SVG Editor frontend** remotely.

Remote edits and annotations are only `captured-not-applied`. Pull them back through the bridge and replay them through the pinned local official SVG Editor API; only the local official server may write authoritative `svg_output`. If the remote session is still open, resync the locally applied result so the same page refreshes from authority.

If Runtime outbound HTTPS is unavailable, do not claim that the Hosted SVG Editor is synchronized and do not expose a stale/test Hosted editor. Preserve the official local Live Preview behavior and continue under the official route's own failure/fallback semantics.

### Deck Review — framework-free actual-SVG handoff

For `Generate PPTX — ordinary Default`, after the current final SVG quality report passes and before Step 7 export, use the pinned Harness Deck Review stage. Run:

`python3 "${SKILL_DIR}/scripts/deck_review_handoff.py" build <project_path>`

This produces `<project_path>/live_preview/deck_review.html`, a self-contained review page that embeds sanitized copies of the actual final SVG files. It does **not** render screenshots and does not require Flask, localhost HTTP, Cloudflare, or Runtime outbound network. Present that HTML through the host's normal user-accessible file transport.

The user must explicitly review every slide as `通过` or `需要修改`. The page must remain open after completion and expose the final `ppt-master-static-deck-review-response/v1` JSON for copying. Materialize the copied JSON unchanged and apply it with:

`python3 "${SKILL_DIR}/scripts/deck_review_handoff.py" apply-response <project_path> --response-file <response.json>`

Only a successful pinned-Harness receipt with `result: approved` and `changes_count: 0` for the current `svg_roster_sha256` closes the Deck Review Gate. `changes-requested` returns to Executor; after supported changes are made, rerun final SVG quality, reconcile Speaker Notes if enabled, rebuild Deck Review, and wait for a new user response because the roster hash has changed. Never reuse an old review receipt after SVG mutation and never self-confirm this gate.

There is **no separate Studio Motion Review page**. Motion remains entirely under the official Harness and appears only when its official route requires it.

### Frozen legacy transports

Interactive Code Block mini-app and Studio static-UI implementations remain repository history/experimental fallback source, but v3.4.x does not load or ship them as the default ChatGPT Runtime interaction path. Do not prefer them over the Hosted official UI.

### Human-confirmation invariant

A confirmation-surface failure may change only the transport, never the owner of the decision. Unless the user explicitly delegated that confirmation, switching from Hosted page to ordinary chat is a blocking human gate: present the current official Gate's unresolved confirmation items, wait for an explicit user confirmation or revision, and only then persist/continue through the official Harness. A fallback notice, recommendation summary, silence, Cloudflare capture acknowledgment, or assistant-authored choice is not user confirmation. Preserve any already-persisted valid official receipt exactly as the official route requires.

If required bootstrap material cannot be resolved or materialized after the supported host paths are genuinely exhausted, fail closed. Never fall back to generic slide authoring.
