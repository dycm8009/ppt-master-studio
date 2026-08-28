# PPT Master Studio — Host Capability Rules

These rules govern how a ChatGPT/serverless host resolves and materializes the pinned GitHub Harness.

## 1. Detect actual host capabilities first
Before GitHub bootstrap, classify only capabilities actually exposed in the current conversation/runtime:
- `github_connector_read`: branch/workflow/release metadata through the connected GitHub app.
- `native_web_read`: ChatGPT-native web/browser access to public GitHub pages or REST API.
- `connector_artifact_download`: GitHub workflow-artifact download into a real runtime file.
- `native_host_file_download`: any host-supported file download/materialization path outside the execution container's own network stack.
- `local_execution`: ability to unpack and run the Harness locally.

Never infer a capability from an earlier chat, from the fact that an app was installed, or from user memory.

## 2. Container networking is not a Web fallback
The execution container's network stack is not equivalent to ChatGPT-native Web access. Commands or libraries that try to reach GitHub directly from the container must not be used to satisfy the public-Web fallback contract.

Examples that do **not** count as `native_web_read` or supported Harness materialization include shell Git network operations, command-line HTTP clients, Python HTTP libraries, Node HTTP/fetch calls, or equivalent direct requests from the execution container.

A DNS/network error from the container only proves that container networking is unavailable. It must never be reported as “public GitHub Web/API was attempted and failed.”

## 3. SHA resolution order
For a NEW project:
1. Use `github_connector_read` when available.
2. Otherwise, use `native_web_read` against public GitHub branch/API metadata.
3. Fail Closed for SHA resolution only after both actually supported host paths are unavailable or have genuinely failed.

For RESUME, use the pinned commit from `project_state.json` or the verified Recovery manifest; do not replace it with current `studio-main`.

## 4. Harness materialization order
After an exact 40-hex SHA is known:
1. Reuse an already-local Runtime Bundle only if it is explicitly bound to that SHA and its SHA-256 verifies.
2. Prefer GitHub Connector workflow-artifact download when supported.
3. Otherwise use a host-native file-download path for the permanent `studio-runtime-<SHA>` Release asset when supported.
4. Only then use another host-native exact-SHA archive/checkout path.
5. Direct container networking is never a fallback materialization channel.

If the SHA is known but no supported materialization channel exists, Fail Closed with the reason `Harness materialization capability unavailable`; do not misreport this as SHA resolution failure and do not request a Recovery Bundle for a NEW project.

## 5. Failure reporting
A blocking message must distinguish:
- SHA resolution failure;
- Runtime artifact/release materialization failure;
- local execution/bootstrap failure;
- RESUME evidence/recovery failure.

It must list the actual host capabilities detected and only the paths genuinely attempted.
