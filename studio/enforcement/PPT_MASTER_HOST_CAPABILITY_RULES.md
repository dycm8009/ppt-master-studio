# PPT Master Studio — Host Capability Rules

These rules govern how a ChatGPT/serverless host resolves and materializes the pinned GitHub Harness.

## 1. Discover before declaring unavailable
On ChatGPT, a connector function not appearing in the immediately preloaded tool list does **not** prove the connector or action is unavailable.

Before marking GitHub metadata or artifact download unavailable, use the host's connector/plugin resource-discovery mechanism when one is exposed. In the current ChatGPT host this means discovering GitHub resources/actions first (for example branch/read functions and artifact-download functions) and then invoking the discovered action. Do not stop at discovery; perform the actual read/download call.

Only after discovery has been attempted, or when the host truly exposes no discovery mechanism, may an unexposed connector capability be classified as unavailable.

## 2. Detect actual current-session capabilities
After discovery, classify only capabilities actually usable in the current conversation/runtime:
- `github_connector_read`: branch/workflow/release metadata through the connected GitHub app.
- `native_web_read`: ChatGPT-native web/browser access to public GitHub pages or REST API.
- `connector_artifact_download`: GitHub workflow-artifact download into a real runtime file.
- `native_host_file_download`: any explicit host-provided URL/file materialization primitive outside the execution container's own network stack.
- `local_execution`: ability to unpack and run the Harness locally.

A host-provided download tool that writes a URL result to a runtime file counts as `native_host_file_download` even if the file ultimately lands in the execution environment, provided the network transfer is performed by the host tool rather than by shell/Python/Node networking inside the container.

Never infer a capability from an earlier chat, from the fact that an app was installed, or from user memory.

## 3. Container networking is not a Web fallback
The execution container's own network stack is not equivalent to ChatGPT-native Web access. Commands or libraries that try to reach GitHub directly from the container must not be used to satisfy the public-Web fallback contract.

Examples that do **not** count as `native_web_read` or supported Harness materialization include shell Git network operations, command-line HTTP clients, Python HTTP libraries, Node HTTP/fetch calls, or equivalent direct requests from the execution container.

A DNS/network error from the container only proves that container networking is unavailable. It must never be reported as “public GitHub Web/API was attempted and failed.”

## 4. Fresh SHA resolution
For every NEW project, the pinned SHA must come from a live branch-metadata read performed in the current bootstrap attempt.

1. Discover and use `github_connector_read` when available, and read current `studio-main` branch metadata.
2. Otherwise, if `native_web_read` is available, read the public GitHub branch/API metadata for `studio-main` in the current attempt.
3. Do not reuse a literal SHA from Project Instructions, an earlier chat, memory, a previous Runtime Release, or a cached project artifact.
4. Record the resolver path and exact 40-hex SHA returned by that current-session branch read.
5. Fail Closed for SHA resolution only after all genuinely supported host resolution paths have been exhausted.

For RESUME, use the pinned commit from `project_state.json` or the verified Recovery manifest; do not replace it with current `studio-main`.

## 5. Harness materialization order
After an exact 40-hex SHA is known:
1. Reuse an already-local Runtime Bundle only if it is explicitly bound to that SHA and its SHA-256 verifies.
2. Before declaring artifact download unavailable, discover GitHub artifact-related actions. If a workflow-artifact download action is available, invoke it for artifact `ppt-master-studio-runtime` associated with the pinned SHA.
3. Otherwise read the permanent Release metadata for tag `studio-runtime-<SHA>` and asset `ppt-master-studio-runtime-<SHA>.zip`.
4. If `native_host_file_download` exists, use that host-provided download primitive for the exact Release asset and its `.sha256` sidecar, then verify SHA-256 locally.
5. Only then use another host-native exact-SHA archive/checkout path.
6. Direct execution-container networking is never a fallback materialization channel.

The absence of a preloaded artifact-download function is not sufficient evidence for step 2 failure. Discovery must happen first.

If the SHA is known but no supported materialization channel exists after discovery and genuine attempts, Fail Closed with the reason `Harness materialization capability unavailable`; do not misreport this as SHA resolution failure and do not request a Recovery Bundle for a NEW project.

## 6. Release existence checks
Do not state that a Runtime Release or asset does not exist unless release metadata for the **exact freshly resolved SHA** has actually been read in the current attempt. A missing download primitive and a missing Release are different failure classes.

## 7. Failure reporting
A blocking message must distinguish:
- connector/resource discovery failure;
- SHA resolution failure;
- Runtime artifact/release materialization failure;
- local execution/bootstrap failure;
- RESUME evidence/recovery failure.

It must list the actual host capabilities detected, discovery performed, the current-session SHA resolver source, and only the paths genuinely attempted.
