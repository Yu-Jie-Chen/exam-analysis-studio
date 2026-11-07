---
name: exam-analysis-studio
description: >
  Turn a whole exam paper into a deliverable 试卷分析报告: read the paper, the
  original answer sheet and the answer key, reconcile every score, locate this
  round's priority problems, write the cause and the training task for each lost
  mark, plan a three-stage review, and render the five-page 文源教育 brand PDF
  (plus one-page / two-page / per-question appendix variants). Works for 物理,
  化学, 数学, 英语, 生物, 地理 and other subjects. Trigger phrases include 试卷分析,
  分析这张卷子, 逐题分析, 出分析报告, 考试诊断, 讲卷前备课, 试卷分析反馈.
metadata:
  version: "0.2.0"
  author: "Yujie Chen"
  license: "Proprietary (internal use)"
  repository: "https://github.com/Yu-Jie-Chen/exam-analysis-studio"
---

# 试卷分析 · Exam Analysis Studio

把一份试卷拆成**逐题证据**，再收成一份家长看得懂、老师讲得出、下一次能验收的报告。

方法来自文源教育《高报学生试卷分析操作流程 V1.3》的四步——**核对 → 定位 → 整理 → 备课**。这个 skill 把其中最耗时的"看卷、录题、写诊断"交给模型，把**判断和签核**留给人。

## This skill replaces the vision API

教学工作台的「试卷分析」原来是浏览器把整份卷子发给视觉模型接口，拿回一份 JSON，教师再在编辑器里逐题改。这个 skill 做同一件事，但分析由**你正在对话的模型**完成：

| | 原来的接口方式 | 这个 skill |
|---|---|---|
| 谁看卷 | 外部视觉模型，一次调用，看不出就编 | 逐页 PNG，一页一页看，看不清就留 `null` |
| 产出 | 编辑器里的草稿 | `draft.json`（工作台能直接导入）+ 分析稿 + PDF |
| 改一次 | 重新调接口，整份重来 | 改 `draft.json` 里那一条，重渲染 |
| 版式 | 工作台渲染 | 同一套渲染器（`vendor/` 原样复制），版式一致 |

工作台仍然是**校核、归档、进学生档案**的地方；它只是不再负责"看卷"。

## What this skill produces

```text
work/<id>/
├── source/             # 试卷、答题卡、答案原样归档（sha256 在 manifest.json）
├── pages/              # 逐页 PNG，模型就是要看这些（p01-试卷-1.png …）
├── draft.json          # 唯一真源：工作台可直接「打开草稿」导入
├── analysis.md         # 分析稿（Markdown），给人读
├── analysis.html       # 同一份分析稿，自包含，可打印
├── report.pdf          # 五页品牌报告 —— 交付物
├── report-poster.pdf   # 可选：单页摘要
├── report-compact.pdf  # 可选：两页家长版
├── report-detail.pdf   # 可选：A2 逐题附录
├── review.md           # 校核记录：谁、哪天、通过了哪几题
└── manifest.json       # 材料清单、页数、校验和
```

> **交付默认：`report.pdf`（五页）+ `analysis.html`（校核用）。** 单页、两页、附录版
> 只在用户明确要的时候才出——多出的每一份都要单独校核。

> **渲染器是复制品，不是重写。** `vendor/` 里的五个模块和品牌素材来自教学工作台；
> 改版式请改工作台，再 `python scripts/sync_engine.py --workbench <教学端工作台>` 同步回来。
> 不要为了让某段文字塞进去而改 `vendor/`。

## 报告版式（五页）

| 页 | 回答什么 | 数据来源 |
|---|---|---|
| 1 封面 | 谁的、哪次、什么学科、什么时候出的 | `student` `school` `grade` `subject` `exam` `analysisDate` |
| 2 左 | 这次考得怎么样：得分、满分、得分率、仪表盘 | 已校核题目的 `score` / `max` |
| 2 右 | 各类题拿了多少分 + 一句题型点评 | 按 `type` 分组；`typeComments` |
| 2 下 | 失分结构（环形图 + 分题型失分条 + 一句判断）、优势 / 短板 / 本轮目标 | 按 `type` 的失分；`strengthText` `weaknessText` `directionText` |
| 3 | 哪些地方丢了分、怎么改（最多 4 题，2×2）+ 三段复习 + 诊断反馈（复盘 / 家长配合 / 接下来） | `priority` 排序；`planFirst/Next/Later`；`teacherCommunication` `parentSupport` |
| 4+ | 附件：每题一段"原答 → 对照 → 参考结果 → 关键解法 → 训练 → 验收" | `appendixIds` 或自动取失分最重的两题 |

硬约束（写文案前先看，超了会直接报错）：**题型最多 6 类**；`strengthText` /
`weaknessText` 各 ≤75 字；`directionText` ≤50 字；`planFirst` / `planNext` / `planLater`
各 ≤110 字；`teacherCommunication` ≤110 字；`parentSupport` ≤100 字；附件最多 5 题。
详见 [`references/report-layout.md`](references/report-layout.md)。

**把版式写满，不要留白。** 优势、短板各写到 3 行左右；三段复习每段 4–5 行；诊断反馈
两段各 2–3 行。写不满就补证据（题号、失分、步骤），不要用套话凑字；每块最多留 1–2 行白。
家长看不懂"多配合"，`parentSupport` 要写成能照做的动作：看什么、说什么、不做什么。

## Non-negotiable rules

1. **原卷优先，不许"整理"。** 题干条件、数据、单位、选项、小问一个字都不改。看不清就写 `[?]` 并问，不要补一个"应该是"的数。
2. **分数只有三种状态：已核、待核、没有。** 分项评分依据不足、字迹不清、缺页缺答案——`score` 留 `null`，`mastery` 写「待核实」。**待核不是零分**，报告会单独统计「已核 / 待核」。
3. **整题和小问不能重复计分。** 一道题要么按整题一个计分单元，要么按小问拆开，二选一。
4. **每个诊断都要挂到原始作答上。** 原因不许只写"粗心""基础差"；要写"会到哪一步、卡在哪、证据是答题卡哪一行"。
5. **机器整理，教师签核。** 所有 `reviewed` 一律 `false`，直到老师看过分析稿并同意——`run.py approve` 是唯一的签核动作。签核前渲染出来的报告，分数全部按"待核"计。
6. **不虚构教学事实。** 没讲过的内容不写"已教"，没做过的沟通不写"已沟通"，没给的练习不写"已完成"。`teachingClass` / `teachingEvidence` / `followup` 由老师填。
7. **一次真源。** `draft.json` 是唯一真源；`analysis.md`、`analysis.html`、`report.pdf` 都是它的投影。两者不一致时，改 JSON 再重渲染。
8. **版式不改。** 报告撑破是文案太长，不是模板太窄。按错误提示精简，不要动 `vendor/`。
9. **隐私。** 学生姓名只出现在给这个学生自己的报告里；示例、截图、公开仓库一律换成占位名。报告不含班级排名、身份证号、家长手机号。

## Choose a route

| 用户意图 | 走法 | 先读 |
|---|---|---|
| 一份完整考卷 → 五页报告 | **Full** | [`references/workflow.md`](references/workflow.md) |
| 只看某几道题 / 补写某几段文案 | **Partial** | [`references/workflow.md`](references/workflow.md) §局部修订 |
| 讲解后独立复做（B 类服务） | **Retake** | [`references/workflow.md`](references/workflow.md) §复做 |
| 材料还没齐（缺页、缺答案、缺答题卡） | **Intake** | [`references/input-materials.md`](references/input-materials.md) |
| 已有工作台草稿，只想要 PDF | **Render** | [`references/report-layout.md`](references/report-layout.md) |
| 出报告前自查 | 任何路线 | [`references/quality-gates.md`](references/quality-gates.md) |

## Workflow at a glance

0. **收料** — 试卷、原始答题卡、成绩、参考答案与评分细则；缺什么一次说清。
1. **建档** — `run.py new` 复制材料、算校验和、写 `draft.json` 骨架。
2. **看图** — `run.py pages` 出逐页 PNG，**一页一页看**，不看文字层代替看图。
3. **核对** — 全卷过一遍：题号、满分、得分、原始作答，缺依据的留 `null`。
4. **定位** — 做得好的题、本轮优先问题、卡在哪一步、初判错因（等学生确认）。
5. **整理** — 逐题写满 `draft.json`；`run.py check` 过结构；`run.py digest` 出分析稿。
6. **备课** — 三段复习、要问的问题、要讲的重点、选一道代表题进附件。
7. **签核** — 老师看 `analysis.html`，改完 `run.py approve --all --reviewer <名字>`。
8. **交付** — `run.py render`（默认五页）；需要归档就在工作台「打开草稿」导入 `draft.json`。

## Minimum output contract

一份合格的报告必须包含：

- 覆盖**全卷**的计分单元（不是只写错题）；
- 每个单元的原卷位置、原始作答、参考结果、关键解法、评分点与评分来源；
- 失分单元的原因、训练任务、验收标准；
- 两条以上**关联题号**的难度依据；
- 三段复习安排与老师 / 家长各一段可执行的话；
- `student` `exam` `teacher` `analysisDate` `reviewer` `reviewDate` `deliveryDate` 齐全；
- 至少两题进附件，且每题都有原答与关键解法。

字段口径见 [`references/output-schema.md`](references/output-schema.md)。

## Quality gates (summary)

| Gate | 阻塞问题 |
|---|---|
| 材料 | 材料齐了吗？缺页缺答案有没有写进 `materialNotes`？ |
| 覆盖 | 每个计分单元都有一行记录吗？整题与小问有没有重复计分？ |
| 分数 | 得分与满分对得上吗？待核项标成 `null` 了吗？ |
| 证据 | 每个诊断都能指到原始作答的具体位置吗？ |
| 版式 | 题型 ≤6 类、短摘要不超字数、附件题号存在吗？ |
| 签核 | 老师看过分析稿吗？`reviewed` 是老师点的吗？ |
| 隐私 | 姓名、学校、排名、联系方式该在的都在、不该在的都不在？ |

完整清单：[`references/quality-gates.md`](references/quality-gates.md)。

## Stop and ask when

- 试卷缺页、答题卡缺题、答案或评分细则缺失 —— 先说清"这一轮能分析到哪"，再动手；
- 分数看不清（涂改、勾选与得分矛盾）—— 不要替学生"猜"一个分数；
- 一道题的官方答案与你的解法冲突 —— 标出来问，不要两边都写；
- 题型名称超过 6 类 —— 先问怎么合并，不要硬塞；
- 用户要求"按这个分数"写结论，但分数待核 —— 先确认待核范围；
- 材料里出现别的学生姓名或整班成绩 —— 停下，这是另一份材料。

## Helper scripts

```bash
# 0. 建档（复制材料、算校验和、写骨架）
python scripts/run.py new 试卷.pdf 答题卡.pdf 答案.pdf \
  --student 王小明 --grade 高三 --subject 物理 \
  --exam "高三第一次月考" --teacher 陈老师 --date 2026-10-25

# 1. 逐页 PNG（模型看图用；--text 只作辅助，不能代替看图）
python scripts/run.py pages work/20261025-物理-王小明 --max-width 1800

# 2. 进度 / 结构校验 / 分析稿
python scripts/run.py status work/20261025-物理-王小明
python scripts/run.py check  work/20261025-物理-王小明
python scripts/run.py digest work/20261025-物理-王小明

# 3. 教师签核（分析稿看过才做这一步）
python scripts/run.py approve work/20261025-物理-王小明 --all --reviewer 陈老师

# 4. 渲染（默认五页；可选 poster / compact / detail）
python scripts/run.py render work/20261025-物理-王小明 --preview
python scripts/run.py render work/20261025-物理-王小明 --format compact --docx

# 5. 一步到底：check + digest + render，只输出三行
python scripts/run.py finish work/20261025-物理-王小明
```

单脚本也可以直接用：`render_pages.py`、`validate_draft.py`、`build_digest.py`、`render_report.py`。

依赖：`pip install -r requirements.txt`（`reportlab`、`python-docx`、`pypdfium2`、`PyMuPDF`）。
`run.py` 会自动找一个装好这些模块的解释器；找不到就用 `--python <路径>` 指定。

## First-run checklist

- [ ] 材料齐了吗？缺的写进 `materialNotes`，并说清这一轮的分析范围。
- [ ] `pages/` 里每一页都看过了吗？有没有跳页？
- [ ] 逐题表覆盖全卷了吗？整题 / 小问只保留一种粒度。
- [ ] 待核分数都写成 `null` 了吗？
- [ ] 每个失分题都有原因、训练、验收吗？
- [ ] 短摘要的字数在限制内吗？（`run.py check` 会报）
- [ ] 老师签核了吗？（`run.py approve`）
- [ ] 五页 PDF 打开看过吗？附件题目选对了吗？

## Repository layout

```text
exam-analysis-studio/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
├── scripts/
│   ├── run.py               # 主入口
│   ├── render_pages.py      # PDF/图片 → 逐页 PNG
│   ├── validate_draft.py    # 结构 + 阻塞项
│   ├── build_digest.py      # 分析稿 md/html
│   ├── render_report.py     # 交付文件渲染
│   ├── sync_engine.py       # 从教学工作台同步 vendor/
│   ├── engine.py            # vendor/ 加载器
│   └── pyenv.py             # 找一个装好依赖的解释器
├── vendor/                  # 渲染器与品牌素材（来自教学工作台）
├── references/
├── templates/
└── examples/
```

## Design principle

报告的价值不在排版，而在**每一条结论都能回到原卷的某一行**。所以这个 skill 保留了
逐题的原始作答、评分来源和证据位置——即使结论后来被推翻，也能看出当时看到的是什么。
