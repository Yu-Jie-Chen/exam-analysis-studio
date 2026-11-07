# 质量门

交付标准来自《文源教育 交付与验收标准 V1.0》，实现在 `vendor/standards.py` 的
`audit()`。`python scripts/run.py check <work>` 跑的就是这套规则。

十条检查项，名称与 `companyChecks` 的键一一对应：

| 键 | 检查 | 不通过的样子 |
|---|---|---|
| `identity` | 身份、试卷与材料来源对应 | 姓名/考试对不上，材料是另一份卷子 |
| `scores` | 分值、得失分与待核范围一致 | 得分加起来不等于总分，或待核项被算成 0 |
| `overview` | 报告模块齐全且结论有证据 | 有结论没证据，或缺模块 |
| `detail` | 详细题号覆盖完整（A 类） | 漏题、整题与小问重复计分 |
| `teaching` | 教学范围与覆盖证据（B 类） | "已教"没有教学证据 |
| `paper` | 纸质独立复做及变式记录（B 类） | 复做没签字、变式没作答 |
| `comparison` | 复做五模块与比较口径（B 类） | 前后分数不是同一范围 |
| `plan` | 训练任务、责任与日期明确 | "加强练习"这种没有任务与验收的话 |
| `layout` | 无重叠、截断、错名或乱码 | 文字压到框外、姓名错、方块字 |
| `archive` | 署名、复核与归档齐全 | 缺 `teacher` / `reviewer` / 日期 |

## 谁做什么

| 事项 | 模型 | 老师 |
|---|---|---|
| 看卷、录题、写诊断、出文案 | ✅ | 复核 |
| `score` 待核项标 `null` | ✅ | 决定是否阶段性交付 |
| `reviewed` 置 `true`（签核） | ❌ **绝不做** | ✅ `run.py approve` |
| `companyChecks` 十项人工验收 | ❌ | ✅ 工作台里点 |
| `teachingClass` / `teachingEvidence` | ❌ | ✅ |
| `followup`（沟通记录） | ❌ | ✅ |

模型能做的门（结构、字数、覆盖、证据）自己先过一遍再交；涉及"人签过字"的门，
一律留给老师，**不要为了让 `check` 变绿去写 `companyChecks`**。

## 交付前自查

```bash
python scripts/run.py check <work>          # 结构 + 文案
python scripts/run.py digest <work>         # 生成分析稿，自己先读一遍
python scripts/run.py render <work> --preview
```

逐条过：

- [ ] `materialNotes` 写清了范围与缺口吗？`summary` 第一句是否与之一致？
- [ ] 每个计分单元都有 `sourcePage`、`studentAnswer`、`referenceAnswer`、`solution`？
- [ ] 每个失分单元都有 `cause`、`action`、`acceptance`？
- [ ] `cause` 是不是"卡在哪一步"，而不是"粗心 / 基础差"？
- [ ] 待核分数都是 `null` 吗？有没有把看不见的分数写成 0？
- [ ] `difficultyPoints` 有 ≥2 条，且每条都点了题号？`difficultySources` 题号都存在？
- [ ] 题型 ≤6 类？三类短摘要 ≤60 字？三段复习 ≤100 字？
- [ ] 附件 2 题选对了吗？每题有原答与关键解法吗？`practiceQuestion` 是真实练习吗？
- [ ] `reviewed` 是老师点的吗？`review.md` 有记录吗？
- [ ] 预览 PNG 看过吗？封面、页脚、附件页都没有截断吗？

## 常见退回原因

1. **把待核写成零分。** 报告立刻变成"全卷丢 40 分"，家长会当场质疑。
2. **整题与小问并存。** 分数翻倍，`validate` 会拦，但手动改 JSON 容易绕过去。
3. **错因写现象。** "粗心看错题"不是原因；"把 30 N 当成合力，没先算最大静摩擦"才是。
4. **三段复习没有验收。** "多做题""加强电学"无法验收，改成"两道改接题，量程与接法都写依据"。
5. **附件题选成满分题。** 附件是给讨论用的，应选失分或有代表性的题。
6. **题型碎成七八类。** 报告只放 6 条，超了直接渲染失败。
7. **报告日期写成今天。** `analysisDate` 是报告上的日期，通常等于复核日；交付日另填 `deliveryDate`。

## 与工作台的关系

工作台导入 `draft.json` 后会再跑一次 `standards.validate()`；它的「正式交付」按钮还会
要求 `companyChecks` 全部通过。本 skill 不替代这一步——它替代的只是"看卷"。
所以：**skill 出稿 → 老师签核 → 工作台归档 / 正式导出**，两边不冲突。
