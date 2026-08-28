# ChatGPT Host Entry Point

Use this file only when a PPT/PPTX task enters PPT Master Studio. It adapts the ChatGPT host to the official PPT Master Harness; it does not redefine PPT authoring workflow.

## 1. Classify

- `RESUME` only when the user explicitly continues an existing Studio project or supplies `project_state.json` / a valid portable recovery bundle for continuation.
- Otherwise use `NEW`. Ordinary PPTX/PDF/DOCX/images/source ZIPs are inputs, not resume evidence.

## 2. Obtain the pinned Harness

For `NEW`, resolve the current `studio-main` 40-character SHA in this session, then pin it for the project. For `RESUME`, use the commit already recorded in project state/recovery; never silently upgrade it.

When GitHub actions are not preloaded, discover connector resources before declaring them unavailable. Use host-native connector/Web/file-download capabilities only; execution-container networking (`git`, `curl`, `wget`, Python/Node HTTP) is not a substitute.

Detailed host-only resolution/materialization rules are in `studio/enforcement/PPT_MASTER_HOST_CAPABILITY_RULES.md`. Load that file only while resolving or materializing the Harness.

## 3. Enter official PPT Master

After the exact Harness is local and verified:

1. Read `skills/ppt-master/SKILL.md`.
2. Run its `attribution_guard.py` exactly as required.
3. Read `skills/ppt-master/workflows/routing.md` and select exactly one top-level route.
4. Follow the selected official route. Load only that route and supporting documents it explicitly triggers.

Do not preload Studio workflow/template/UI/motion/QA policy because the official Harness owns those concerns.

## 4. Host-only adapters

Load Studio host adapters only when their condition occurs:

- checkpoint/preflight: project pin or resume verification;
- portable recovery: local project state was actually lost on a continuation run;
- Stage 1 mini app: when the active official route reaches the combined Stage-1 communication/template confirmation and this ChatGPT conversation exposes supported HTML/React Preview;
- generic Interactive Code Block mini app: only for another active official confirmation surface that has no dedicated host adapter;
- static UI adapter: only when the active official confirmation flow needs a host fallback that cannot use supported mini-app Preview or ordinary chat confirmation.

A host adapter may change transport or persistence, but must not invent a second PPT workflow, schema, design policy, motion policy, or QA authority.

**Stage-1 mini-app transport:** on ChatGPT, prefer `studio/scripts/stage1_mini_app.py` for the official combined Stage-1 confirmation when code-block Preview is available. The adapter reads the active `confirm_ui/recommendations.stage1.json`, `confirm_ui/template_options.json`, and official pinned Harness catalogs/indexes, then emits one self-contained fenced `html` code block. It is a rich **chat confirmation** surface, not the Flask/UI branch: it must not create or fabricate `result.json`, `template_selection.json`, `template_handoff.json`, options hashes, or any other official Confirm UI receipt. The user's returned `ppt-master-studio-stage1-mini-app-response/v1` payload must be validated against the current context with the same adapter before the official route continues. After validation, treat those values as the user's explicit Stage-1 chat decision and continue exactly under the official chat/delegated ordering, including official template-selection validation/application and later Stage 2. If the context changed, regenerate the mini app instead of accepting a stale payload.

**Generic mini-app transport:** when supported code-block Preview is available for another confirmation surface, `studio/scripts/mini_app_builder.py` may render the current official Gate data into one self-contained HTML code block. Surface that fenced `html` block directly in the assistant response so ChatGPT can offer Code/Preview. Do not serialize raw `app_block`/GenUI markers and do not attach the HTML as a substitute for the code block. A mini app may collect local UI state and emit a structured confirmation payload, but it must not assume an undocumented automatic callback from Preview to the assistant; until a host-native callback is actually available, the user returns the generated confirmation payload in chat.

**Human-confirmation invariant:** a confirmation-surface failure may change only the transport, never the owner of the decision. Unless the user has explicitly delegated that confirmation, switching from page/mini app to ordinary chat is a blocking human gate: present the current official Gate's unresolved confirmation items in chat, wait for an explicit user confirmation or revision, and only then continue. A fallback notice, recommendation summary, silence, or assistant-authored choice is not user confirmation. Preserve any already-persisted valid official receipt exactly as the official route requires.

If required bootstrap material cannot be resolved or materialized after the supported host paths are genuinely exhausted, fail closed. Never fall back to generic slide authoring.
