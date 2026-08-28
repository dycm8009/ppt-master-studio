# ChatGPT Inline Artifact Render Contract

This document defines how a `ppt-master-chat-inline-artifact-package/v1` is presented inside an ordinary ChatGPT conversation.

The package is produced by:

```bash
python -m studio.artifact_ui_poc.build_artifact <surface> <project>
```

The package is canonical for **presentation data only**. Gate acceptance remains owned by `studio/scripts/static_ui_adapter.py validate`.

## 1. Artifact-first behavior

For Stage 1, Stage 2, Deck Review, and conditional Motion Review, the ChatGPT host adapter must try the inline artifact path before constructing or presenting Static UI fallback HTML.

A new conversation does not need previous-turn proof that inline artifacts work. The first inline render attempt is the capability probe for that conversation.

Do not interpret these as reasons to skip the probe:
- no previous artifact exists in this chat;
- this is a newly opened chat;
- the assistant cannot read artifact-local state back automatically;
- the user is on a different conversation than the one used for host acceptance testing.

The missing artifact → assistant callback affects handoff only; it does not disable inline rendering.

## 2. Host render mapping

Take the package's `render` object:

```json
{
  "language": "html",
  "variant": "inline",
  "icon": "app",
  "title": "PPT Master · Stage 1",
  "content": "<self-contained HTML fragment>"
}
```

Map it to one host-native inline app/artifact block with these values:

```text
app_block.language      = render.language
app_block.entrypoint    = "index.html"
app_block.bundle_version = 1
app_block.title         = render.title
app_block.variant       = render.variant
app_block.icon          = render.icon
app_block.content       = render.content
```

In ChatGPT hosts whose response renderer supports direct inline app content references, emit exactly one inline `app_block` for the Gate surface. Do not return the package JSON, an HTML attachment, a code block, or a browser URL as a substitute for the inline attempt.

The host serialization syntax is transport-level and may evolve; the semantic input is always the mapping above. If the host exposes an explicit inline-artifact tool/action, use it. If the host accepts inline app content references directly in assistant output, use that supported response mechanism.

## 3. Success and fallback

Inline render success means the user sees the interactive Gate surface embedded in the conversation and can edit controls locally.

Fallback to Studio Static UI is allowed only if:
- `build_artifact` fails closed;
- the current host explicitly provides no inline app/artifact render mechanism;
- the host rejects the render attempt;
- the package violates self-containment or parity requirements.

Do not choose Static UI merely because the current chat has no previous artifact-host verification.

## 4. Handoff and authority

Current ChatGPT inline artifacts support local interaction and canonical capture but have no supported automatic callback to the assistant.

The user-visible action is therefore:

```text
Confirm
  ↓
Captured · not validated
  ↓
复制并继续
  ↓
paste/send canonical JSON
  ↓
static_ui_adapter.py validate
  ↓
accepted receipt
```

`captured != delivered != accepted` remains mandatory.

## 5. Parity

The inline artifact must not maintain its own product semantics. It must consume the same canonical inputs as the Static UI / validator path, including:
- canonical IDs and enums;
- recommendation/options hashes;
- template candidates;
- Stage 2 catalogs and preview semantics;
- Deck Review `changes[]` and validator-compatible `svg_roster_sha256`;
- Motion Review official animation registries and plan hash.

See `PARITY_CONTRACT.md` for the complete parity boundary.