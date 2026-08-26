# PPT Master Studio — ChatGPT Project Bootstrap

This repository is the single Harness source authority for PPT Master Studio. Do not treat uploaded Harness ZIPs or copied Authority/Workflow files as current once this bootstrap is active.

## Repository authority
- Repository: `dycm8009/ppt-master-studio`
- Stable branch: `studio-main`
- Development branch: `studio-dev`
- Upstream mirror: `main`

## New PPT project
1. Resolve the current HEAD SHA of `studio-main`.
2. Read `studio/VERSION.json` at that exact SHA.
3. Materialize/download that exact commit into the runtime; never keep following the moving branch after project start.
4. Read upstream `skills/ppt-master/SKILL.md` and run its attribution guard.
5. Read the Studio Authority, Workflow, Template Rules, Regression Policy, plus Static UI/Recovery Rules on serverless hosts.
6. Run `python3 studio/scripts/enforced_bootstrap.py --repo-root <checkout> --running-commit <SHA>`.
7. Read upstream `skills/ppt-master/workflows/routing.md` and select exactly one route.
8. Create the initial checkpoint using `studio/scripts/enforced_checkpoint.py` with repository/ref/commit binding.

Missing authority, bootstrap failure, or commit mismatch is blocking.

## Existing project / new chat
1. Read `project_state.json` first when present.
2. Use `harness.commit` from state as the required Harness commit; do not replace it with current `studio-main`.
3. Materialize that exact commit, bootstrap it, then run `enforced_preflight.py <project> --running-commit <pinned SHA>`.
4. If local state was lost, restore the latest verified `*.ppt-recovery.zip`; its manifest carries the pinned Harness binding.
5. Resume from the last completed gate, never from chat memory.

Only an explicit Harness migration may change an in-progress project pin.
