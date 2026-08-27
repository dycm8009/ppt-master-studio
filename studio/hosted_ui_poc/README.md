# Hosted Confirm UI POC (方案 B2)

这是隔离验证目录，不改变当前 `static-html` 生产路径。

目标：验证 Cloudflare Worker + Static Assets + per-session Durable Object 是否能替代本地单文件 HTML，提供稳定 URL、强一致临时会话和更好的浏览器交互，同时保持 Harness validator 为最终 authority。
