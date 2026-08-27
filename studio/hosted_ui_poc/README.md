# Hosted Confirm UI POC (方案 B)

这是隔离验证目录，不改变当前 `static-html` 生产路径。

目标：验证 Cloudflare Worker + Static Assets + KV 是否能替代本地单文件 HTML，提供稳定 URL、临时会话和更好的浏览器交互，同时保持 Harness validator 为最终 authority。

## POC contract

- `POST /api/sessions`：创建 24h session。输入 `{surface,payload}`。
- `GET /api/sessions/<token>`：读取 session。
- `POST /api/sessions/<token>/response`：捕获用户确认 JSON；返回 `captured-not-validated`，绝不生成 accepted receipt。
- `GET /api/sessions/<token>/response`：由 Harness/host 取回用户回传，再调用现有 `static_ui_adapter.py validate`。
- `/s/<token>`：浏览器交互页。
- session token 为随机 192-bit bearer token；KV key 不可枚举；响应使用 `Cache-Control: no-store`；TTL 默认 86400 秒。
- PPT 内容和 session 数据只进入临时 KV，不进入 GitHub。

## 当前范围

POC 前端只实现 Stage 1 的主要沟通字段，用来验证 Hosted transport + UX。Stage 2 / Deck Review / Motion Review 暂时只验证 session 传输层；在 POC 通过后再迁移现有 Static UI 组件。

## Deploy

1. 在 Cloudflare 创建 KV namespace。
2. 把 `wrangler.jsonc` 中 `REPLACE_WITH_KV_NAMESPACE_ID` 替换为 namespace id。
3. 在此目录运行 `npx wrangler deploy`。

Cloudflare 当前推荐新项目使用 Workers Static Assets 和 `wrangler.jsonc`。生产化时建议用独立域名，并增加 origin/auth、session payload size limit、R2 大对象拆分以及清理/审计策略。
