"""Check a draft against the delivery standard before anyone renders it.

Mirrors what the workbench does on import (`standards.validate`) and then lists
what is still missing in the words a teacher uses: 待核分数、未校核题目、超长文案、
题型超过六类、附件题号不存在。

    python scripts/validate_draft.py work/<id>/draft.json
    python scripts/validate_draft.py work/<id>/draft.json --json

Exit codes: 0 可以渲染，1 有阻塞项，2 结构不合格。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import load  # noqa: E402

SHORT_LIMITS = {
    "strengthText": ("优势", 75),
    "weaknessText": ("薄弱", 75),
    "directionText": ("学习方向", 50),
    "planFirst": ("优先处理", 110),
    "planNext": ("随后巩固", 110),
    "planLater": ("后续专题", 110),
    "teacherCommunication": ("诊断反馈·复盘", 110),
    "parentSupport": ("诊断反馈·家长", 100),
}
COVER_FIELDS = {
    "student": "学生姓名",
    "exam": "考试名称",
    "grade": "年级",
    "subject": "学科",
    "analysisDate": "分析日期",
    "teacher": "分析教师",
    "reviewer": "复核人",
    "reviewDate": "复核日期",
    "deliveryDate": "交付日期",
}
# 学科老师要确认的，不是模型能"补"出来的。
MANUAL_CHECKS = {
    "identity", "scores", "overview", "detail", "teaching",
    "paper", "comparison", "plan", "layout", "archive",
}


def load_json(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise SystemExit(f"JSON 解析失败（第 {error.lineno} 行第 {error.colno} 列）：{error.msg}") from error


def check(draft: dict) -> dict:
    standards = load("standards")
    result = {"blocking": [], "notes": [], "normalized": None, "stats": {}, "types": {}}
    try:
        data = standards.validate(draft)
    except ValueError as error:
        result["fatal"] = str(error)
        return result
    result["normalized"] = data

    full, score, known = standards.stats(data)
    questions = data["questions"]
    pending_score = [q["id"] for q in questions if q.get("score") is None]
    unreviewed = [q["id"] for q in questions if not q.get("reviewed")]
    result["stats"] = {
        "questions": len(questions),
        "full": full,
        "known": known,
        "score": score,
        "rate": round(score / known * 100, 1) if known else 0,
        "pendingScore": pending_score,
        "unreviewed": unreviewed,
    }

    groups = standards.group(data, "type")
    result["types"] = {key: {"total": v[0], "score": v[1], "known": v[2]} for key, v in groups.items()}

    if not questions:
        result["blocking"].append("还没有逐题记录：questions 为空")
    if len(groups) > 6:
        result["blocking"].append(f"题型有 {len(groups)} 类，最终模板最多展示 6 类，请合并同类题型名称")
    if unreviewed:
        result["blocking"].append(
            f"{len(unreviewed)} 道题未校核（第 {'、'.join(unreviewed[:8])}{'…' if len(unreviewed) > 8 else ''} 题）："
            "报告只统计已校核的分数，校核后再渲染"
        )
    if pending_score:
        result["blocking"].append(
            f"{len(pending_score)} 道题分数待核（第 {'、'.join(pending_score[:8])} 题）："
            "缺评分依据时留空是对的，但正式交付前要补上或登记待核范围"
        )

    for field, label in COVER_FIELDS.items():
        if not str(data.get(field) or "").strip():
            result["blocking"].append(f"缺{label}（{field}）")

    for field, (label, limit) in SHORT_LIMITS.items():
        value = str(data.get(field) or "").strip()
        if not value:
            result["notes"].append(f"{label}（{field}）为空，报告会用自动生成的兜底句")
        elif len(value) > limit:
            result["blocking"].append(f"{label}（{field}）{len(value)} 字，超过 {limit} 字会撑破模板")

    appendix = str(data.get("appendixIds") or "").strip()
    if appendix:
        ids = [part.strip() for part in appendix.replace("，", ",").split(",") if part.strip()]
        known_ids = {q["id"] for q in questions}
        missing = [qid for qid in ids if qid not in known_ids]
        if len(ids) > 5:
            result["blocking"].append("附件题号最多 5 题")
        if missing:
            result["blocking"].append("附件题号不存在：" + "、".join(missing))
        if len(set(ids)) != len(ids):
            result["blocking"].append("附件题号重复")

    for question in questions:
        qid = question["id"]
        for key in ("type", "topic", "sourcePage", "studentAnswer", "referenceAnswer", "solution",
                    "scoringPoints", "scoringSource", "conditions", "challenge", "acceptance",
                    "difficultyReason", "abilityTask"):
            if not str(question.get(key) or "").strip():
                result["blocking"].append(f"第 {qid} 题缺「{_label(key)}」")
        lost = question.get("score") is None or question.get("score", 0) < question.get("max", 0)
        if lost:
            for key in ("cause", "action", "errorType"):
                if not str(question.get(key) or "").strip():
                    result["blocking"].append(f"第 {qid} 题失分但缺「{_label(key)}」")

    audit = standards.audit(data, "first")
    manual = [item for item in audit["errors"] if item.startswith("人工验收未通过") or item.startswith("补充")]
    # 逐题缺项上面已经逐条列过，这里只补整体性的要求。
    rest = [item for item in audit["errors"] if item not in manual and not item.startswith("第")]
    result["audit"] = {"status": audit["status"], "errors": rest, "manual": manual, "warnings": audit["warnings"]}
    result["blocking"].extend(rest)
    result["blocking"] = list(dict.fromkeys(result["blocking"]))
    if manual:
        result["notes"].append(
            "交付验收里还有 " + str(len(manual)) + " 项人工确认（署名、复核、公司验收），在工作台里完成"
        )
    return result


def _label(key: str) -> str:
    standards = load("standards")
    return standards.DETAIL_FIELDS.get(key, key)


def report(result: dict) -> int:
    if result.get("fatal"):
        print("结构不合格：" + result["fatal"])
        return 2
    stats = result["stats"]
    print(f"题目 {stats['questions']} 道 · 满分 {stats['full']:g} · 已核 {stats['known']:g} 分 · 得 {stats['score']:g} 分（{stats['rate']}%）")
    if result["types"]:
        print("题型：" + "、".join(f"{key} {value['score']:g}/{value['total']:g}" for key, value in result["types"].items()))
    if result["blocking"]:
        print(f"\n阻塞项 {len(result['blocking'])} 条：")
        for item in result["blocking"]:
            print("  × " + item)
    else:
        print("\n结构检查通过。")
    for item in result["notes"]:
        print("  · " + item)
    warnings = (result.get("audit") or {}).get("warnings") or []
    for item in warnings[:6]:
        print("  · " + item)
    return 1 if result["blocking"] else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 draft.json")
    parser.add_argument("draft", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check(load_json(args.draft))
    if args.json:
        result.pop("normalized", None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get("fatal") else (1 if result["blocking"] else 0)
    return report(result)


if __name__ == "__main__":
    raise SystemExit(main())
