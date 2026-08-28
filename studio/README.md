# PPT Master Studio

PPT Master Studio is a thin ChatGPT host adapter around the official PPT Master skill. It does not maintain a second PPT workflow.

## Branches

- `main` — upstream mirror
- `studio-main` — stable ChatGPT host adapter
- `studio-dev` — development

A NEW project resolves and pins the current `studio-main` commit once. A RESUME project uses its existing pinned commit unless the user explicitly requests migration.

## Runtime authority

PPT authoring authority remains under `skills/ppt-master/`:

- `SKILL.md` owns the official load order;
- `workflows/routing.md` selects exactly one route;
- the selected route owns its gates, templates, images, motion, recovery semantics and QA;
- supporting documents are loaded only when the selected route explicitly triggers them.

Studio adds only host-specific capabilities the official skill cannot provide itself: ChatGPT/GitHub materialization and commit pinning, serverless persistence helpers, portable recovery for real filesystem loss, and an optional static confirmation transport fallback.

## ChatGPT entry

Persistent Project Instructions should stay minimal and point PPT tasks to:

`studio/host/chatgpt/ENTRYPOINT.md`

That entry point loads host materialization rules only while bootstrapping, then hands execution to the official PPT Master load order. Do not preload duplicate Studio workflow or design-policy documents.

## Runtime release

Every stable `studio-main` commit publishes a commit-bound Runtime Release using tag `studio-runtime-<SHA>` and asset `ppt-master-studio-runtime-<SHA>.zip`.

The Runtime is built from a whitelist: the official `skills/ppt-master` package plus minimal ChatGPT host adapters. Repository documentation, tests, regression policy and experiments are intentionally excluded. A Runtime ZIP is not a project Recovery Bundle.
