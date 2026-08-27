# Hosted Confirm UI POC (方案 B2)

这是隔离验证目录，不改变当前 `static-html` 生产路径。

目标：验证 Cloudflare Worker + Static Assets + per-session Durable Object 是否能替代本地单文件 HTML，提供稳定 URL、强一致临时会话和更好的浏览器交互，同时保持 Harness validator 为最终 authority。

## 为什么从 KV 改为 Durable Object

Hosted confirmation 是典型的即时 read-after-write 流程：Host 创建 session 后浏览器应立即读取，用户提交后 Host 也应立即取回 response。KV 的跨 location eventual consistency 不适合这个交互闭环；B2 使用 `SESSIONS.getByName(token)` 将每个随机 token 路由到独立 Durable Object，并在对象的 strongly-consistent storage 内保存该 session。

## POC contract

- `POST /api/sessions`：创建 24h session。输入 `{surface,payload}`。
- `GET /api/sessions/<token>`：读取 session。
- `POST /api/sessions/<token>/response`：捕获一次用户确认 JSON；返回 `captured-not-validated`，绝不生成 accepted receipt。重复 capture 返回 409，避免覆盖已确认响应。
- `GET /api/sessions/<token>/response`：由 Harness/host 取回用户回传，再调用现有 `static_ui_adapter.py validate`。
- `/s/<token>`：浏览器交互页。
- session token 为随机 192-bit bearer token；token 作为 Durable Object name，不存在可枚举的 session index；HTTP 响应使用 `Cache-Control: no-store`。
- 每个 session 设置 24h Durable Object alarm；过期读取也会立即清空 storage，因此 alarm 延迟不会延长有效期。
- PPT 内容和 session 数据只进入临时 Durable Object storage，不进入 GitHub。

## 当前范围

POC 前端只实现 Stage 1 的主要沟通字段，用来验证 Hosted transport + UX。为确保回传一定满足当前 Harness validator，本阶段固定 `template_selection.mode=free_design` 且 `selection_keys=[]`，暂不暴露模板选择 UI。Stage 2 / Deck Review / Motion Review 暂时只验证 session 传输层；在 POC 通过后再迁移现有 Static UI 组件和 Stage 1 candidate schema。

## Deploy

1. 确认 Wrangler v4 可用并已登录 Cloudflare：`npx wrangler --version`、`npx wrangler whoami`。
2. 在本目录运行 `npx wrangler check`。
3. 运行 `npx wrangler deploy`。首次部署会按 `wrangler.jsonc` 的 `v1` migration 创建 SQLite-backed `HostedSession` Durable Object class，不需要预建 KV namespace。
4. 用真实 Stage 1 payload 做完整 Gate：创建 session → 浏览器打开 `/s/<token>` → capture → Host GET response → `static_ui_adapter.py validate` → 检查 `accepted.stage1.json`。

## 仍需在真实 Cloudflare 部署验证

- workers.dev / 自定义域名 URL 可达。
- 创建后的 session 立即可读，capture 后 response 立即可读。
- 24h alarm / expiry 行为符合预期。
- Hosted service 始终只返回 `captured-not-validated`。
- 实际 Stage 1 response 能被当前 Harness validator 接受。

生产化时建议继续增加 origin/auth、session payload size limit、Rate Limit / abuse protection、observability，以及大对象拆分策略。
