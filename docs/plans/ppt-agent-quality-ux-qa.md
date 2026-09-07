# PPT Agent 方案实施质量检查与修复记录

检查日期：2026-09-08（Asia/Taipei）  
仓库：`dycm8009/ppt-master-studio`  
实施分支：`plan/ppt-agent-quality-ux`  
关联：[PR #34](https://github.com/dycm8009/ppt-master-studio/pull/34)  
规划：[质量与流程体验升级路线图](ppt-agent-quality-ux-roadmap.md)

## 1. 结论与范围

**本批已实现能力中复现的缺陷已修复，定向行为回归与现有 Studio Regression 均通过；整个路线图尚不具备完成验收条件。**

此次不是只看 CI 绿灯。检查覆盖代码、工件所有权、实际 Chromium 交互、当前文件与旧回执冲突、资源变化、故事板解析、实验输入和 Runtime 打包兼容性。未执行完整主题到最终 PPTX 的人工端到端验收，也未在目标 PowerPoint 中验证文字、图表、公式或播放行为。

稳定基线由本次 GitHub branch metadata 取得：`studio-main@527ec8d079ce18aa7b2e015f1ec896800779bb30`。被检查的原实现为 `45ea5a42aacee0875bd3e445fea4bfa898978c9d`。修复仅进入实施分支，没有合并、发布 Runtime 或部署生产 Worker。

## 2. 可复现证据

| 阶段 | 提交与证据 | 结果 |
| --- | --- | --- |
| 原实现既有回归 | [Studio Regression](https://github.com/dycm8009/ppt-master-studio/actions/runs/34139311502) | 通过，但未覆盖本次发现的行为问题 |
| 先加入失败复现 | `e9ec523cc37bac00d62981c1e5ff3c6a214cc64c`；[针对性 QA](https://github.com/dycm8009/ppt-master-studio/actions/runs/34142197429) | 11 个 Python 用例、4 个 Chromium 用例失败；这是 15 个失败场景，不是 15 个独立根因 |
| 同一失败提交的既有回归 | [Studio Regression](https://github.com/dycm8009/ppt-master-studio/actions/runs/34142197395) | 仍通过，证明原测试有覆盖缺口 |
| 修复与扩展回归 | [`7cf51a252409229867785820b4a1b7c8c0ac7c0b`](https://github.com/dycm8009/ppt-master-studio/commit/7cf51a252409229867785820b4a1b7c8c0ac7c0b)；[针对性 QA](https://github.com/dycm8009/ppt-master-studio/actions/runs/34144482868) | 30/30 Python、10/10 真实 Chromium 用例通过 |
| 修复后的既有回归 | [Studio Regression](https://github.com/dycm8009/ppt-master-studio/actions/runs/34144482862) | 全部步骤成功，包括无 Flask Runtime、Hosted UI 合约、打包白名单和 Wrangler dry-run |

测试工作流检出精确 PR HEAD，使用只读仓库权限；失败时保留日志及该提交的已跟踪源码供复现，未包含未跟踪环境文件。测试中的批准 JSON 均属于合成临时项目，不是代替用户批准真实作品。

本地执行了 30 项 Python 用例、原有五组定向脚本、完整控制面冒烟及 Runtime headless 测试。当前执行容器无法下载 Chromium，因此浏览器成功结论来自上述实际 GitHub runner 日志，不能描述为本地浏览器验证。

## 3. 缺陷与修复

| 优先级 | 已复现问题 | 修复内容 | 主要回归 |
| --- | --- | --- | --- |
| P0 | XML 被序列化为 `ns0:svg`，插入 HTML 后不是实际 SVG；审阅区无真实页面 | 正确声明 SVG 命名空间；浏览器检查节点类型、命名空间、尺寸和文字 | 实际页面显示、横竖画布比例 |
| P0 | 仅对比缓存 manifest/receipt，没有比较当前 SVG，修改后仍可能显示可导出 | Harness 重新计算当前有序 SVG 与资源快照；`apply-response`、`status`、`assert-approved` 共享当前证据检查 | 修改、增页、删页、坏 XML、HTML 修改、导出前再检查 |
| P0 | 自包含 HTML 留有相对图片引用；图片/图标单独变化不影响批准哈希 | 使用既有资源路径解析器及图标构造助手内嵌项目素材；依赖字节摘要纳入 roster | HTML 移位后图片可解码、图片/图标变化后旧回复被拒绝 |
| P0 | 已完成后再修改意见，旧批准 JSON 仍可复制；清空修改意见可能恢复旧批准 | 草稿变化立即清空结果 JSON；逐页有效性重新判断；无效修改不能保留原批准 | 完成后修改、无评论修改、历史决定不预选 |
| P1 | Clipboard API 与 fallback 失败仍显示“已复制” | 只在实际成功时显示成功；失败给出手工复制提示；避免异步旧结果污染新草稿 | 模拟两条复制路径失败 |
| P1 | 缺少 response 或回执字段时可推断为 approved | 校验 manifest、response、receipt 的类型、计数、结果、哈希和页标识；历史只读取完整有效证据 | 缺失字段、缺失 response、损坏历史、错误 ordinal、原样保留评论 |
| P1 | Storyboard 将代码中的 Markdown 标题/字段误当规划，且丢失缩进 | 结构解析屏蔽代码围栏；保留字面缩进；拒绝重复页身份/字段和不一致页数 | C++ 代码、围栏内标题、重复页、代码内容浏览器展示 |
| P1 | 缺少源文档/HTML 或篡改 JSON 后仍读取旧故事板 | `load_current` 重新投影当前 Design Spec，校验派生 JSON 和 HTML；两项实验复用此入口 | 源修改/删除、HTML 删除、JSON 修改、实验拒绝过期输入 |
| P1 | Host 自行重解释 Gate；编辑器历史计数被当作当前已应用 | Deck/Storyboard 状态委托 Harness；Confirm 复用官方阶段构建逻辑；编辑器计数仅作为历史信息，未知远端状态不冒充已验证 | 新会话覆盖旧结果、历史 editor cursor 不产生正向状态 |
| P1 | 语义实验删除比较符号，把 `x > 0` 与 `x < 0` 判为相同 | 比较仅归一化空白及大小写；保留运算符；输出说明实际覆盖仅为文本结构启发式 | 不同运算符不误报重复 |
| P2 | 路线图 DoD 截断于“重大叙”，PR 描述仍为纯文档 | 补齐 DoD，并增加逐工作流真实实施状态；更新 PR 范围 | 文档审查及变更范围复核 |

同时隔离 SVG 元素 ID，避免页面元素与审阅控件同名；移除执行性构造并安全嵌入 JSON；损坏的派生文件可由其 owning source 重建。单文件派生输出采用临时写入后替换，降低半写文件风险。

## 4. 权威与兼容边界

- Workflow、人工 Gate 和质量裁决仍在 `skills/ppt-master`。Host 仅调用并呈现官方状态；`access_provided` 仍不能由文件存在或脚本成功推断。
- 真实 SVG 审阅没有替换成 PNG/JPEG/contact sheet。项目图片作为资源内嵌，不把整页栅格化。
- 旧资源无依赖的 roster 保留原摘要算法；有资源依赖的旧审阅需要重建。资源变化生成新 roster，新版本仍需人工批准，没有实现逐页 approval reuse。
- 普通 Default 在进入 Step 7 或恢复导出前运行 `deck_review_handoff.py assert-approved`；该命令只检查 Deck Review，不替代 final SVG quality、图片就绪及其他官方 Gate，也不擅自扩展到 Quick 或 native 路由。
- 浏览器不能呈现的媒体、未闭合的资源、外部网络图片等明确报错，不静默留下空白，也不代替用户重新选择资源。EMF/WMF 等仍需另行设计可验收的官方预览路径，本次没有宣称支持。
- Storyboard 是静态快照；`status` 在重新检查时发现失效，不表示已打开的离线 HTML 能实时感知源文档变化。
- 代表页选择与语义工具保持 experiment-only、nonblocking；未修改 P01 后连续生成的生产节奏，没有事实正确性或视觉拓扑验证能力声明。

## 5. 复跑入口

从仓库根目录运行，下列均使用合成测试项目：

```bash
python skills/ppt-master/scripts/attribution_guard.py
python -S studio/tests/quality_ux_adversarial_test.py
python studio/tests/smoke_test.py
python studio/tests/runtime_bundle_headless_test.py
```

在具备浏览器依赖下载能力的测试环境：

```bash
python -m pip install playwright==1.57.0
python -m playwright install --with-deps chromium
python studio/tests/quality_ux_browser_test.py
```

GitHub 自动化入口为 `.github/workflows/quality-ux-qa.yml` 与既有 `studio-regression.yml`。本次 runner 有工具链弃用告警，但测试没有被跳过；生产 Worker 仅做 dry-run，未进行发布。

## 6. 仍未完成的路线图工作

本批修复解决已有实现的正确性问题，不把未实施功能标成已完成。WS-A 尚缺前端统一状态与完整自动回传闭环；WS-C 尚无新增内容绑定三方向 UI；WS-D/WS-E 尚无固定语料、盲评与改善基线；WS-F 尚缺完整修改范围/依赖追踪/合法批准复用；WS-G/WS-H 尚缺目标 PowerPoint 验证与统一项目工作区。

PR 应保持 Draft。发布前还需要完整真实项目的人工使用验收、目标平台验证，以及以数据证明的质量/返工改善。不能以本次 40 项针对性测试通过，替代整个路线图的验收。
