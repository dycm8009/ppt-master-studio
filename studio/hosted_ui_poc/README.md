# Hosted Confirm UI POC（方案 B3P + B3E）

这是隔离验证目录，不改变当前 `static-html` 生产路径。

B2 已验证 Cloudflare Worker + Static Assets + per-session Durable Object 的 Hosted transport。B3 现在分成两条 Host Adapter：

- **B3P（默认，Plus）**：ChatGPT 桌面版内置 Browser + Site Tools / WebMCP。网页自己注册 3 个工具，直接调用同源 `/api/*`，不依赖自定义 MCP Connector。
- **B3E（可选，Business / Enterprise / Edu）**：远程 `/mcp` endpoint，复用相同 Durable Object session 后端。

正常用户路径不依赖用户本机 `curl`、Python、Wrangler 或 repo checkout。

## 目标架构

```text
ChatGPT Plus Desktop + Site Tools
        |
        | page-native WebMCP tools
        v
Hosted root page /   (Host Bridge)
        |
        | same-origin /api/*
        v
Durable Object session storage
        |
        +---- /s/<token> ----> 用户确认
        |
        +---- captured response ----> ChatGPT Site Tool
                                      |
                                      v
                         ChatGPT-local Harness validate

Optional B3E:
ChatGPT Business/Enterprise -> /mcp -> same Durable Object backend
```

Hosted service 仍然只负责 capture。它不能生成 `accepted.stage1.json`，也不能把 `captured-not-validated` 升格为 accepted；最终 authority 始终是 PPT Master Studio 本地 Harness validator。

## B3P：Plus Site Tools Host Bridge

在 ChatGPT 桌面版的内置 Browser 中打开 Worker 根页 `/`。根页检测 `document.modelContext || navigator.modelContext`，并注册恰好 3 个 Site Tools：

- `create_confirm_session(surface, payload)`：写动作。创建 24h Hosted session，返回 `confirm_url`，并在根页显示可点击的确认链接。
- `get_confirm_session(session)`：只读。返回 open/captured/expired 状态，不返回私有 payload。
- `get_confirm_response(session)`：只读。用户尚未确认时返回 `pending`；确认后返回 captured response，并明确 `harness_status=not-validated`。

这 3 个工具是网页原生 WebMCP 工具，不需要 MCP App、Developer Mode 或 MCP Connector。根页应保持打开，因为 Site Tools 只属于提供它们的当前网页；确认页可以另开标签。

### B3P 正常用户路径

1. 用户在 ChatGPT 桌面版内置 Browser 打开 Hosted 根页一次。
2. PPT Master Harness 在 ChatGPT 中生成 Stage payload 和真实 hashes。
3. ChatGPT 调用根页 Site Tool `create_confirm_session`。
4. 根页显示确认链接；用户打开 `/s/<token>` 并点击“确认并捕获”。
5. ChatGPT 调用 `get_confirm_response` 取回用户 response。
6. ChatGPT 在自己的 Harness 运行环境中执行 `static_ui_adapter.py validate`。
7. 只有 validator 生成 `static_ui/accepted.<surface>.json` 后 Gate 才算 accepted。

用户不需要终端、curl、Python、Wrangler 或本地 repo。

## B3E：可选 Remote MCP

远程 MCP endpoint：`https://<worker>.<account>.workers.dev/mcp`。

它使用 Cloudflare Agents SDK `createMcpHandler()`，同样只暴露：

- `create_confirm_session`
- `get_confirm_session`
- `get_confirm_response`

B3E 只作为支持完整自定义 MCP 的套餐/工作空间兼容层，不是 Plus 默认路径。

## Harness authority

无论 B3P 还是 B3E，Host Adapter 都不提供 `accept`、`validate`、`approve` 或任何能制造 Harness accepted receipt 的远端动作。`validate_stage1_gate.py` 仅保留为开发者 E2E / regression / disaster-debug 工具，不是生产用户流程。

## Deploy / regression

GitHub Studio Regression 会：

- 运行 Studio smoke；
- 运行 B2 Durable Object transport smoke；
- 用 mock `modelContext` 验证 B3P 恰好注册 3 个 Site Tools、读写 annotations、create/status/pending/captured 行为，以及 Host Bridge 不泄漏 session payload；
- 安装 B3E MCP dependencies；
- 执行 Wrangler bundle dry-run。

`.github/workflows/hosted-ui-poc-deploy.yml` 可在 `studio-dev` push 后自动部署 Cloudflare POC。仓库配置 `CLOUDFLARE_API_TOKEN` 与 `CLOUDFLARE_ACCOUNT_ID` 后即可让部署不再依赖开发者本机；缺失 secrets 时 workflow 安全跳过真实部署。

## B2 已验证

- workers.dev URL 可达。
- Durable Object migration / binding 可正常创建 session。
- 创建后的 session 可立即读取。
- 浏览器 `/s/<token>` 可保持 token 路由并加载 Stage 1 UI。
- 用户 capture 后 Host 可立即读取 response。
- Hosted API 返回 `Cache-Control: no-store`。
- Hosted capture ack 始终为 `captured-not-validated`。

## B3P 剩余 Gate

- 部署含根页 Site Tools Host Bridge 的新 Worker bundle。
- 在 ChatGPT Plus 桌面版内置 Browser 中打开根页，地址栏确认 Site Tools 可发现。
- Site Tools 列表恰好包含 3 个预期动作。
- ChatGPT 从会话中调用 `create_confirm_session`，无需用户终端操作。
- 用户只在确认页点击确认。
- ChatGPT 调用 `get_confirm_response` 取回 captured response。
- 使用真实 Stage 1 project payload 在 ChatGPT Harness 内生成 `accepted.stage1.json`。
- 24h alarm / expiry 的线上长时行为。

## Production hardening

POC 当前 Hosted API / Site Tools / MCP endpoint 未加用户身份绑定。生产化前至少增加身份/授权策略、session payload size limit、rate limiting / abuse protection、observability、审计和大对象拆分策略；不得因为 Site Tools 或 MCP 接入而降低现有 Harness Gate、Recovery 或 `project_state` 约束。
