"""Render a draft with the brand engine — the same code the workbench uses.

    # 五页品牌报告（默认）
    python scripts/render_report.py work/<id>/draft.json
    # 其它交付物
    python scripts/render_report.py work/<id>/draft.json --format poster --docx
    python scripts/render_report.py work/<id>/draft.json --format compact --docx
    python scripts/render_report.py work/<id>/draft.json --format detail
    # 顺手出每页 PNG，用来核对版式
    python scripts/render_report.py work/<id>/draft.json --preview work/<id>/preview

需要 reportlab；五页品牌报告另需 PyMuPDF（合成封面与页脚）。用 `run.py render`
会自动挑一个装好依赖的解释器。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import load  # noqa: E402

FORMATS = ("final", "poster", "compact", "detail", "paper", "acceptance")


def _suffix(fmt: str, docx: bool, svg: bool) -> str:
    if docx:
        return "docx"
    if svg:
        return "svg"
    return "pdf"


def render(data: dict, fmt: str, kind: str, docx: bool, svg: bool) -> bytes:
    standards = load("standards")
    view = standards.report_view(data, kind) if fmt in ("poster", "compact") else data
    if fmt == "final":
        return load("final_report").export_final_pdf(data, kind)
    if fmt == "poster":
        module = load("poster_report")
        if svg:
            return module.export_svg(view)
        return module.export_docx(view) if docx else module.export_pdf(view)
    if fmt == "compact":
        module = load("compact_report")
        return module.export_docx(view) if docx else module.export_pdf(view)
    module = load("delivery_reports")
    return {"detail": module.detail_pdf, "paper": module.paper_pdf, "acceptance": module.acceptance_pdf}[fmt](data)


def preview(pdf: bytes, out: Path, scale: float = 1.4) -> list[str]:
    import fitz

    out.mkdir(parents=True, exist_ok=True)
    names = []
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        for index, page in enumerate(doc):
            target = out / f"report-p{index + 1:02d}.png"
            page.get_pixmap(matrix=fitz.Matrix(scale, scale)).save(target)
            names.append(target.name)
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染试卷分析报告")
    parser.add_argument("draft", type=Path)
    parser.add_argument("--format", default="final", choices=FORMATS)
    parser.add_argument("--kind", default="first", choices=("first", "retake"))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--docx", action="store_true", help="poster/compact 输出 Word")
    parser.add_argument("--svg", action="store_true", help="poster 输出 SVG")
    parser.add_argument("--preview", type=Path, default=None, help="同时把每页导成 PNG")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    standards = load("standards")
    if args.svg and args.format != "poster":
        print("--svg 只用于 --format poster")
        return 2
    text = args.draft.read_text(encoding="utf-8-sig")
    try:
        data = standards.validate(json.loads(text))
    except ValueError as error:
        print("结构不合格：" + str(error))
        return 2
    except json.JSONDecodeError as error:
        print(f"JSON 解析失败（第 {error.lineno} 行）：{error.msg}")
        return 2

    suffix = _suffix(args.format, args.docx, args.svg)
    out = args.out or (args.draft.parent / (f"report-{args.format}.{suffix}" if args.format != "final" else f"report.{suffix}"))
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = render(data, args.format, args.kind, args.docx, args.svg)
    except ValueError as error:
        message = str(error)
        print("渲染中止：" + message)
        if "超出" in message or "「" in message:
            print("这类报错通常意味着某段文字放不进固定模板——先精简文案，不要把版式改小。")
        return 3
    out.write_bytes(payload)

    pages = None
    if suffix == "pdf":
        import fitz

        with fitz.open(stream=payload, filetype="pdf") as doc:
            pages = len(doc)
    shots = preview(payload, args.preview) if args.preview and suffix == "pdf" else []

    unreviewed = [q["id"] for q in data["questions"] if not q.get("reviewed")]
    if unreviewed:
        print(f"注意：{len(unreviewed)} 道题未校核，报告里这些分数按“待核”处理，不计入得分率。")

    if args.json:
        print(json.dumps({"out": str(out), "bytes": len(payload), "pages": pages, "preview": shots}, ensure_ascii=False))
    else:
        size = f"{len(payload) / 1024 / 1024:.2f} MB"
        print(f"{args.format} → {out}  ({size}{f', {pages} 页' if pages else ''})")
        for name in shots:
            print("  " + str(args.preview / name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
