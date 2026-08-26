# PPT Master Studio v3.2.0 — Workflow Contract

## Startup
1. Resolve Harness commit: new project = current `studio-main` HEAD; continuation = exact commit pinned in state/recovery manifest.
2. Materialize that exact commit.
3. Read upstream `skills/ppt-master/SKILL.md` and run its attribution guard.
4. Read Studio Authority and run `studio/scripts/enforced_bootstrap.py --repo-root <checkout> --running-commit <SHA>`.
5. Read upstream routing and select exactly one route/profile.
6. On serverless hosts read Static UI and Recovery Rules.
7. Create/load checkpoint with repository/ref/commit binding.

Any missing authority, bootstrap failure, or pin mismatch is blocking.

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

## Resume
Read state first. If missing, restore the latest valid recovery bundle. Materialize `harness.commit`, bootstrap that exact SHA, run `studio/scripts/enforced_preflight.py <project> --running-commit <SHA>`, and resume from the last completed gate. Never infer missing state from chat.
