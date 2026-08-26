# PPT Master Studio v3.2.1 — Workflow Contract

## Startup mode classification
- **NEW**: create/rebuild a deck without an explicit continuation request and without a prior project state/recovery authority.
- **RESUME**: continue an existing project from `project_state.json` or a valid Recovery Bundle.
- Source/handoff ZIPs are inputs, not recovery evidence unless they contain a valid `PPT_MASTER_RECOVERY_MANIFEST.json` using a supported `ppt-master-portable-recovery/*` schema.

## NEW startup
1. Resolve Harness commit = current `studio-main` HEAD.
2. On ChatGPT, attempt the connected GitHub connector first; if it fails/is unavailable, attempt public GitHub Web/API. Only failure of both resolution paths is blocking.
3. Pin that exact SHA for the new project.
4. Materialize the exact SHA, preferring GitHub Runtime Release tag `studio-runtime-<SHA>` / asset `ppt-master-studio-runtime-<SHA>.zip`; fall back to exact-SHA repository archive/checkout if needed.
5. A NEW project never requires `*.ppt-recovery.zip` merely to obtain the Harness.
6. Read upstream `skills/ppt-master/SKILL.md` and run its attribution guard.
7. Read Studio Authority and run `studio/scripts/enforced_bootstrap.py --repo-root <checkout> --running-commit <SHA>`.
8. Read upstream routing and select exactly one route/profile.
9. On serverless hosts read Static UI and Recovery Rules.
10. Create checkpoint with repository/ref/commit binding.

## RESUME startup
1. Read state first. If `project_state.json` exists, use its exact `harness.commit`.
2. If state/project files were lost, restore the latest verified Recovery Bundle; do not substitute a source/handoff package.
3. Materialize the pinned Harness commit, bootstrap that exact SHA, run `studio/scripts/enforced_preflight.py <project> --running-commit <SHA>`, and resume from the last completed gate.
4. If no valid recovery evidence exists and required project artifacts are truly lost, Fail Closed. Never infer missing state from chat.

Any missing authority, bootstrap failure, pin mismatch, or exhaustion of supported GitHub resolution/materialization paths is blocking.

## Enforced pipeline
A. Source Intake — preserve facts/order in Beautify/Convert by default.
B. Strategist — preserve upstream two-stage human confirmation. Static Stage 1 covers communication + template choice; Stage 2 covers final deck solution + production controls. Freeze `design_spec.md`/`spec_lock.md` only after final Stage 2 confirmation.
C. Deck Art Direction — mandatory for 18+ slides; create `deck_plan.json` with composition family, primary visual carrier, rhythm, and section personality. Same family max 2 consecutive by default; no universal card fallback.
D. Visual Carrier — image pipeline is Opportunity → Necessity → Compatibility → Role Fitness → Treatment/Placement. General + Dark Tech prefers SVG/typography/icons/native chart/table before raster imagery.
E. Planning Recovery — on serverless hosts surface a verified planning-ready recovery ZIP before authoring.
F. Page Authoring — exact roster from frozen spec/plan; choose diagrams/process/comparison/table/timeline/network/editorial/typography according to communication job.
G. Motion — default transition none; long-deck deck-wide object auto-animation forbidden; recommended max 35% animated slides, 3 object rows/slide, 24 rows across 30–40 slides.
H. Render + QA — SVG quality, static/runtime visual review, diversity/similarity, image audit if needed, motion audit if needed. After accepted Deck Review changes surface authoring-reviewed recovery snapshot.
I. Export — surface final QA/motion recovery snapshot, export only from canonical source, then PPTX postflight.

Only an explicit Harness migration may change an in-progress project pin.
