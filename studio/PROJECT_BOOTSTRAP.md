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

## Detect host capabilities first
Read `studio/enforcement/PPT_MASTER_HOST_CAPABILITY_RULES.md` before any GitHub bootstrap. Choose paths only from capabilities actually exposed in the current conversation/runtime.

At minimum distinguish:
- connected GitHub metadata access;
- ChatGPT-native public Web/API access;
- connector artifact download;
- host-native file download/materialization;
- local unpack/execution.

The execution container's own network stack is not a substitute for ChatGPT-native Web or connector access. A container DNS/network failure does not count as a public GitHub Web/API attempt.

## NEW project — host resolver
1. Resolve the current full 40-character HEAD SHA of `studio-main`.
2. Use the connected GitHub connector first when it is actually exposed. If connector access is absent or genuinely fails, use ChatGPT-native public GitHub Web/API when that capability is actually exposed.
3. Fail Closed for SHA resolution only after all genuinely supported host resolution paths have been exhausted. Report actual detected capabilities and actual attempts.
4. Pin that exact SHA for the project lifetime.
5. Materialize the exact pinned SHA through supported host file channels in this order:
   - already-local verified Runtime Bundle bound to the pinned SHA;
   - GitHub Connector workflow artifact `ppt-master-studio-runtime`;
   - host-native download of permanent Release tag `studio-runtime-<SHA>`, asset `ppt-master-studio-runtime-<SHA>.zip`;
   - another host-native exact-SHA repository archive/checkout path.
6. Do not use direct execution-container networking as a GitHub fallback or materialization channel.
7. If SHA resolution succeeds but no supported materialization channel exists, Fail Closed as `Harness materialization capability unavailable`; do not misreport it as SHA resolution failure and do not request a Recovery Bundle for a NEW project.
8. Read `studio/VERSION.json` at that exact SHA.
9. Read upstream `skills/ppt-master/SKILL.md` and run its attribution guard.
10. Read the Studio Authority, Workflow, Template Rules, Regression Policy, Host Capability Rules, plus Static UI/Recovery Rules on serverless hosts.
11. Run `python3 studio/scripts/enforced_bootstrap.py --repo-root <checkout> --running-commit <SHA>`.
12. Read upstream `skills/ppt-master/workflows/routing.md` and select exactly one route.
13. Create the initial checkpoint using `studio/scripts/enforced_checkpoint.py` with repository/ref/commit binding.

Missing authority, bootstrap failure, commit mismatch, or failure of all actually supported GitHub resolution/materialization paths is blocking.

## RESUME project / new chat
1. Read `project_state.json` first when present.
2. Use `harness.commit` from state as the required Harness commit; do not replace it with current `studio-main`.
3. Run the same host-capability detection before materializing the pinned Harness. Do not infer GitHub/Web availability from another chat.
4. Materialize that exact commit, bootstrap it, then run `enforced_preflight.py <project> --running-commit <pinned SHA>`.
5. If local state was lost, restore the latest verified `*.ppt-recovery.zip`; its manifest carries the pinned Harness binding.
6. A valid Recovery Bundle must contain `PPT_MASTER_RECOVERY_MANIFEST.json` with schema `ppt-master-portable-recovery/*`; ordinary source/handoff packages do not qualify.
7. Resume from the last completed gate, never from chat memory.

Only an explicit Harness migration may change an in-progress project pin.
