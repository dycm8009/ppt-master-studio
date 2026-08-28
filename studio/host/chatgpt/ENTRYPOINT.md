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
- static UI adapter: only when the active official confirmation flow needs a host fallback that cannot use its normal page/chat channel.

A host adapter may change transport or persistence, but must not invent a second PPT workflow, schema, design policy, motion policy, or QA authority.

If required bootstrap material cannot be resolved or materialized after the supported host paths are genuinely exhausted, fail closed. Never fall back to generic slide authoring.
