# ChatGPT Project Router Migration

## Goal

Reduce fresh-chat routing ambiguity by making ChatGPT Project Instructions a small, stable router instead of a second copy of the Studio operating manual.

## What moves out of Project Instructions

Do not keep duplicated machine authority in persistent Project Sources when GitHub `dycm8009/ppt-master-studio` is already the source of truth:

- copied Authority / Workflow / Template / Regression files;
- old runtime or enforced Harness ZIPs;
- v2/v3 add-on ZIPs;
- detailed host capability, artifact transport, image, motion and QA rules.

Those rules live in the pinned Studio commit and are loaded after routing/bootstrap.

A human-facing README or setup guide may remain, but it must not become a second execution authority.

## Project Instructions responsibility

The persistent Project prompt now owns only:

1. identify every PPT/PPTX/slide-deck/presentation task as `PPT_MASTER_TASK`;
2. classify NEW vs RESUME before bootstrap;
3. allow host-mandated slide/artifact handoff but force PPT Master bootstrap before generic authoring;
4. resolve/materialize/pin the Studio Harness according to Host Capability Rules;
5. enter the pinned repo's chat-inline artifact UI path at Gate surfaces;
6. fail closed instead of silently falling back to generic slides.

Everything else is repository authority.

## NEW / RESUME

`RESUME` is only valid when the user explicitly requests continuation or supplies valid project-state/recovery evidence for continuation.

Ordinary PPTX, PDF, document, image, source ZIP, handoff ZIP or material package is still a `NEW` input.

Users do not need to say `初始化环境`.

## Chat-inline artifact UI

The Project prompt names only the artifact entry point:

```text
python -m studio.artifact_ui_poc.build_artifact <surface> <project>
```

The active probe, direct GenUI response serialization, Parity rules and Static UI fallback conditions are defined by the pinned repository contracts:

- `studio/enforcement/PPT_MASTER_HOST_CAPABILITY_RULES.md`
- `studio/artifact_ui_poc/CHATGPT_RENDER_CONTRACT.md`
- `studio/artifact_ui_poc/CHATGPT_DIRECT_CONTENT_REFERENCE.md`
- `studio/artifact_ui_poc/PARITY_CONTRACT.md`

The Project prompt must not duplicate those volatile transport details.

Current verified behavior still has no supported artifact → assistant callback. Local Confirm means `captured`; accepted Gate evidence is produced only by `static_ui_adapter.py validate` after the canonical JSON is delivered back to the assistant.

## Expected result

A fresh chat should treat a normal request such as:

> 使用 PPT Master Studio 帮我生成这个 PPT

as a PPT Master task immediately, classify it as NEW unless continuation evidence exists, and bootstrap the pinned Studio runtime without requiring a separate `初始化环境` prompt.
