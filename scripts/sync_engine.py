"""Re-copy the renderer from the teaching workbench.

The report layout lives in one place: the workbench. This skill keeps a verbatim
copy so it can run on its own, which means the copy can go stale. Run this after
any change to the workbench's report code or brand assets.

    python scripts/sync_engine.py --workbench "F:\\文源教育\\...\\教学端工作台"
    python scripts/sync_engine.py --workbench <dir> --check   # 只比对，不写入

`--check` 会列出哪些文件与工作台不一致、哪些多了少了。
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE.parent / "vendor"

MODULES = ["standards.py", "final_report.py", "compact_report.py", "poster_report.py", "delivery_reports.py"]
ASSETS = ["WenyuanSans-Regular.ttf", "WenyuanSans-Bold.ttf", "DejaVuSerif.ttf", "orange_cover.pdf", "OFL.txt", "template-source.json"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def pairs(workbench: Path) -> list[tuple[Path, Path]]:
    pairs_ = [(workbench / name, VENDOR / name) for name in MODULES]
    pairs_ += [(workbench / "assets" / name, VENDOR / "assets" / name) for name in ASSETS]
    return pairs_


def compare(workbench: Path) -> list[str]:
    lines = []
    for source, target in pairs(workbench):
        if not source.is_file():
            lines.append(f"缺源文件：{source}")
            continue
        if not target.is_file():
            lines.append(f"未同步：{target.name}")
            continue
        if digest(source) != digest(target):
            lines.append(f"已变更：{target.name}（工作台 {digest(source)} / 本地 {digest(target)}）")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="从教学工作台同步渲染器")
    parser.add_argument("--workbench", type=Path, required=True)
    parser.add_argument("--check", action="store_true", help="只比对，不写入")
    args = parser.parse_args()

    workbench = args.workbench.expanduser().resolve()
    if not (workbench / "final_report.py").is_file():
        print(f"{workbench} 不像教学工作台目录（没有 final_report.py）")
        return 2

    if args.check:
        lines = compare(workbench)
        print("\n".join(lines) if lines else "已与工作台一致。")
        return 1 if lines else 0

    (VENDOR / "assets").mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for source, target in pairs(workbench):
        if not source.is_file():
            print(f"跳过（工作台没有）：{source.name}")
            continue
        shutil.copy2(source, target)
        written.append(target)

    # 记下来源，方便以后回答"这份渲染器是哪一版"。
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# 渲染器来源\n", f"- 同步时间：{stamp}", f"- 来源目录：`{workbench}`", "", "| 文件 | sha256 前 16 位 |", "| --- | --- |"]
    for target in written:
        lines.append(f"| {target.relative_to(VENDOR).as_posix()} | `{digest(target)}` |")
    lines += [
        "",
        "`vendor/` 是教学工作台渲染器的**逐字节副本**，不要在这里改版式。",
        "改工作台 → `python scripts/sync_engine.py --workbench <dir>` → 重新出预览。",
        "",
        "字体按 SIL Open Font License 1.1 分发，见 `assets/OFL.txt`。",
    ]
    (VENDOR / "PROVENANCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已同步 {len(written)} 个文件 → {VENDOR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
