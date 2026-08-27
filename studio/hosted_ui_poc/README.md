# Hosted Confirm UI POC（方案 B3）

这是隔离验证目录，不改变当前 `static-html` 生产路径。

B2 已验证 Cloudflare Worker + Static Assets + per-session Durable Object 的 Hosted transport。B3 在同一个 Worker 上增加远程 MCP Host Adapter，使 ChatGPT 能直接创建确认 session、读取状态并取回用户 response；正常用户路径不依赖用户本机 `curl`、Python、Wrangler 或 repo checkout。

## 目标架构

```text
ChatGPT / PPT Master Harness
        |
        | remote MCP tools
        v
/mcp  Host Adapter
        |
        v
Durable Object session storage
        |
        +---- /s/<token> ----> 用户浏览器确认
        |
        +---- captured response ----> ChatGPT
                                      |
                                      v
                         local Harness validate
```

Hosted service 仍然只负责 capture。它不能生成 `accepted.stage1.json`，也不能把 `captured-not-validated` 升格为 accepted；最终 authority 始终是 PPT Master Studio 本地 Harness validator。

## B3 MCP endpoint

远程 MCP endpoint：

`https://<worker>.<account>.workers.dev/mcp`

使用 Cloudflare Agents SDK 当前推荐的 stateless `createMcpHandler()` 路径。MCP server 与现有 `/api/*`、`/s/<token>` 共享同一个 `SESSIONS` Durable Object binding。

暴露 3 个工具：

- `create_confirm_session(surface, payload)`：创建 24h Hosted session，返回 `confirm_url`；不会创建 accepted receipt。
- `get_confirm_session(session)`：只读 session 状态，不返回私有 payload。
- `get_confirm_response(session)`：用户尚未确认时返回 `pending`；确认后返回 captured response，并明确 `harness_status=not-validated`。

MCP tools 不提供 `accept`、`validate`、`approve` 或任何能制造 Harness accepted receipt 的远端动作。

## ChatGPT-native 正常用户路径

1. ChatGPT 内的 PPT Master Harness 生成 Stage payload 和真实 hashes。
2. ChatGPT 调用 `create_confirm_session`。
3. ChatGPT 把返回的 `confirm_url` 给用户。
4. 用户只在浏览器里确认，不需要打开终端。
5. 用户回到 ChatGPT 后，ChatGPT 调用 `get_confirm_response`。
6. ChatGPT 在自己的 Harness 运行环境中执行 `static_ui_adapter.py validate`。
7. 只有 validator 生成 `static_ui/accepted.<surface>.json` 后 Gate 才算 accepted。

`validate_stage1_gate.py` 仅保留为开发者 E2E / regression / disaster-debug 工具，不是生产用户流程。

## 在 ChatGPT 中连接 POC

ChatGPT 需要支持远程自定义 MCP App 的 Developer Mode。创建一个自定义 App，endpoint 填部署后的 `/mcp` URL，然后 Scan Tools；扫描结果应恰好包含上面的 3 个工具。POC 当前不配置 OAuth，因此只适合隔离测试。正式上线前必须增加认证和访问控制。

注意：`create_confirm_session` 属于写动作；实际可用性受当前 ChatGPT 套餐、workspace policy 和 Developer Mode 权限控制。若当前 workspace 只允许 read/fetch MCP，则 B3 的 create 工具不能完成端到端测试。

## Deploy / regression

开发者部署一次即可：

```sh
cd studio/hosted_ui_poc
npm install
npx wrangler deploy --dry-run
npx wrangler deploy
```

GitHub Studio Regression 会安装该目录依赖、继续运行 B2 transport smoke，并执行 Wrangler MCP bundle dry-run，避免 MCP import/config 破坏 Worker 打包。

## B2 已验证

- workers.dev URL 可达。
- Durable Object migration / binding 可正常创建 session。
- 创建后的 session 可立即读取。
- 浏览器 `/s/<token>` 可保持 token 路由并加载 Stage 1 UI。
- 用户 capture 后 Host 可立即读取 response。
- Hosted API 返回 `Cache-Control: no-store`。
- Hosted capture ack 始终为 `captured-not-validated`。

## B3 剩余 Gate

- 部署含 `/mcp` 的新 Worker bundle。
- ChatGPT Developer Mode 能成功 Scan Tools，并只发现 3 个预期动作。
- 从 ChatGPT 内部真实调用 `create_confirm_session`，无需用户终端操作。
- 用户浏览器确认后，从 ChatGPT 内部调用 `get_confirm_response` 取回结果。
- 使用真实 Stage 1 project payload 在 ChatGPT Harness 内生成 `accepted.stage1.json`。
- 24h alarm / expiry 的线上长时行为。

## Production hardening

POC 当前 MCP endpoint 未加认证。生产化前至少增加 OAuth/身份绑定、origin/auth policy、session payload size limit、rate limiting / abuse protection、observability、审计和大对象拆分策略；不得因为 MCP 接入而降低现有 Harness Gate 或 Recovery / project_state 约束。
