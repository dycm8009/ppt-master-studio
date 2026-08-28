# ChatGPT Host Capability Rules

Load this file only while resolving or materializing the PPT Master Studio Harness. It governs host access only; it does not define PPT workflow, design, UI, motion, recovery, or QA.

## Deterministic ChatGPT connector discovery

When GitHub is connected/in-scope but specific actions are not preloaded, use connector resource discovery before capability classification.

For a NEW project, complete these checks in this order:

1. Discover GitHub branch/read actions before resolving `studio-main`.
2. Resolve `dycm8009/ppt-master-studio` `studio-main` through current-session branch metadata. The SHA in that branch response is authoritative for the project pin.
3. Do not use code search, commit pages, release tags, cached Web/search results, chat history, memory, or a literal SHA as a substitute for current branch metadata. If connector branch metadata succeeds, it wins over a conflicting Web/search value.
4. After the SHA is pinned, discover GitHub workflow/artifact actions, including artifact listing and artifact download, before classifying artifact materialization as unavailable.
5. Locate a Studio Runtime Release workflow run whose `head_sha` exactly equals the pinned SHA, list its artifacts, and prefer the non-expired artifact named `ppt-master-studio-runtime`.
6. If that matching artifact exists and a download action was discovered, actually invoke the artifact download. Only an absent action after discovery, a missing/expired matching artifact, or an actual download failure may remove that path from consideration.

A message such as `artifact_download: not exposed` is not a valid failure reason unless resource discovery was attempted first and did not expose a usable action.

## NEW

1. In the current session, obtain the current 40-character `studio-main` SHA. Prefer the GitHub Connector after the discovery sequence above; native public Web/API is fallback only when connector branch metadata is genuinely unavailable or an actual connector call fails.
2. Never reuse a SHA from Project Instructions, chat history, memory, an older Runtime Release, a commit page, search result, or another project.
3. Pin the resolved SHA for the project lifetime.

## RESUME

Use the exact `harness.commit` from `project_state.json` or verified portable recovery evidence. Do not replace it with the current `studio-main` unless the user explicitly requests a Harness migration.

## Materialization

Use the first genuinely available path:

1. already-local verified Runtime bound to the pinned SHA;
2. after connector resource discovery, the `ppt-master-studio-runtime` workflow artifact for a Studio Runtime Release run whose `head_sha` exactly matches the pinned SHA;
3. exact-SHA Runtime Release asset plus checksum through an explicit host-native URL/file download capability;
4. another host-native exact-SHA archive/checkout capability.

Before declaring artifact download unavailable, discover GitHub artifact/download actions when discovery is exposed and actually call a discovered action when a matching non-expired artifact exists. Absence from the initially preloaded tool list is not proof of unavailability.

For the GitHub Actions artifact path, treat the downloaded artifact as an outer container ZIP: extract it, locate the exact `ppt-master-studio-runtime-{commit}.zip` and `.sha256`, verify the inner ZIP, extract it, then use that extracted directory as the Runtime root.

Before saying a Runtime Release or asset does not exist, read metadata for the exact pinned SHA.

## Network boundary

Host-native Connector, Web and file-download capabilities are distinct from the execution container. Shell `git`/`curl`/`wget`, Python HTTP libraries, Node fetch/http, or container DNS/network access must never be used as Connector/Web fallbacks. A container network failure proves only that the container cannot reach the network.

## Fail closed

- If no current-session stable SHA can be resolved after all host-supported resolution paths are genuinely exhausted: report SHA resolution failure.
- If a SHA is resolved but no supported file materialization path remains after connector discovery, required real download attempts, and the remaining host-native paths are genuinely exhausted: report `Harness materialization capability unavailable`.
- A NEW project never requires a project Recovery Bundle just to obtain the Harness.

After materialization, return to `studio/host/chatgpt/ENTRYPOINT.md` and enter the official `skills/ppt-master` load order.
