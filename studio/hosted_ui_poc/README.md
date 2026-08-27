# Hosted Confirm UI POC（方案 B4 + B3P/B3E compatibility）

这是隔离验证目录，不改变当前 `static-html` 生产路径。

B2 已验证 Cloudflare Worker + Static Assets + per-session Durable Object 的 Hosted transport。Plus 默认路径现在是 **B4 Browser Handoff**；B3P Site Tools 与 B3E remote MCP 保留为兼容层。

正常用户路径不依赖用户本机 `curl`、Python、Wrangler、repo checkout 或 Work mode。

## B4：Plus Browser Handoff（默认）

```text
ChatGPT / PPT Master Harness
        |
        | Stage payload in URL #fragment
        v
Hosted root page /
        |
        | same-origin POST /api/sessions
        v
Durable Object session storage
        |
        +---- auto navigate /s/<token> ----> 用户确认
        |
        +---- capture succeeds
        v
/s/<token>#ppt-master-captured=<browser handoff>
        |
        | current Browser URL returns with the chat turn
        v
ChatGPT decodes response
        |
        v
static_ui_adapter.py validate
        |
        v
static_ui/accepted.<surface>.json
```

浏览器 `#fragment` 不会随 HTTP request 发送到 Worker。根页读取 bootstrap envelope 后立即用 `history.replaceState` 清掉 bootstrap fragment，再同源创建 session。确认成功后，页面把 capture envelope 写入当前 `/s/<token>` URL fragment，供 ChatGPT 内置 Browser 在用户返回聊天时完成 host handoff。

Hosted/browser 层始终只报告 `captured-not-validated` / `harness_status=not-validated`；只有本地 PPT Master Harness validator 能生成 accepted receipt。

POC 的 bootstrap/capture browser handoff envelope 上限为 24 KiB；超过上限必须显式失败，不得截断。

## B4 real Plus/Desktop acceptance：PASS

已在真实 ChatGPT Plus 桌面版内置 Browser + 真实 Cloudflare Worker 完成两轮验证：

1. **Transport round-trip（dummy hashes）**
   - ChatGPT 生成 bootstrap fragment URL；
   - 页面自动创建 Durable Object session；
   - 自动导航到 `/s/<token>`；
   - 用户确认；
   - 页面生成 `#ppt-master-captured=...`；
   - 返回聊天后，ChatGPT 从当前 Browser URL 解码完整 response。

2. **Real Harness Stage 1 acceptance（real hashes）**
   - 使用当前 Studio Harness 生成真实 Stage 1 recommendation/options hashes；
   - 通过同一 B4 Browser Handoff 完成用户确认；
   - ChatGPT 从当前 Browser URL 解码真实 `ppt-master-chat-confirm/v1` response；
   - 在 ChatGPT 运行环境执行 `studio/scripts/static_ui_adapter.py validate`；
   - validator 返回 0，并真实生成 `static_ui/accepted.stage1.json`；
   - accepted receipt 的 recommendation/options hashes 与确认 payload 完全一致。

本次真实 Stage 1 receipt hashes：

- `recommendation_sha256 = ca095617a96f74ba61737013c53de97353d18a4c71e9254779cb329149d6cbdc`
- `options_sha256 = 5d55ae2b5a1fa2e6746868e0644b7bd119f1a3139f17f91827b304ed6e1f1692`

因此 B4 已证明可以在 Plus 中完成：

`Harness payload -> Browser bootstrap -> user confirm -> Browser handoff -> Harness validate -> accepted receipt`

且不需要 Site Tool model invocation、Work mode、自定义 MCP App 或用户本机终端。

## B3P：Site Tools compatibility

根页仍注册 3 个网页原生 Site Tools：

- `create_confirm_session(surface, payload)`
- `get_confirm_session(session)`
- `get_confirm_response(session)`

真实 Plus Desktop 已证明 Site Tools discovery PASS（可见 2 个读取 + 1 个写入工具），但当前宿主没有稳定把 page tools 挂载到模型 execution tool set。因此 B3P 不再是 Plus acceptance dependency。

## B3E：Remote MCP compatibility

远程 MCP endpoint：`https://<worker>.<account>.workers.dev/mcp`。

它复用相同 Durable Object 后端，仅作为支持自定义 remote MCP 的套餐/工作空间兼容层，不是 Plus 默认路径。

## Harness authority

Host Adapter、Hosted 页面、Site Tools 和 MCP 都不能提供 `accept`、`validate`、`approve` 或制造 Harness accepted receipt。最终 authority 始终是 PPT Master Studio 本地 Harness validator。

## Deploy / regression

GitHub Studio Regression 会覆盖：

- Studio smoke；
- B2 Durable Object transport smoke；
- B3P mock Site Tools contract；
- B4 bootstrap/capture fragment encode/decode contract；
- Wrangler bundle dry-run（含可选 MCP endpoint）。

`.github/workflows/hosted-ui-poc-deploy.yml` 使用 GitHub Actions Secrets 中的 `CLOUDFLARE_API_TOKEN` 与 `CLOUDFLARE_ACCOUNT_ID` 自动部署 `studio-dev` 到 Cloudflare，不需要开发者本机 Wrangler。

## 已验证

- workers.dev URL / Durable Object migration / binding；
- create + immediate read-after-write；
- `/s/<token>` route 保持 token；
- capture -> immediate read；
- API `Cache-Control: no-store`；
- capture acknowledgement 始终 `captured-not-validated`；
- Plus Desktop Site Tools discovery；
- Plus Desktop B4 Browser Handoff；
- 真实 Stage 1 Browser confirmation -> ChatGPT Harness accepted receipt。

## 尚未关闭的验证项

- 24h Durable Object alarm / expiry 的真实长时线上行为仍是 long-running validation item。
- 推进到 production 前仍需 identity/auth binding、rate limiting / abuse protection、payload limits、observability/audit，以及 browser fragment 的清理/隐私策略。

在这些项目关闭前，PR 保持 Draft，不晋升到 `studio-main`。
