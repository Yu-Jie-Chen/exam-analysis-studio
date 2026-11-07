"""Find a Python interpreter that can actually render the report.

The report engine needs `reportlab` (+ `python-docx` for Word output, and
PyMuPDF/`fitz` for the five-page brand PDF, which merges the cover and adds the
page footer). Not every interpreter on a machine has them — the bundled DSH
runtime, for instance, ships reportlab but not PyMuPDF — so `run.py` re-execs
the renderer with the first interpreter that passes an import probe.

Order: `--python` / `$EXAM_STUDIO_PYTHON` → this interpreter → `python` on PATH
→ the runtimes this project is normally built on.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

BUNDLED = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "python.exe"
COMMON = [
    BUNDLED,
    Path("D:/python/python3.11.5/python.exe"),
    Path("C:/Python312/python.exe"),
    Path("C:/Python311/python.exe"),
]

# What each output format really imports.
NEEDS = {
    "final": ("reportlab", "fitz"),
    "poster": ("reportlab", "docx"),
    "compact": ("reportlab", "docx"),
    "detail": ("reportlab",),
    "paper": ("reportlab",),
    "acceptance": ("reportlab",),
    "pages": ("fitz",),
}


def _works(exe: str, needed: tuple[str, ...]) -> bool:
    code = "import " + ",".join(needed)
    try:
        done = subprocess.run(
            [exe, "-c", code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def candidates(explicit: str | None = None) -> list[str]:
    seen: list[str] = []

    def add(value: str | None) -> None:
        if not value:
            return
        path = value if os.path.isabs(value) or os.sep in value else (shutil.which(value) or value)
        if path and path not in seen and Path(path).is_file():
            seen.append(path)

    add(explicit)
    add(os.environ.get("EXAM_STUDIO_PYTHON"))
    add(sys.executable)
    add(shutil.which("python"))
    add(shutil.which("python3"))
    for path in COMMON:
        add(str(path))
    return seen


def find(needed: tuple[str, ...], explicit: str | None = None) -> str:
    tried = []
    for exe in candidates(explicit):
        if _works(exe, needed):
            return exe
        tried.append(exe)
    raise SystemExit(
        "找不到能渲染报告的 Python。需要的模块："
        + "、".join(needed)
        + "\n已尝试：\n  "
        + "\n  ".join(tried)
        + "\n请安装依赖：python -m pip install -r requirements.txt"
        + "\n或指定解释器：--python D:\\python\\python3.11.5\\python.exe"
    )


def run(exe: str, args: list[str], cwd: Path | None = None) -> int:
    return subprocess.call([exe, *args], cwd=str(cwd) if cwd else None)
