# 更新记录

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
