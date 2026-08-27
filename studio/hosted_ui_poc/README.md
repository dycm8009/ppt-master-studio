# Hosted Confirm UI POC（方案 B4 + B3P/B3E 兼容）

这是隔离验证目录，不改变当前 `static-html` 生产路径。

B2 已验证 Cloudflare Worker + Static Assets + per-session Durable Object 的 Hosted transport。B3P 又证明 ChatGPT Plus 桌面版能发现网页注册的 3 个 Site Tools，但在当前宿主里“发现”没有自动等于“模型执行层可调用”。因此 Plus 默认路径升级为 **B4 Browser Handoff**；B3P Site Tools 与 B3E remote MCP 都保留为可选加速/兼容层。

正常用户路径不依赖用户本机 `curl`、Python、Wrangler、repo checkout、Work mode 或自定义 MCP App。

## B4 默认架构（Plus）

```text
ChatGPT / PPT Master Harness
        |
        | 生成 browser bootstrap URL
        | payload 放在 #fragment（不随 HTTP 发送）
        v
Hosted root page /
        |
        | 读取 fragment -> 立即从地址栏清除
        | same-origin POST /api/sessions
        v
Durable Object session storage
        |
        +---- /s/<token> ----> 用户确认
        |
        +---- capture response
                         |
                         | response 编码进本地 #fragment
                         v
                  用户回到 ChatGPT
                         |
                         v
                ChatGPT Harness validate
```

Hosted service 仍然只负责 capture。它不能生成 `accepted.stage1.json`，也不能把 `captured-not-validated` 升格为 accepted；最终 authority 始终是 PPT Master Studio 本地 Harness validator。

## B4 Browser Handoff

### Bootstrap

ChatGPT 使用 Harness 生成的真实 surface payload 构造：

`https://<worker>.<account>.workers.dev/#ppt-master-bootstrap=<base64url-envelope>`

Envelope schema：`ppt-master-browser-bootstrap/v1`。

关键边界：

- Stage payload 位于 URL fragment；浏览器不会把 fragment 作为 HTTP request target 发送给 Worker。
- 根页解析后立即用 `history.replaceState` 清除 bootstrap fragment，再同源 `POST /api/sessions`。
- 创建成功后页面自动 `location.replace('/s/<token>')`，用户直接进入确认页。
- POC 对单个 browser handoff envelope 限制为 24 KiB，超限必须回到更强的 Host Adapter，而不是静默截断。

### Capture handoff

用户点击“确认并捕获”后：

1. response 正常写入 Durable Object；ack 仍为 `captured-not-validated`。
2. 页面额外生成 `ppt-master-browser-capture/v1` envelope。
3. envelope 仅写入当前 `/s/<token>#ppt-master-captured=...` 的本地 fragment。
4. 用户保持页面打开并回到 ChatGPT；ChatGPT 从当前 Browser URL 接力取得 response，然后在自己的 Harness 环境中执行 `static_ui_adapter.py validate`。

Capture fragment 只是 POC host handoff，不是 accepted receipt。只有本地 validator 生成 `static_ui/accepted.<surface>.json` 后 Gate 才算 accepted。

## B3P：可选 Site Tools

根页仍注册恰好 3 个 Site Tools：

- `create_confirm_session(surface, payload)`
- `get_confirm_session(session)`
- `get_confirm_response(session)`

真实 ChatGPT Plus Desktop 已验证 Site Tools discovery：PASS（2 read + 1 write）。但当前宿主没有把这些网页工具稳定注入到模型可调用 tool set，所以 Site Tools 不再是 Plus 默认 acceptance path；如果未来宿主提供稳定 invocation，它可以无缝替代 B4 的 fragment handoff。

## B3E：可选 Remote MCP

远程 MCP endpoint：`https://<worker>.<account>.workers.dev/mcp`。

它继续暴露同样 3 个动作并复用相同 Durable Object 后端，只用于支持完整自定义 MCP 的套餐/工作空间，不是 Plus 默认路径。

## Harness authority

B4、B3P、B3E 都不提供 `accept`、`validate`、`approve` 或任何能制造 Harness accepted receipt 的远端动作。`validate_stage1_gate.py` 仅保留为开发者 E2E / regression / disaster-debug 工具，不是生产用户流程。

## Deploy / regression

GitHub Studio Regression 会：

- 运行 Studio smoke；
- 运行 B2 Durable Object transport smoke；
- 验证 Site Tools 注册/读写 contract；
- 验证 B4 bootstrap/capture fragment encode/decode contract；
- 安装可选 B3E MCP dependencies；
- 执行 Wrangler bundle dry-run。

`.github/workflows/hosted-ui-poc-deploy.yml` 在 `studio-dev` push 后自动部署 Cloudflare POC。仓库已配置 `CLOUDFLARE_API_TOKEN` 与 `CLOUDFLARE_ACCOUNT_ID` 后，部署不再依赖开发者本机。

## 已验证

### B2 transport：PASS

- workers.dev URL 可达。
- Durable Object migration / binding 可正常创建 session。
- 创建后的 session 可立即读取。
- 浏览器 `/s/<token>` 可保持 token 路由并加载 Stage 1 UI。
- 用户 capture 后 Host 可立即读取 response。
- Hosted API 返回 `Cache-Control: no-store`。
- Hosted capture ack 始终为 `captured-not-validated`。

### B3P discovery：PASS

- ChatGPT Plus 桌面版内置 Browser 能发现根页 Site Tools。
- 列表恰好 3 个动作：2 read + 1 write。

### B3P model invocation：当前宿主 BLOCKED

- 即使在聊天中显式关联当前 Browser 页面，Site Tools 没有稳定出现在模型执行层可调用 tool set。
- 因此不把这一步作为 Plus 默认 dependency。

## B4 剩余 Gate

Do not merge until：

- 自动部署含 B4 Browser Handoff 的 Worker bundle；
- ChatGPT 生成一个 Stage 1 bootstrap URL，用户只需在内置 Browser 打开；
- 页面无需 Site Tool invocation 即自动创建 session 并进入 `/s/<token>`；
- 用户点击确认后，当前 URL 出现 `#ppt-master-captured=...`；
- 用户回聊天后，ChatGPT 能从 Browser URL 接力 decode captured response；
- 使用真实 Stage 1 project payload 在 ChatGPT Harness 内生成 `accepted.stage1.json`；
- 24h alarm / expiry 的线上长时行为。

## Production hardening

POC 当前 Hosted API / Site Tools / MCP endpoint 未加用户身份绑定。fragment 不会发送给服务器，但仍会存在于当前浏览器地址栏/本地 history 表面，因此 production 需要评估更严格的本地清除策略、身份/授权、session payload size limit、rate limiting / abuse protection、observability、审计以及大对象拆分策略；不得因为 Host Adapter 变化而降低 Harness Gate、Recovery 或 `project_state` 约束。
