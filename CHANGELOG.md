# 更新记录

## 0.2.0 — 2026-11-07

版式重排：五页报告不再"把字段塞进去就完事"，每块写到 3–5 行，修掉大面积留白。

- 第 2 页 01：优势 / 短板改为动态排布，各约 3 行；补满分题清单、失分最重、本轮先拿回 N 分
- 第 2 页 03：图例改成"失分 + 占比 + 比例条"，底部补一句失分结构判断
- 第 2 页 04：补"得分最稳的 6 题"表，短板下面不再空一大片
- 第 3 页 05：四道题改 2×2 卡片，每题固定"原答 / 卡点 / 怎么练 / 验收"四行；只有 3 题时自动改整宽
- 第 3 页 06：三栏写满，底部补"节奏"一行
- 第 3 页 07：标题改为"诊断反馈"，拆成"跟孩子复盘 / 家长配合 / 接下来"，家长那段落写成能照做的动作
- 字数上限：优势/短板 60→75，方向 60→50，三段复习 100→110；新增复盘 110、家长 100 的校验
- 只丢 0 分时 05 改为"满分题保持清单"，不再留一张空卡
- 分析稿（`analysis.md` / `analysis.html`）第五节同步改名"诊断反馈"

## 0.1.0 — 2026-11-07

第一版。把教学工作台里"视觉模型接口 + 编辑器逐题改"的试卷分析，改成由模型直接看卷出稿。

- `scripts/run.py` 一条入口：`new` / `pages` / `status` / `check` / `digest` / `approve` / `render` / `finish`
- `scripts/render_pages.py`：PDF / 图片 → 逐页 PNG，模型逐页看图（`--text` 只作辅助）
- `scripts/validate_draft.py`：结构校验 + 阻塞项 + 字数/题型/附件题号检查
- `scripts/build_digest.py`：`analysis.md` / `analysis.html` 分析稿，校核用
- `scripts/render_report.py`：五页品牌报告、单页、两页、A2 附录、B2 复做记录、验收记录
- `scripts/sync_engine.py`：从教学工作台同步渲染器（`--check` 只比对）
- `vendor/`：教学工作台 `standards.py`、`final_report.py`、`compact_report.py`、
  `poster_report.py`、`delivery_reports.py` 与品牌素材的逐字节副本
- `references/`：工作流程（核对 → 定位 → 整理 → 备课）、材料要求、字段口径、版式约束、质量门
- `templates/`：`draft.json`、`question.json` 骨架
- `examples/wangxiaoming-physics/`：虚构学生的完整示例（4 题，30 分，五页报告 5 页）
- 签核沿用工作台的口径：`reviewed` 只由老师置位，未签核的分数不计入得分率

### 与工作台的分工

- 工作台：校核界面、学生档案、归档、正式交付验收
- 本 skill：看卷、录题、写诊断、出稿、出报告
- `draft.json` 是两边共用的格式，工作台「打开草稿」可直接导入
