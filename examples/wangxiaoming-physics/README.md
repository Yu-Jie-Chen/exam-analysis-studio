# 示例：王小明 · 高三物理 · 第一次月考

**虚构数据。** "王小明"、"示例中学"、"示例教师"都是为了演示字段口径编的；
题目是常见的物理题型改写，不来自任何真实学员。

4 道题，满分 30 分，得 15 分：

| 题 | 题型 | 考点 | 得分 | 优先级 |
|---|---|---|---|---|
| 1 | 单选 | 匀变速直线运动 | 4/4 | 0 |
| 2 | 单选 | 受力分析与静摩擦临界 | 0/4 | 3 |
| 3 | 实验 | 伏安法测电阻与分压电路 | 6/10 | 2 |
| 4 | 解答 | 牛顿第二定律与多过程 | 5/12 | 1 |

## 目录里的东西

| 文件 | 说明 |
|---|---|
| `draft.json` | 完整草稿：可直接拖进教学工作台「打开草稿」 |
| `analysis.md` / `analysis.html` | 分析稿，老师校核时看这份 |
| `report.pdf` | 五页品牌报告（封面 + 诊断 + 规划 + 附件 A/B） |
| `preview/` | 每页 PNG（`.gitignore` 里，不在仓库中） |

## 复现

```bash
python scripts/run.py check  examples/wangxiaoming-physics
python scripts/run.py digest examples/wangxiaoming-physics
python scripts/run.py render examples/wangxiaoming-physics --preview
```

## 这个示例刻意示范了几件事

1. **`materialNotes` 先写范围**——"4 道题，满分 30 分"，而不是假装是整卷。
2. **`digest*` 三个短句不写句号**——报告会用「；」连接，写成句号会出现「。；」。
3. **`priority` 不等于失分多少**——第 2 题失 4 分排第 3 位（可迁移性最高），
   第 4 题失 7 分只排第 1 位之后的第 3 位（先修临界判断）。
4. **`cause` 写"卡在哪一步"**——"没有先判断是否达到最大静摩擦"，不是"粗心"。
5. **附件选失分题**——`appendixIds: "2,3"`，不是选满分题。
