# 字段口径

`draft.json` 是唯一真源。工作台能直接导入它，渲染器也只读它。
本文件是逐字段的字典——**写之前先查，别凭印象猜字段名**。

骨架：`templates/draft.json`（整份）与 `templates/question.json`（单题）。

## 顶层字段

| 字段 | 类型 | 谁填 | 口径 |
|---|---|---|---|
| `schemaVersion` | int | 固定 `2` | 工作台按这个版本迁移，别改 |
| `service` | `A`/`B` | 老师 | A = 高报附赠诊断，出整卷报告；B = 月考等，后面还有纸质复做 |
| `student` | str | 老师 | 报告封面上的姓名。**公开示例里换成占位名** |
| `studentId` | str | 工作台 | 工作台归档时回填，手写留空 |
| `school` | str | 老师 | 封面"学校" |
| `grade` | str | 老师 | 高中三年级 / 高三 / 高一 都行，封面原样显示 |
| `stage` | str | 默认 `高中` | 小学 / 初中 / 高中 |
| `subject` | str | 老师 | 物理 / 化学 / 数学 …，封面与页眉都用它 |
| `exam` | str | 老师 | "观山湖区第一高级中学高三年级 9 月综合练习"这种可识别的名称 |
| `examDate` | `YYYY-MM-DD` | 老师 | 考试日期 |
| `analysisDate` | `YYYY-MM-DD` | 模型/老师 | **报告日期**，封面和页脚都用它 |
| `teacher` | str | 老师 | 分析教师 |
| `institution` | str | 默认 `文源教育` | 机构名，页眉用 |
| `reviewer` | str | 老师 | 复核人；`approve --reviewer` 会写这里 |
| `reviewDate` | `YYYY-MM-DD` | 老师 | 复核日期 |
| `deliveryDate` | `YYYY-MM-DD` | 老师 | 交付日期 |
| `materialNotes` | str | 模型 | 用了哪几页、缺了什么、哪些题未覆盖、答案来源。空着会被 `check` 提示 |
| `summary` | str | 模型 | 整卷判断，2–4 句。**第一句先写分析范围** |
| `difficultyPoints` | str[≤3] | 模型 | 难度依据，每条一句，须点明题号 |
| `difficultySources` | str[≤3] | 模型 | 与上一条一一对应的题号，如 `["2","3"]`；`check` 会验证题号存在 |
| `difficultyConclusion` | str | 模型 | 优先补强方向，一句话 |
| `strengthText` | str ≤60 | 模型 | 优势，带题号与证据。第 2 页绿色框 |
| `weaknessText` | str ≤60 | 模型 | 短板，带题号与证据。第 2 页红色框 |
| `directionText` | str ≤60 | 模型 | 学习方向。第 2 页米色框 |
| `plan` | str | 模型 | 完整阶段安排（长文，可跨段），第 3 页兜底与工作台用 |
| `planFirst` | str ≤100 | 模型 | 第 3 页「优先处理」 |
| `planNext` | str ≤100 | 模型 | 第 3 页「随后巩固」 |
| `planLater` | str ≤100 | 模型 | 第 3 页「后续专题与检查习惯」 |
| `teacherCommunication` | str | 模型/老师 | 老师怎么跟学生谈：问什么、讲什么、约什么 |
| `parentSupport` | str | 模型/老师 | 家长能执行的具体动作，不写"多加督促"这种空话 |
| `followup` | str | 老师 | 沟通后的记录，**不进报告**，只存档 |
| `appendixIds` | str | 模型 | 附件题号，逗号分隔，≤5 题；留空自动取失分最重的两题 |
| `typeComments` | `{题型: 说明}` | 模型 | 第 2 页每条题型条下的点评；键必须与 `questions[].type` 完全一致 |
| `questions` | obj[] | 模型 | 逐题记录，见下 |
| `variants` | obj[] | 老师 | B 类复做的变式记录，A 类留空 |
| `retakeScope` | obj/null | 老师 | 锁定题组，由 `standards.lock_scope()` 生成，不要手写 |

## questions[] 字段

| 字段 | 类型 | 口径 |
|---|---|---|
| `id` | str | 题号，`"1"` `"12"` `"4(2)"` 都行；不能重复。整题与小问不能同时出现 |
| `type` | str | 题型，**全卷最多 6 类**（第 2 页只放得下 6 条）。单选 / 多选 / 实验 / 解答 / 填空 / 计算 / 作图… |
| `topic` | str | 主要考点，一个，不超过 12 字（第 3 页标题行用） |
| `max` | number | 满分，>0 |
| `score` | number/null | 得分；**看不清或缺依据就 `null`**，不许猜 0 |
| `difficulty` | `基础`/`中档`/`提升` | 只能是这三个值，否则 `validate` 报错 |
| `ability` | 五选一 | `概念理解` `模型建构` `实验探究` `运算推理` `规范表达` |
| `sourcePage` | str | `试卷第 2 页第 3 题 / 答题卡第 2 页`；附录页会打印这一行 |
| `difficultyReason` | str | 为什么是这个难度，一句 |
| `abilityTask` | str | 这道题要求学生做成的能力动作 |
| `conditions` | str | 解题必需的关键条件（数据、状态、边界） |
| `challenge` | str | 本题难点 / 最容易错的一步 |
| `studentAnswer` | str | **照抄**学生的选项、式子、图像描述；空白就写"未作答" |
| `referenceAnswer` | str | 参考结果。自拟的必须写进 `scoringSource` |
| `solution` | str | 关键解法：用哪条规律、怎么列、怎么得结果 |
| `scoringPoints` | str | 分项评分点；没有细则就写"按卷面批改，分项待核" |
| `scoringSource` | str | 学校细则 / 自拟参考解待复核 / 教师按卷面批改 |
| `mastery` | str | 掌握 / 部分掌握 / 未掌握 / 待核实 |
| `errorType` | str | 概念 / 条件 / 模型 / 运算 / 实验 / 表达 / 流程 / 无 |
| `evidence` | str | 原答与页码证据（与 `studentAnswer` 互补，可重复） |
| `cause` | str | 会到哪一步、卡在哪、证据是什么。**不许只写"粗心"** |
| `action` | str | 针对性训练任务，可执行、可验收 |
| `acceptance` | str | 独立完成与复测通过的条件 |
| `questionText` | str | 题干摘录或原卷位置；不改写已知条件 |
| `priority` | int | 0–3，本轮优先级。第 3 页按它排序 |
| `reviewed` | bool | **只有老师签核后才 `true`**；模型一律写 `false` |
| `digestEvidence` | str | 第 3 页短摘要·证据。**不写句号**，页面会用「；」连接三句 |
| `digestMastery` | str | 第 3 页短摘要·掌握判断。不写句号 |
| `digestAction` | str | 第 3 页短摘要·下一步。不写句号 |
| `practiceQuestion` | str | 只有真实存在的配套练习才填，否则留空 |
| `practiceAnswer` | str | 同上 |

`reviewed` 与 `score` 的组合决定报告怎么算：

| `reviewed` | `score` | 报告里的样子 |
|---|---|---|
| `true` | 数字 | 计入得分与得分率 |
| `true` | `null` | 显示"待核"，计入分母、不计入分子 |
| `false` | 任何值 | **整题按待核处理**，不进得分率 |

## 短摘要的写法

第 3 页每题只有一行，格式是三句用「；」连起来：

```text
digestEvidence：只写了 30-20=10 N，没有最大静摩擦的比较
digestMastery：会用分量，缺临界判断
digestAction：先算最大静摩擦，再定方向
```

渲染结果：`只写了 30-20=10 N，没有最大静摩擦的比较；会用分量，缺临界判断；先算最大静摩擦，再定方向。`

所以：**三句都不写句号**，否则会出现「。；」。

## 派生字段（不用写）

这些由渲染器算，写进 JSON 也会被覆盖或忽略：
`stats`、`group`、`difficulty()`、`abilities()`、`retakeMetrics`、`radarCurrent`、
`pairedScores`、`retakeRows`。

## 最小可用示例

```json
{
  "schemaVersion": 2,
  "service": "A",
  "student": "王小明",
  "grade": "高三",
  "subject": "物理",
  "exam": "高三第一次月考 · 物理",
  "analysisDate": "2026-10-25",
  "teacher": "陈老师",
  "reviewer": "陈老师",
  "reviewDate": "2026-10-25",
  "deliveryDate": "2026-10-26",
  "materialNotes": "4 道题，满分 30 分；原始答题卡字迹可读。",
  "summary": "……",
  "strengthText": "第 1 题公式选用准确，列式与单位完整。",
  "weaknessText": "第 2 题未判断静摩擦临界；第 3 题改接后未重定量程。",
  "directionText": "先修临界判断，再补电学实验，最后两道新题复测。",
  "difficultyPoints": ["第 2 题需比较最大静摩擦，属条件筛选。", "第 3 题需判断分压接法与量程。"],
  "difficultySources": ["2", "3"],
  "plan": "……",
  "planFirst": "……", "planNext": "……", "planLater": "……",
  "teacherCommunication": "……", "parentSupport": "……",
  "appendixIds": "2,3",
  "typeComments": {"单选": "基础题稳，临界题需要固定判断顺序。"},
  "questions": []
}
```

完整示例见 [`examples/wangxiaoming-physics/draft.json`](../examples/wangxiaoming-physics/draft.json)。
