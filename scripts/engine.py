"""Load the vendored report engine.

`vendor/` holds a byte-for-byte copy of the workbench renderers
(standards.py, final_report.py, compact_report.py, poster_report.py,
delivery_reports.py) plus the brand assets they read from `vendor/assets/`.

The modules use flat imports (`from standards import ...`), so the only thing
this module does is put `vendor/` on `sys.path`.

    from engine import load
    final_report = load('final_report')
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

VENDOR = Path(__file__).resolve().parent.parent / "vendor"

_MISSING = """
找不到内置渲染器：{path}

skills 目录可能被不完整地复制了。请重新克隆仓库，或运行
    python scripts/sync_engine.py --workbench <教学工作台目录>
从工作台重新同步渲染器与品牌素材。
"""


def _ensure_path() -> None:
    if not (VENDOR / "final_report.py").is_file():
        raise SystemExit(_MISSING.format(path=VENDOR).strip())
    if str(VENDOR) not in sys.path:
        sys.path.insert(0, str(VENDOR))


def load(name: str):
    """Import one engine module (`standards`, `final_report`, ...)."""
    _ensure_path()
    try:
        return importlib.import_module(name)
    except ImportError as error:
        hint = ""
        if "fitz" in str(error):
            hint = "\n缺少 PyMuPDF（import fitz）。python -m pip install -r requirements.txt"
        elif "reportlab" in str(error) or "docx" in str(error):
            hint = "\n缺少 reportlab / python-docx。python -m pip install -r requirements.txt"
        raise SystemExit(f"渲染器 {name} 加载失败：{error}{hint}") from error
