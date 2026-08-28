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

## Discover and detect host capabilities first
Read `studio/enforcement/PPT_MASTER_HOST_CAPABILITY_RULES.md` before any GitHub bootstrap.

On ChatGPT, absence from the immediately preloaded tool list is not enough to mark GitHub unavailable. When connector/plugin resource discovery is exposed, discover GitHub branch/read and artifact-download actions first, then invoke the discovered action. Only after discovery may an unexposed action be classified as unavailable.

At minimum distinguish:
- connected GitHub metadata access;
- ChatGPT-native public Web/API access;
- connector artifact download;
- explicit host-native URL/file download/materialization;
- local unpack/execution.

The execution container's own network stack is not a substitute for ChatGPT-native Web or connector access. A container DNS/network failure does not count as a public GitHub Web/API attempt.

## NEW project — host resolver
1. Perform a **fresh current-session read** of `studio-main` branch metadata and obtain its current full 40-character HEAD SHA. Never use a literal SHA from another chat, memory, Project Instructions, an older Release, or a prior project.
2. Discover and use the connected GitHub connector first when available. If connector access is genuinely unavailable after discovery or genuinely fails, use ChatGPT-native public GitHub Web/API when that capability is actually exposed.
3. Record the resolver path and SHA returned by that current bootstrap attempt. Fail Closed for SHA resolution only after all genuinely supported host resolution paths have been exhausted.
4. Pin that exact SHA for the project lifetime.
5. Materialize the exact pinned SHA through supported host file channels in this order:
   - already-local verified Runtime Bundle bound to the pinned SHA;
   - discover GitHub artifact actions, then download workflow artifact `ppt-master-studio-runtime` when available;
   - read permanent Release tag `studio-runtime-<SHA>` and use an explicit host-provided URL/file download primitive for `ppt-master-studio-runtime-<SHA>.zip` plus its `.sha256` when available;
   - another host-native exact-SHA repository archive/checkout path.
6. A host-provided URL-to-file tool counts as host-native materialization; shell `git`, `curl`, `wget`, Python HTTP libraries, Node fetch, or similar execution-container networking do not.
7. Do not say a Runtime Release/asset is missing unless metadata for the exact freshly resolved SHA has actually been read in the current attempt.
8. If SHA resolution succeeds but no supported materialization channel exists after connector discovery and genuine attempts, Fail Closed as `Harness materialization capability unavailable`; do not misreport it as SHA resolution failure and do not request a Recovery Bundle for a NEW project.
9. Read `studio/VERSION.json` at that exact SHA.
10. Read upstream `skills/ppt-master/SKILL.md` and run its attribution guard.
11. Read the Studio Authority, Workflow, Template Rules, Regression Policy, Host Capability Rules, plus Static UI/Recovery Rules on serverless hosts.
12. Run `python3 studio/scripts/enforced_bootstrap.py --repo-root <checkout> --running-commit <SHA>`.
13. Read upstream `skills/ppt-master/workflows/routing.md` and select exactly one route.
14. Create the initial checkpoint using `studio/scripts/enforced_checkpoint.py` with repository/ref/commit binding.

Missing authority, bootstrap failure, commit mismatch, or failure of all actually supported GitHub resolution/materialization paths is blocking.

## RESUME project / new chat
1. Read `project_state.json` first when present.
2. Use `harness.commit` from state as the required Harness commit; do not replace it with current `studio-main`.
3. Run the same connector discovery and host-capability detection before materializing the pinned Harness. Do not infer GitHub/Web availability from another chat.
4. Materialize that exact commit, bootstrap it, then run `enforced_preflight.py <project> --running-commit <pinned SHA>`.
5. If local state was lost, restore the latest verified `*.ppt-recovery.zip`; its manifest carries the pinned Harness binding.
6. A valid Recovery Bundle must contain `PPT_MASTER_RECOVERY_MANIFEST.json` with schema `ppt-master-portable-recovery/*`; ordinary source/handoff packages do not qualify.
7. Resume from the last completed gate, never from chat memory.

Only an explicit Harness migration may change an in-progress project pin.
