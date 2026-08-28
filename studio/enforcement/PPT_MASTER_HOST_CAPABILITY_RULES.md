# ChatGPT Host Capability Rules

Load this file only while resolving or materializing the PPT Master Studio Harness. It governs host access only; it does not define PPT workflow, design, UI, motion, recovery, or QA.

## NEW

1. In the current session, obtain the current 40-character `studio-main` SHA. Prefer the GitHub Connector; if connector functions are not preloaded and resource discovery exists, discover branch/read actions first. Native public Web/API is the fallback only when it is actually available.
2. Never reuse a SHA from Project Instructions, chat history, memory, an older Runtime Release, or another project.
3. Pin the resolved SHA for the project lifetime.

## RESUME

Use the exact `harness.commit` from `project_state.json` or verified portable recovery evidence. Do not replace it with the current `studio-main` unless the user explicitly requests a Harness migration.

## Materialization

Use the first genuinely available path:

1. already-local verified Runtime bound to the pinned SHA;
2. after connector resource discovery, the `ppt-master-studio-runtime` workflow artifact for that SHA;
3. exact-SHA Runtime Release asset plus checksum through an explicit host-native URL/file download capability;
4. another host-native exact-SHA archive/checkout capability.

Before declaring artifact download unavailable, discover GitHub artifact/download actions when discovery is exposed and actually call a discovered action. Absence from the initially preloaded tool list is not proof of unavailability.

Before saying a Runtime Release or asset does not exist, read metadata for the exact pinned SHA.

## Network boundary

Host-native Connector, Web and file-download capabilities are distinct from the execution container. Shell `git`/`curl`/`wget`, Python HTTP libraries, Node fetch/http, or container DNS/network access must never be used as Connector/Web fallbacks. A container network failure proves only that the container cannot reach the network.

## Fail closed

- If no current-session stable SHA can be resolved after all host-supported resolution paths are genuinely exhausted: report SHA resolution failure.
- If a SHA is resolved but no supported file materialization path remains after discovery and genuine attempts: report `Harness materialization capability unavailable`.
- A NEW project never requires a project Recovery Bundle just to obtain the Harness.

After materialization, return to `studio/host/chatgpt/ENTRYPOINT.md` and enter the official `skills/ppt-master` load order.
