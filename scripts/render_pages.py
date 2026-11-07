"""Turn the materials into page images the model can actually look at.

A vision pass is only as good as what it sees: render every page of the paper,
the answer sheet and the answer key to PNG at a readable size, then read those
files with the host's image viewer. Never analyse a PDF from its text layer
alone — scores, ticks and handwriting live in the image.

    python scripts/render_pages.py work/<id>/source --out work/<id>/pages
    python scripts/render_pages.py paper.pdf --out pages --pages 1-4 --max-width 2200
    python scripts/render_pages.py work/<id>/source --out pages --text   # text layer too
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
PDF_SUFFIXES = {".pdf"}


def parse_pages(spec: str | None, total: int) -> list[int]:
    if not spec:
        return list(range(total))
    keep: list[int] = []
    for chunk in re.split(r"[,，]", spec):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            first, last = chunk.split("-", 1)
            keep.extend(range(int(first) - 1, int(last)))
        else:
            keep.append(int(chunk) - 1)
    return [index for index in keep if 0 <= index < total]


def unique_stem(path: Path, used: dict[str, int]) -> str:
    """Keep two files with the same stem apart in one flat output folder."""
    base = path.stem
    used[base] = used.get(base, 0) + 1
    return base if used[base] == 1 else f"{base}-{used[base]}"


def render(source: Path, out: Path, max_width: int, pages_spec: str | None, want_text: bool) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in source.iterdir() if p.is_file()) if source.is_dir() else [source]
    report: dict = {"pages": [], "text": [], "skipped": []}
    used: dict[str, int] = {}
    counter = 0

    for file in files:
        suffix = file.suffix.lower()
        if suffix in PDF_SUFFIXES:
            import fitz

            with fitz.open(file) as doc:
                wanted = parse_pages(pages_spec, len(doc))
                stem = unique_stem(file, used)
                text_chunks: list[str] = []
                for index in wanted:
                    page = doc[index]
                    zoom = min(3.0, max(1.0, max_width / max(1.0, page.rect.width)))
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                    counter += 1
                    target = out / f"p{counter:02d}-{stem}-{index + 1}.png"
                    pixmap.save(target)
                    report["pages"].append(
                        {
                            "file": target.name,
                            "source": file.name,
                            "page": index + 1,
                            "width": pixmap.width,
                            "height": pixmap.height,
                        }
                    )
                    text = page.get_text().strip() if want_text else ""
                    if text:
                        text_chunks.append(f"--- 第 {index + 1} 页 ---\n{text}")
                if text_chunks:
                    target = out / f"text-{stem}.txt"
                    target.write_text("\n\n".join(text_chunks) + "\n", encoding="utf-8")
                    report["text"].append({"file": target.name, "source": file.name, "pages": len(text_chunks)})
        elif suffix in IMAGE_SUFFIXES:
            from PIL import Image

            with Image.open(file) as image:
                image = image.convert("RGB")
                if image.width > max_width:
                    height = round(image.height * max_width / image.width)
                    image = image.resize((max_width, height), Image.LANCZOS)
                counter += 1
                target = out / f"p{counter:02d}-{file.stem}{'.jpg' if suffix == '.jpeg' else suffix}"
                image.save(target)
                report["pages"].append(
                    {"file": target.name, "source": file.name, "page": 1, "width": image.width, "height": image.height}
                )
        else:
            report["skipped"].append(file.name)

    (out / "pages.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="把试卷/答题卡渲染成逐页 PNG")
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-width", type=int, default=1800)
    parser.add_argument("--pages", default=None, help="1-4 或 1,3,5；默认全部")
    parser.add_argument("--text", action="store_true", help="同时导出 PDF 文字层（有的话）")
    args = parser.parse_args()

    source = args.source
    if not source.exists():
        print(f"找不到材料：{source}", file=sys.stderr)
        return 2
    out = args.out or (source.parent / "pages")
    report = render(source, out, args.max_width, args.pages, args.text)

    print(f"页面：{len(report['pages'])} 张 → {out}")
    for entry in report["pages"]:
        print(f"  {entry['file']}  {entry['width']}×{entry['height']}")
    if report["text"]:
        print("文字层：" + "、".join(entry["file"] for entry in report["text"]) + "（有文字层也别跳过看图）")
    if report["skipped"]:
        print("跳过：" + "、".join(report["skipped"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
