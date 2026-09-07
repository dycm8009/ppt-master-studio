# PPT Master Studio — PPT Agent 质量与流程体验升级路线图

状态：Proposal  
基线：`studio-main@527ec8d079ce18aa7b2e015f1ec896800779bb30`  
范围：以 Default Generate 为首个落地点；不在 Host 层建立第二套 PPT workflow / Gate authority。

## 1. 目标

把 PPT Master Studio 从“严格工作流驱动的 PPT 生成器”推进为“围绕真实作品逐步决策、可验证、低返工的协作式 PPT Agent”。

两个核心目标：

1. **提高输出质量**：更早发现内容、叙事、视觉表达和最终 PPTX 的问题。
2. **提高过程体验**：用户始终知道当前状态、实际作品、待决策事项和修改影响范围。

非目标：

- 不以增加模板、动画数量或 Agent 数量作为成功指标。
- 不在 ChatGPT Host adapter 中复制 Strategist / Executor / Deck Review / QA 规则。
- 不绕过现有人工确认 Gate、roster hash 或最终 SVG quality gate。
- 不把模型主观评分作为唯一质量证明。

## 2. 设计原则

### 2.1 作品优先于配置

每次需要用户判断时，尽量让判断绑定到实际内容、故事板、真实 SVG 或最终 PPTX，而不是抽象参数。

### 2.2 只在需要人的判断时阻塞

需要用户决定：沟通目标、内容边界、设计方向、最终页面是否接受。  
不需要用户推动：确定性校验、派生文件重建、已确认方案内的常规生成和受影响下游重跑。

### 2.3 单一权威

官方 Harness 是 workflow、Gate、artifact ownership、recovery 和 QA 的唯一权威。Host/UI 只负责呈现、传输、持久化适配和状态投影。

### 2.4 状态必须可证明

区分：

`generated → presented/access-provided → user-submitted → validated → applied`

不得把页面打开、远端 capture、静默或旧 receipt 表述为已经确认或已经应用。

### 2.5 修改应有边界

用户要求局部修改时，先确定 target / allowed changes / invariants / dependent artifacts，只重跑受影响链路；不得无理由全套重生成。

---

## 3. 目标用户旅程

下面是用户体验层的六个阶段。它们是现有 Harness 工件与 Gate 的投影，不是新的独立 workflow。

| 阶段 | 用户看到 | 用户判断 | Harness/Agent 责任 |
|---|---|---|---|
| 1. 对齐目标 | 已预填的受众、目标、场景、内容边界 | 是否正确理解任务 | 从现有输入推导，只询问真正缺口 |
| 2. 故事与方向 | 故事板 + 3 个内容相关设计方向 | 是否这样讲、选哪个方向 | Strategist 形成完整方案并推荐最佳方向 |
| 3. 代表页校准 | 使用真实内容的典型/高风险页面 | 密度、表达和视觉语法是否成立 | 在大规模制作前验证方法风险 |
| 4. 完成全稿 | 真实页面和进度 | 通常无需操作 | 连续完成页面和确定性检查 |
| 5. 审阅与修订 | 实际 SVG、逐页意见、版本差异 | 页面是否准确清楚 | 有边界地修改并重验依赖 |
| 6. 验证与交付 | PPTX、能力说明、重要告警 | 是否可投入使用 | 验证实际交付物和可编辑边界 |

---

## 4. Workstreams

## WS-A — 可靠交互与状态协议（P0）

### 问题

确认页面、Deck Review 和 ChatGPT 之间可能存在“用户以为完成，但 Harness 尚未验证/应用”的认知落差；可访问 artifact 失败时，用户甚至可能看不到需要审阅的实际内容。

### 计划

1. 定义统一的用户可见状态模型：
   - `artifact_generated`
   - `access_provided`
   - `remote_captured`
   - `locally_validated`
   - `applied`
   - `stale`
2. Hosted Confirm UI、Hosted Editor、Deck Review adapter 映射到同一状态语义。
3. 自动 pull/apply 成功后禁止继续要求用户 copy JSON。
4. 自动反馈不可用时，只暴露一个明确 fallback 动作：复制 confirmation JSON 回聊天。
5. 对 launch/access 失败、capture 成功但 apply 失败、旧 receipt、roster mutation 建立端到端测试。
6. UI 文案禁止使用无法证明的“已同步”“已确认”“已应用”。

### 验收

- 不存在 remote `captured-not-validated` 被显示为已完成的路径。
- Deck Review 无法访问时不会被文字摘要假装替代。
- 用户一次提交后，系统能明确指出当前状态和唯一下一动作。
- 自动 apply 成功路径不再要求人工重复返回 JSON。

---

## WS-B — 可评审故事板（P1）

### 问题

Design Spec 已有精确 page roster，但用户不容易在正式页面制作前检查整套论证是否成立。

### 计划

从现有 `design_spec.md §IX` 投影一个只读 Storyboard View，不创建第二份叙事权威。每页至少展示：

- page id / title
- page job / audience takeaway
- key claim
- evidence / source dependency
- relationship to previous/next page
- intended visual structure / major object plan
- risk flags（如高密度、复杂 chart/table、code、formula、image dependency）

StoryBoard 修改必须回写到 owning Strategist/Design Spec 流程；view 自身不成为 authority。

### 验收

- Storyboard 与当前 Design Spec page roster 一一对应。
- roster 修改后旧 Storyboard 自动标记 stale。
- 不存在 Storyboard 与 Design Spec 可独立分叉的持久状态。
- 在评测集上记录“全稿生成后结构性返工率”作为基线和改进指标。

---

## WS-C — 内容绑定的设计方向（P1）

### 问题

三个 design directions 已存在，但用户仍可能主要通过颜色、风格名称等低信息量线索选择。

### 计划

1. Stage 2 的三个方向继续保持 whole-deck solution，不增加方向数量。
2. 每个方向必须明确说明同一段实际内容如何被组织：
   - narrative spine
   - information grouping
   - emphasis strategy
   - representative visual grammar
   - reading/presentation trade-off
3. 方向对比页优先展示“如何解释内容”，视觉 token 作为次级信息。
4. 保持当前确认语义：方向只初始化完整 bundle，最终执行 authority 仍来自确认后的 component values。

### 验收

- 三个方向不能只靠名称/颜色形成差异。
- 每个方向至少能指出一个内容结构或信息承载方式上的实质差异。
- 自动测试确保 Stage 1 仍保持 template-independent。

---

## WS-D — 代表性页面校准（P1，需 Harness 变更）

### 问题

当前 P01 first-page gate 主要校验首个页面的方法问题；封面往往不能覆盖多行正文、复杂图表、架构图、代码等高风险内容。

### 方案

引入 **Representative Coverage Calibration**，但不直接在 Host 层插入新 Gate。

候选策略：

1. P01 保留现有 first-page gate。
2. Strategist/Executor 根据 Design Spec 风险标签选择 0–2 个代表性 coverage targets，例如：
   - dense text / multi-column
   - chart/table
   - architecture/relationship diagram
   - code/formula
   - image-heavy composition
3. 先通过离线评测比较：
   - 当前 `P01 → uninterrupted remaining pages`
   - `P01 + representative calibration → remaining pages`
4. 只有证明显著减少后期返工，才修改官方 generation rhythm 和对应测试。

### 必须解决的流程冲突

当前 Default Generate 明确要求首页面 Gate 后连续生成剩余页面，因此该能力必须修改 `skills/ppt-master` owning workflow，而不能作为 Studio adapter 的额外步骤。

### 验收

- 不破坏现有 first-page method signal。
- 代表页选择可由确定性风险规则解释。
- 相比 baseline，后期大范围布局返工下降；若没有改善则不默认启用。

---

## WS-E — 语义/表达质量检查（P1/P2）

### 目标

把“技术合法”与“表达有效”拆开。

### 检查维度

- 标题是否准确概括本页主张。
- evidence 是否支持 claim。
- 图形 topology 是否匹配语义关系（并列 / 顺序 / 因果 / 层级 / 对比）。
- 图表 encoding 是否容易误导。
- 相邻页面是否重复而没有推进。
- 关键限定条件、例外、数字、来源是否仍然存在。
- 无障碍基础检查：对比度、仅颜色编码、阅读顺序/alt-text 能力边界。

### 输出规则

禁止只输出一个总分。Issue 必须至少包含：

- page id
- category
- severity
- evidence
- expected semantic relationship
- suggested repair scope

模型评审只作为辅助信号；确定性事实错误、资源缺失、schema/geometry failure 继续由现有 blocking gate 负责。

### 集成策略

先以 benchmark / optional diagnostic 形式运行；只有经过 precision/recall 和人工盲评后，才决定哪些规则可升级为默认 advisory 或 blocking。

---

## WS-F — 增量修订与审阅复用（P1/P2）

### 问题

当前 Deck Review 与整个 SVG roster hash 绑定。任意 SVG mutation 后必须重建 review，旧 receipt 不能批准新 deck；这一安全边界必须保留。

### 短期方案

1. 修改请求规范化为：
   - targets
   - allowed changes
   - invariants
   - affected dependencies
2. 修订后重跑 final SVG quality、notes reconciliation 和 Deck Review。
3. 新 review UI 优先突出 changed pages / diff summary，但仍满足当前逐页显式决定要求。

### 长期研究

设计 per-slide content hash + dependency hash 的 review reuse 模型：

- 未变化且依赖未变化的 slide approval 可作为输入证据；
- 新版本是否允许复用必须由 Harness 计算和验证；
- 仍需为新 roster 生成新的合法 receipt；
- 禁止直接复制旧 receipt 或由 Host 自行认定通过。

### 验收

- 非目标页面无意变化率可测。
- 修改后所有 stale artifacts 可追踪。
- 任何 approval reuse 都有 Harness 级 provenance 和新 receipt。

---

## WS-G — 最终 PPTX 验证（P2）

### 问题

SVG review 可以验证页面设计，但不能单独证明 PowerPoint 中的最终换行、字体、原生对象、公式、动画/播放行为完全正确。

### 计划

在现有 package/resource postflight 之外增加 capability-aware delivery verification：

1. 始终执行现有 exporter postflight。
2. 当目标 PowerPoint/Office 渲染环境可用时，增加：
   - open/render smoke test
   - text wrapping/font substitution checks
   - native chart/table/formula checks where applicable
   - notes/transition/animation checks when enabled
3. 环境不可用时明确记录 `not-verified-in-target-powerpoint`，不得伪装为已验证。
4. Delivery Summary 说明真实编辑能力：native text/chart/table/formula、SVG/image carriers、font dependencies、known warnings。

### 验收

- “PPTX 已导出”和“已在目标 PowerPoint 验证”是两个不同状态。
- 交付摘要不使用笼统的“全可编辑”声明。

---

## WS-H — 统一 Project Workspace UX（P2）

### 方向

将 Stage 1 / Stage 2 / Storyboard / Live Preview / Deck Review / Delivery 组织为一个稳定的项目体验，而不是多个互不相关的页面。

建议信息架构：

- 左：page/story roster
- 中：当前真实 artifact / preview
- 右：当前 decision / issue / edit scope
- 顶部：phase、version、authority state、stale/applied 状态

约束：

- UI 不能持有独立 Gate authority。
- 每个视图必须绑定当前 project + pinned Harness + artifact version/hash。
- 任何修改先进入 owning Harness API，再刷新视图。

---

## 5. Benchmark 与质量度量

建立固定评测集，至少覆盖：

1. 中文密集正文
2. C++ / code-heavy 技术培训
3. 多层架构/流程关系图
4. 多 chart/table 数据汇报
5. 图片密集型 deck
6. source-fidelity / beautify 场景
7. 中途局部修改
8. Stage 1/2 中断恢复
9. Deck Review 修改后 roster hash 变化
10. transport failure / copy-JSON fallback

核心指标：

- first successful artifact presentation rate
- confirmation round-trip failure rate
- duplicate user action count
- structural rework after full-deck generation
- unintended non-target slide mutation rate
- final PPTX defect count
- semantic-review precision / false-positive rate
- human blind-review preference / task-success rating

不预设“提升 X%”；先建立 baseline，再以数据决定默认启用策略。

---

## 6. 实施顺序

### Milestone 0 — Baseline & observability

- 固定 benchmark corpus。
- 为 Confirm / Review / Export 建立状态事件和失败分类。
- 记录现有流程的 round-trip、返工和缺陷基线。

### Milestone 1 — P0 reliability

- 实现统一状态协议。
- 修复 artifact presentation / confirmation feedback 的歧义。
- 增加 transport / stale receipt / recovery E2E tests。

### Milestone 2 — Planning visibility

- Storyboard View。
- 内容绑定的 design-direction comparison。
- 不改变现有 Gate 数量。

### Milestone 3 — Quality experiments

- Representative Coverage Calibration benchmark。
- Semantic/communication QA benchmark。
- 只有实验通过阈值后再修改 Default Generate authority。

### Milestone 4 — Incremental revision

- edit scope / dependency tracking。
- changed-page-focused Deck Review UX。
- 研究 Harness-authoritative approval reuse。

### Milestone 5 — Delivery verification & unified workspace

- capability-aware PPTX verification。
- Delivery Summary。
- 统一项目工作区导航。

---

## 7. 推荐代码/文档落点

以下是规划目标，不表示已经实现：

- `skills/ppt-master/workflows/generate-pptx.md`
  - 只有 Representative Calibration 经验证后才修改 generation rhythm。
- `skills/ppt-master/references/strategist.md`
  - Storyboard projection contract / content-bound direction requirements。
- `skills/ppt-master/workflows/stages/deck-review.md`
  - changed-page emphasis；长期 review reuse authority。
- `skills/ppt-master/workflows/governance/failure-recovery.md`
  - 新增 artifact-state / incremental-review recovery entries。
- `skills/ppt-master/scripts/confirm_ui/`
  - authority state projection；不改变确认 ownership。
- `skills/ppt-master/scripts/deck_review_handoff.py`
  - version/diff metadata；长期 per-slide approval evidence。
- `studio/host/chatgpt/`
  - transport/status adapter only。
- `studio/host/cloudflare/`
  - unified status presentation / project navigation，仍保持 transport-only 边界。
- benchmark / regression suite
  - transport, semantic QA, representative calibration, incremental revision, final PPTX verification。

---

## 8. Definition of Done

该路线图完成不能只以功能数量判断。至少满足：

1. 用户每次被要求决策时都能访问实际需要判断的内容。
2. UI/Agent 不再混淆 captured、validated、applied。
3. 重大叙