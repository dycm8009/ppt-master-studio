# ChatGPT Direct Content Reference Transport

This file records the currently verified ChatGPT response serialization used for the PPT Master chat-inline Artifact probe.

This is a **transport adapter**, not a new product schema. Canonical Gate data still comes from `ppt-master-chat-inline-artifact-package/v1` and acceptance remains owned by `studio/scripts/static_ui_adapter.py validate`.

## Verified response form

For the current ChatGPT host, an inline artifact may be emitted directly in the assistant response as a GenUI content reference:

```text
genui{"app_block":{"language":"<render.language>","entrypoint":"index.html","bundle_version":1,"title":"<render.title>","variant":"<render.variant>","icon":"<render.icon>","content":"<render.content>"}}
```

The actual values MUST come from the package `render` object. The assistant must not hand-author a second copy of the Stage schema or UI semantics.

## Probe rule

The direct content reference above is itself the first host render probe in a fresh ChatGPT conversation.

Do not require any of the following before emitting it:

- a preloaded `app_block` tool;
- a discoverable `app_block` action;
- `genui_search` returning an `app_block` widget;
- an artifact tool name appearing in the current tool list;
- successful inline rendering in an earlier conversation.

Absence from the tool/action list is **not** evidence that direct response content references are unavailable. This transport is serialized in the assistant response rather than invoked as a normal tool call.

## Fallback evidence

Static UI fallback is allowed after direct-reference probing only when there is concrete current-turn evidence that the response transport cannot render the content reference, or when artifact construction/self-containment fails closed.

Do not claim `current host has no inline app_block interface` solely because no `app_block` tool/action is exposed.

## Authority

Direct content-reference rendering changes presentation only:

```text
Confirm -> captured -> 复制并继续 -> paste/send canonical JSON -> static_ui_adapter.py validate -> accepted
```

`captured != delivered != accepted` remains mandatory.
