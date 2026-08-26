# PPT Master Studio — ChatGPT Project Bootstrap

This repository is the single Harness source authority for PPT Master Studio. Do not treat uploaded Harness ZIPs or copied Authority/Workflow files as current once this bootstrap is active.

## Repository authority
- Repository: `dycm8009/ppt-master-studio`
- Stable branch: `studio-main`
- Development branch: `studio-dev`
- Upstream mirror: `main`

## Classify before bootstrapping
- **NEW**: create/rebuild a deck without an explicit request to resume a prior project state.
- **RESUME**: continue an existing deck/project from `project_state.json` or a valid `*.ppt-recovery.zip`.
- A normal source/handoff ZIP is not a Recovery Bundle just because it is a ZIP.
- A brand-new project does **not** require a Recovery Bundle.

## NEW project — host resolver
1. Resolve the current full 40-character HEAD SHA of `studio-main`.
2. On ChatGPT, use the connected GitHub connector first. If connector access fails or is not exposed, use the public GitHub branch/API as fallback. Do not Fail Closed until both resolution paths have been attempted.
3. Pin that exact SHA for the project lifetime.
4. Prefer the commit-bound GitHub Runtime Release:
   - tag: `studio-runtime-<SHA>`
   - asset: `ppt-master-studio-runtime-<SHA>.zip`
5. If the Runtime Release is temporarily unavailable, materialize the exact SHA using repository archive/checkout. Never substitute a different commit and never ask for a Recovery Bundle merely to bootstrap a NEW project.
6. Read `studio/VERSION.json` at that exact SHA.
7. Read upstream `skills/ppt-master/SKILL.md` and run its attribution guard.
8. Read the Studio Authority, Workflow, Template Rules, Regression Policy, plus Static UI/Recovery Rules on serverless hosts.
9. Run `python3 studio/scripts/enforced_bootstrap.py --repo-root <checkout> --running-commit <SHA>`.
10. Read upstream `skills/ppt-master/workflows/routing.md` and select exactly one route.
11. Create the initial checkpoint using `studio/scripts/enforced_checkpoint.py` with repository/ref/commit binding.

Missing authority, bootstrap failure, commit mismatch, or failure of all supported GitHub resolution/materialization paths is blocking.

## RESUME project / new chat
1. Read `project_state.json` first when present.
2. Use `harness.commit` from state as the required Harness commit; do not replace it with current `studio-main`.
3. Materialize that exact commit, bootstrap it, then run `enforced_preflight.py <project> --running-commit <pinned SHA>`.
4. If local state was lost, restore the latest verified `*.ppt-recovery.zip`; its manifest carries the pinned Harness binding.
5. A valid Recovery Bundle must contain `PPT_MASTER_RECOVERY_MANIFEST.json` with schema `ppt-master-portable-recovery/*`; ordinary source/handoff packages do not qualify.
6. Resume from the last completed gate, never from chat memory.

Only an explicit Harness migration may change an in-progress project pin.
