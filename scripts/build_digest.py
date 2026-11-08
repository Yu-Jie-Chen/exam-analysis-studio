"""Write the analysis as something a teacher can read and correct.

`analysis.md` and `analysis.html` are the working copy — every number, quote and
diagnosis in one place, with the 待核 items marked. The five-page PDF is the
delivery; this is the proof-reading surface. Build it *before* rendering, so a
wrong 原始作答 or a missing 错因 is caught while it is still cheap to fix.

    python scripts/build_digest.py work/<id>/draft.json
    python scripts/build_digest.py work/<id>/draft.json --out-dir work/<id>
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import load  # noqa: E402

CSS = """
:root{--ink:#222;--navy:#173a5a;--orange:#f65b1b;--line:#e3e8ee;--muted:#6b7a88;--green:#22ac72;--red:#f34e40}
*{box-sizing:border-box}
body{margin:0;background:#f2f4f7;color:var(--ink);font:14px/1.75 "Microsoft YaHei","PingFang SC","Noto Sans CJK SC",sans-serif}
main{max-width:860px;margin:0 auto;background:#fff;padding:40px 46px 56px}
header{border-bottom:2px solid var(--orange);padding-bottom:16px;margin-bottom:22px}
h1{font-size:24px;margin:0 0 6px;color:var(--navy)}
.sub{color:var(--muted);font-size:13px}
.scorebar{display:flex;gap:26px;flex-wrap:wrap;margin:18px 0 4px;padding:14px 18px;background:#f7f9fb;border:1px solid var(--line);border-radius:8px}
.scorebar div{min-width:96px}
.scorebar b{display:block;font-size:22px;color:var(--orange);font-weight:700}
.scorebar span{font-size:12px;color:var(--muted)}
h2{font-size:17px;margin:34px 0 12px;padding-left:10px;border-left:4px solid var(--orange);color:var(--navy)}
h3{font-size:15px;margin:20px 0 8px}
table{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0 4px}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{background:#f7f9fb;font-weight:600;color:var(--navy)}
tr.total td{background:#fffaf6;font-weight:600}
.q{border:1px solid var(--line);border-radius:8px;padding:16px 18px;margin:14px 0}
.q-head{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px}
.q-no{background:var(--navy);color:#fff;font-weight:700;border-radius:4px;padding:1px 9px;font-size:13px}
.q-topic{font-weight:700;color:var(--navy)}
.badge{font-size:11px;padding:1px 8px;border-radius:10px;border:1px solid var(--line);color:var(--muted);background:#fafbfc}
.badge.ok{color:var(--green);border-color:#bfe6d6;background:#f1fbf6}
.badge.warn{color:var(--red);border-color:#f6cdc9;background:#fef4f3}
.grid{display:grid;grid-template-columns:96px 1fr;gap:4px 12px;font-size:13px}
.grid dt{color:var(--muted)}
.grid dd{margin:0}
.note{background:#fff8f0;border:1px solid #f6dcc4;border-radius:6px;padding:10px 14px;font-size:13px;color:#7a4a20}
.todo{border:1px solid #f6cdc9;background:#fef6f5;border-radius:8px;padding:12px 16px}
.todo li{margin:3px 0}
footer{margin-top:40px;border-top:1px solid var(--line);padding-top:12px;color:var(--muted);font-size:12px}
@media print{body{background:#fff}main{max-width:none;padding:0}@page{size:A4;margin:16mm}.q,table{break-inside:avoid}}
"""


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def text(value) -> str:
    return esc(value).replace("\n", "<br>")


def badge(label: str, tone: str = "") -> str:
    return f'<span class="badge {tone}">{esc(label)}</span>'


def question_block(question: dict) -> str:
    reviewed = question.get("reviewed") is True
    score = question.get("score")
    head = [
        f'<span class="q-no">第 {esc(question["id"])} 题</span>',
        f'<span class="q-topic">{esc(question.get("topic") or "考点待补")}</span>',
        badge(question.get("type") or "题型待补"),
        badge(f'难度 {question.get("difficulty") or "—"}'),
        badge(f'{_num(question.get("max"))} 分'),
        badge("已校核" if reviewed and score is not None else "待校核", "ok" if reviewed and score is not None else "warn"),
    ]
    if question.get("priority"):
        head.append(badge(f'优先级 {question["priority"]}'))
    rows = [
        ("原卷位置", question.get("sourcePage")),
        ("原始作答", question.get("studentAnswer") or question.get("evidence")),
        ("参考结果", question.get("referenceAnswer")),
        ("关键条件", question.get("conditions")),
        ("难点", question.get("challenge")),
        ("关键解法", question.get("solution")),
        ("评分点", question.get("scoringPoints")),
        ("评分来源", question.get("scoringSource")),
        ("掌握状态", question.get("mastery")),
        ("错误分类", question.get("errorType")),
        ("原因", question.get("cause")),
        ("训练任务", question.get("action")),
        ("验收", question.get("acceptance")),
        ("能力维度", question.get("ability")),
        ("难度依据", question.get("difficultyReason")),
    ]
    body = "".join(
        f"<dt>{esc(label)}</dt><dd>{text(value) if value else '<i>待补</i>'}</dd>" for label, value in rows if value is not None or label in ("原始作答", "参考结果", "关键解法", "原因", "训练任务")
    )
    got = _num(score) if score is not None else "—"
    return (
        f'<section class="q"><div class="q-head">{"".join(head)}</div>'
        f'<div class="sub" style="margin:-4px 0 10px">得分 {got} / {_num(question.get("max"))}</div>'
        f'<dl class="grid">{body}</dl></section>'
    )


def _num(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def build(data: dict) -> tuple[str, str]:
    standards = load("standards")
    full, score, known = standards.stats(data)
    rate = score / known * 100 if known else 0
    questions = data["questions"]
    groups = standards.group(data, "type")
    pending = [q for q in questions if not q.get("reviewed") or q.get("score") is None]

    head = (
        f'{esc(data.get("student") or "未命名学生")} · {esc(data.get("grade") or data.get("stage") or "")} · '
        f'{esc(data.get("subject") or "物理")} · {esc(data.get("exam") or "未命名考试")}'
    )
    cover = [
        ("学校", data.get("school")),
        ("考试日期", data.get("examDate")),
        ("分析日期", data.get("analysisDate")),
        ("分析", data.get("teacher")),
        ("复核", data.get("reviewer")),
        ("交付日期", data.get("deliveryDate")),
    ]
    cover_html = " · ".join(f"{esc(k)}：{esc(v)}" for k, v in cover if v)

    type_rows = "".join(
        f'<tr><td>{esc(key)}</td><td>{_num(value[0])}</td><td>{_num(value[1])}</td>'
        f'<td>{_num(value[2])}</td><td>{(value[1] / value[2] * 100 if value[2] else 0):.1f}%</td></tr>'
        for key, value in groups.items()
    ) + (
        f'<tr class="total"><td>合计</td><td>{_num(full)}</td><td>{_num(score)}</td><td>{_num(known)}</td>'
        f'<td>{rate:.1f}%</td></tr>'
    )

    todo_items = []
    unreviewed = [q["id"] for q in questions if not q.get("reviewed")]
    if unreviewed:
        todo_items.append("未校核：" + "、".join(f"第 {qid} 题" for qid in unreviewed))
    nulls = [q["id"] for q in questions if q.get("score") is None]
    if nulls:
        todo_items.append("分数待核：" + "、".join(f"第 {qid} 题" for qid in nulls))
    missing = [f'第 {q["id"]} 题「{label}」' for q in questions for label, key in
               (("原因", "cause"), ("训练", "action"), ("验收", "acceptance")) if not str(q.get(key) or "").strip()]
    if missing:
        todo_items.append("缺字段：" + "、".join(missing[:10]) + ("…" if len(missing) > 10 else ""))
    todo_html = "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in todo_items) + "</ul>" if todo_items else "<p>逐题记录完整。</p>"

    plan = [("优先处理", data.get("planFirst")), ("随后巩固", data.get("planNext")), ("后续专题", data.get("planLater"))]
    plan_html = "".join(
        f'<tr><th style="width:110px">{esc(label)}</th><td>{text(value) if value else "<i>待补</i>"}</td></tr>' for label, value in plan
    )

    appendix = str(data.get("appendixIds") or "").strip()
    appendix_note = f"附件题号：{esc(appendix)}" if appendix else "附件题号：留空，报告自动取失分最重的两题"

    html_doc = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>分析稿 · {esc(data.get("student") or "")} {esc(data.get("exam") or "")}</title>
<style>{CSS}</style></head><body><main>
<header><h1>{head}</h1><div class="sub">{cover_html}</div>
<div class="scorebar">
<div><b>{_num(score)}<span style="font-size:13px"> 分</span></b><span>得分</span></div>
<div><b>{_num(full)}</b><span>满分</span></div>
<div><b>{_num(known)}</b><span>已核分数</span></div>
<div><b>{rate:.1f}%</b><span>得分率（按已核）</span></div>
<div><b>{len(questions)}</b><span>计分单元</span></div>
</div></header>

<section><h2>一、材料与范围</h2>
<p>{text(data.get("materialNotes")) if data.get("materialNotes") else "<i>待填：用了哪几页、缺了什么、哪些题未覆盖</i>"}</p>
<p>{text(data.get("summary")) if data.get("summary") else "<i>待填：整体判断</i>"}</p></section>

<section><h2>二、得分结构</h2>
<table><thead><tr><th>题型</th><th>满分</th><th>得分</th><th>已核</th><th>得分率</th></tr></thead>
<tbody>{type_rows}</tbody></table></section>

<section><h2>三、逐题记录</h2>
{"".join(question_block(question) for question in questions)}</section>

<section><h2>四、复习安排</h2>
<table><tbody>{plan_html}</tbody></table>
<p>{text(data.get("plan")) if data.get("plan") else "<i>待填：分阶段任务与复测</i>"}</p></section>

<section><h2>五、诊断反馈</h2>
<p><b>问题出在哪儿：</b>{text(data.get("problemText")) if data.get("problemText") else "<i>待补</i>"}</p>
<p><b>接下来怎么做：</b>{text(data.get("nextStepText")) if data.get("nextStepText") else "<i>待补</i>"}</p></section>

<section><h2>六、待校核</h2>
<div class="todo">{todo_html}</div>
<p class="sub" style="margin-top:10px">{appendix_note}</p></section>

<footer>分析稿 · 由 exam-analysis-studio 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M")} · 交付版式见 report.pdf</footer>
</main></body></html>"""

    lines = [f"# {head}", ""]
    if cover_html:
        lines += [cover_html, ""]
    lines += [
        f"- 满分 {_num(full)}，已核 {_num(known)}，得分 {_num(score)}，得分率 {rate:.1f}%",
        f"- 题目 {len(questions)} 个计分单元；题型 {len(groups)} 类",
        "",
        "## 材料与范围",
        data.get("materialNotes") or "_待填_",
        "",
        data.get("summary") or "_待填_",
        "",
        "## 得分结构",
        "",
        "| 题型 | 满分 | 得分 | 已核 | 得分率 |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {key} | {_num(v[0])} | {_num(v[1])} | {_num(v[2])} | {(v[1] / v[2] * 100 if v[2] else 0):.1f}% |"
        for key, v in groups.items()
    ]
    lines += ["", "## 逐题记录", ""]
    for question in questions:
        state = "已校核" if question.get("reviewed") and question.get("score") is not None else "待校核"
        lines += [
            f"### 第 {question['id']} 题 · {question.get('topic') or '考点待补'}（{question.get('type') or '—'}，{_num(question.get('score'))}/{_num(question.get('max'))} 分，{state}）",
            "",
        ]
        for label, key in (("原答", "studentAnswer"), ("参考", "referenceAnswer"), ("解法", "solution"),
                           ("错因", "cause"), ("训练", "action"), ("验收", "acceptance")):
            value = str(question.get(key) or "").strip()
            if value:
                lines.append(f"- **{label}**：{value}")
        lines.append("")
    lines += ["## 复习安排", ""]
    for label, value in plan:
        lines.append(f"- **{label}**：{value or '待补'}")
    lines += ["", f"- **完整计划**：{data.get('plan') or '待补'}", ""]
    lines += ["## 诊断反馈", "",
              f"- **问题出在哪儿**：{data.get('problemText') or '待补'}",
              f"- **接下来怎么做**：{data.get('nextStepText') or '待补'}", ""]
    lines += ["## 待校核", ""] + ([f"- {item}" for item in todo_items] or ["- 无"]) + ["", appendix_note, ""]
    return html_doc, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成分析稿 analysis.html / analysis.md")
    parser.add_argument("draft", type=Path)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()
    standards = load("standards")
    try:
        data = standards.validate(json.loads(args.draft.read_text(encoding="utf-8-sig")))
    except ValueError as error:
        print("结构不合格：" + str(error))
        return 2
    except json.JSONDecodeError as error:
        print(f"JSON 解析失败（第 {error.lineno} 行）：{error.msg}")
        return 2
    out_dir = args.out_dir or args.draft.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    html_doc, markdown = build(data)
    (out_dir / "analysis.html").write_text(html_doc, encoding="utf-8")
    (out_dir / "analysis.md").write_text(markdown, encoding="utf-8")
    pending = sum(1 for q in data["questions"] if not q.get("reviewed") or q.get("score") is None)
    print(f"分析稿：{out_dir / 'analysis.html'}、{out_dir / 'analysis.md'}（待校核 {pending} 题）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
