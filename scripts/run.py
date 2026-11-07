"""One entry point for a whole 试卷分析 run.

    python scripts/run.py new 试卷.pdf 答题卡.pdf 答案.pdf \
        --student 王小明 --grade 高三 --subject 物理 --exam "高三第一次月考" \
        --teacher 陈老师 --date 2026-10-25

    python scripts/run.py pages   work/20261025-物理-王小明   # 逐页 PNG，供看图
    python scripts/run.py status  work/20261025-物理-王小明
    python scripts/run.py check   work/20261025-物理-王小明   # 结构 + 阻塞项
    python scripts/run.py digest  work/20261025-物理-王小明   # 分析稿，先给人看
    python scripts/run.py approve work/20261025-物理-王小明 --all --reviewer 陈老师
    python scripts/run.py render  work/20261025-物理-王小明 [--format final|poster|...]
    python scripts/run.py finish  work/20261025-物理-王小明   # check + digest + render

`finish` 一口气跑完检查、分析稿和渲染：顺利时最后一行是 NEXT；卡住时停在 STOP，
并说明还差什么。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import pyenv  # noqa: E402
from engine import load  # noqa: E402

FORMATS = ("final", "poster", "compact", "detail", "paper", "acceptance")


# ---------------------------------------------------------------- helpers

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workdir_of(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    if path.is_file() and path.name == "draft.json":
        return path.parent
    if not path.is_dir():
        raise SystemExit(f"找不到工作目录：{path}")
    return path


def draft_of(work: Path) -> Path:
    path = work / "draft.json"
    if not path.is_file():
        raise SystemExit(f"{work} 里没有 draft.json；先运行 run.py new")
    return path


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------- commands

def cmd_new(args) -> int:
    work_root = Path(args.out or (Path.cwd() / "work")).expanduser().resolve()
    slug = args.id or f"{args.date.replace('-', '')}-{args.subject or 'physics'}-{(args.student or 'student')}"
    work = work_root / slug
    source = work / "source"
    for folder in (source, work / "pages"):
        folder.mkdir(parents=True, exist_ok=True)

    materials = []
    for item in args.materials:
        path = Path(item).expanduser().resolve()
        if not path.exists():
            print(f"跳过（不存在）：{item}")
            continue
        if path.is_dir():
            files = [p for p in sorted(path.iterdir()) if p.is_file()]
        else:
            files = [path]
        for file in files:
            target = source / file.name
            if target.exists() and target.resolve() != file:
                target = source / f"{file.stem}-{hashlib.sha1(str(file).encode()).hexdigest()[:6]}{file.suffix}"
            if not target.exists():
                shutil.copy2(file, target)
            materials.append({"name": target.name, "bytes": target.stat().st_size, "sha256": sha256(target)})

    draft_path = work / "draft.json"
    manifest_path = work / "manifest.json"
    manifest = read_json(manifest_path) if manifest_path.is_file() else {"id": slug, "createdAt": datetime.now().isoformat(timespec="seconds"), "materials": []}
    known = {entry["name"] for entry in manifest["materials"]}
    manifest["materials"] += [entry for entry in materials if entry["name"] not in known]
    manifest.update(
        {
            "student": args.student or manifest.get("student", ""),
            "grade": args.grade or manifest.get("grade", ""),
            "subject": args.subject or manifest.get("subject", ""),
            "exam": args.exam or manifest.get("exam", ""),
        }
    )
    manifest["updatedAt"] = datetime.now().isoformat(timespec="seconds")
    write_json(manifest_path, manifest)

    if not draft_path.is_file():
        template = read_json(ROOT / "templates" / "draft.json")
        template.update(
            {
                "student": args.student,
                "grade": args.grade,
                "subject": args.subject or "物理",
                "school": args.school,
                "exam": args.exam,
                "teacher": args.teacher,
                "analysisDate": args.date,
                "reviewer": args.teacher,
                "reviewDate": args.date,
                "service": args.service,
            }
        )
        template["questions"] = []
        template["retakeScope"] = None
        write_json(draft_path, template)
        print(f"新建：{draft_path}")
    else:
        print(f"沿用已有草稿：{draft_path}")

    print(f"工作目录：{work}")
    if materials:
        print(f"材料 {len(materials)} 个 → {source}")
    print("下一步：run.py pages " + str(work))
    return 0


def cmd_pages(args) -> int:
    work = workdir_of(args.work)
    source = work / "source"
    if not source.is_dir() or not any(source.iterdir()):
        print(f"{source} 是空的：先把试卷、答题卡放进去")
        return 1
    exe = pyenv.find(pyenv.NEEDS["pages"], args.python)
    command = [str(HERE / "render_pages.py"), str(source), "--out", str(work / "pages"), "--max-width", str(args.max_width)]
    if args.only:
        command += ["--pages", args.only]
    if args.text:
        command.append("--text")
    return pyenv.run(exe, command)


def cmd_status(args) -> int:
    work = workdir_of(args.work)
    draft_path = work / "draft.json"
    print(f"工作目录：{work}")
    sources = sorted((work / "source").glob("*")) if (work / "source").is_dir() else []
    print(f"材料：{len(sources)} 个" + ("  " + "、".join(p.name for p in sources[:6]) if sources else ""))
    pages = sorted((work / "pages").glob("p*.png")) if (work / "pages").is_dir() else []
    print(f"页面：{len(pages)} 张")
    if not draft_path.is_file():
        print("草稿：尚未创建")
        print("下一步：run.py new <材料…> --student …")
        return 1
    data = read_json(draft_path)
    questions = data.get("questions") or []
    reviewed = [q for q in questions if q.get("reviewed")]
    pending = [q for q in questions if q.get("reviewed") and q.get("score") is None]
    print(f"题目：{len(questions)} 道，已校核 {len(reviewed)} 道，分数待核 {len(pending)} 道")
    for name in ("analysis.html", "report.pdf", "report-poster.pdf", "report-compact.pdf", "report-detail.pdf"):
        path = work / name
        if path.is_file():
            print(f"  {name}  {path.stat().st_size / 1024:.0f} KB  {datetime.fromtimestamp(path.stat().st_mtime):%Y-%m-%d %H:%M}")
    if not questions:
        print("下一步：看图逐题录入 draft.json")
    elif len(reviewed) < len(questions):
        print("下一步：run.py digest 给人看，然后 run.py approve")
    else:
        print("下一步：run.py render")
    return 0


def cmd_check(args) -> int:
    work = workdir_of(args.work)
    sys.path.insert(0, str(HERE))
    import validate_draft

    result = validate_draft.check(validate_draft.load_json(draft_of(work)))
    if args.json:
        result.pop("normalized", None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        validate_draft.report(result)
    return 2 if result.get("fatal") else (1 if result["blocking"] else 0)


def cmd_digest(args) -> int:
    work = workdir_of(args.work)
    return pyenv.run(sys.executable, [str(HERE / "build_digest.py"), str(draft_of(work)), "--out-dir", str(work)])


def cmd_approve(args) -> int:
    work = workdir_of(args.work)
    path = draft_of(work)
    data = read_json(path)
    questions = data.get("questions") or []
    if not questions:
        print("还没有题目可以校核")
        return 1
    ids = [q["id"] for q in questions]
    if args.all:
        chosen = ids
    elif args.ids:
        chosen = [part.strip() for part in args.ids.replace("，", ",").split(",") if part.strip()]
        unknown = [qid for qid in chosen if qid not in ids]
        if unknown:
            print("没有这些题号：" + "、".join(unknown))
            return 1
    else:
        print("用 --all 或 --ids 1,2,3 指定校核范围")
        return 1
    stamp = args.date or datetime.now().strftime("%Y-%m-%d")
    for question in questions:
        if question["id"] in chosen:
            question["reviewed"] = True
    if args.reviewer:
        data["reviewer"] = args.reviewer
    data["reviewDate"] = stamp
    write_json(path, data)

    review = work / "review.md"
    line = f"- {stamp} 校核通过：第 {'、'.join(chosen)} 题（{args.reviewer or '未署名'}）\n"
    review.write_text((review.read_text(encoding="utf-8") if review.is_file() else "# 校核记录\n\n") + line, encoding="utf-8")

    remaining = [q["id"] for q in questions if not q.get("reviewed")]
    print(f"已校核 {len(chosen)} 道题" + (f"，还剩 {'、'.join(remaining)} 题" if remaining else "，全部题目已校核"))
    return 0


def cmd_render(args) -> int:
    work = workdir_of(args.work)
    needed = pyenv.NEEDS.get(args.format, ("reportlab",))
    exe = pyenv.find(needed, args.python)
    command = [str(HERE / "render_report.py"), str(draft_of(work)), "--format", args.format, "--kind", args.kind]
    out = Path(args.out).expanduser().resolve() if args.out else _default_out(work, args.format, args.docx, args.svg)
    command += ["--out", str(out)]
    if args.docx:
        command.append("--docx")
    if args.svg:
        command.append("--svg")
    if args.preview:
        command += ["--preview", str(work / "preview")]
    return pyenv.run(exe, command)


def _default_out(work: Path, fmt: str, docx: bool, svg: bool) -> Path:
    suffix = "docx" if docx else "svg" if svg else "pdf"
    return work / (f"report.{suffix}" if fmt == "final" else f"report-{fmt}.{suffix}")


def cmd_finish(args) -> int:
    work = workdir_of(args.work)
    code = cmd_check(argparse.Namespace(work=str(work), json=False))
    if code == 2:
        return 2
    if code == 0:
        cmd_digest(argparse.Namespace(work=str(work)))
        render_code = cmd_render(
            argparse.Namespace(
                work=str(work), format=args.format, kind="first", out=None,
                docx=args.docx, svg=False, preview=True, python=args.python,
            )
        )
        if render_code:
            print("STOP：渲染失败，先看上面的报错")
            return render_code
        print(f"NEXT：把 {_default_out(work, args.format, args.docx, False)} 发出去；需要归档就去工作台「打开草稿」导入 draft.json")
        return 0
    print("STOP：还有阻塞项，修完再跑 finish")
    return 1


# ---------------------------------------------------------------- CLI

def main() -> int:
    parser = argparse.ArgumentParser(prog="run.py", description="试卷分析一站式入口")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="新建工作目录并归档材料")
    new.add_argument("materials", nargs="*", help="试卷、答题卡、答案、评分细则（PDF 或图片）")
    new.add_argument("--out", default=None, help="work 根目录，默认 ./work")
    new.add_argument("--id", default=None)
    new.add_argument("--student", default="")
    new.add_argument("--grade", default="")
    new.add_argument("--subject", default="物理")
    new.add_argument("--school", default="")
    new.add_argument("--exam", default="")
    new.add_argument("--teacher", default="")
    new.add_argument("--service", default="A", choices=("A", "B"))
    new.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    new.set_defaults(func=cmd_new)

    pages = sub.add_parser("pages", help="渲染逐页 PNG")
    pages.add_argument("work")
    pages.add_argument("--max-width", type=int, default=1800)
    pages.add_argument("--only", default=None, help="1-4 或 1,3,5")
    pages.add_argument("--text", action="store_true")
    pages.add_argument("--python", default=None)
    pages.set_defaults(func=cmd_pages)

    status = sub.add_parser("status", help="进度与下一步")
    status.add_argument("work")
    status.set_defaults(func=cmd_status)

    check = sub.add_parser("check", help="结构校验与阻塞项")
    check.add_argument("work")
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=cmd_check)

    digest = sub.add_parser("digest", help="生成分析稿 analysis.html / analysis.md")
    digest.add_argument("work")
    digest.set_defaults(func=cmd_digest)

    approve = sub.add_parser("approve", help="教师校核签核")
    approve.add_argument("work")
    approve.add_argument("--all", action="store_true")
    approve.add_argument("--ids", default=None)
    approve.add_argument("--reviewer", default="")
    approve.add_argument("--date", default=None)
    approve.set_defaults(func=cmd_approve)

    render = sub.add_parser("render", help="渲染交付文件")
    render.add_argument("work")
    render.add_argument("--format", default="final", choices=FORMATS)
    render.add_argument("--kind", default="first", choices=("first", "retake"))
    render.add_argument("--out", default=None)
    render.add_argument("--docx", action="store_true")
    render.add_argument("--svg", action="store_true")
    render.add_argument("--preview", action="store_true")
    render.add_argument("--python", default=None)
    render.set_defaults(func=cmd_render)

    finish = sub.add_parser("finish", help="check + digest + render")
    finish.add_argument("work")
    finish.add_argument("--format", default="final", choices=FORMATS)
    finish.add_argument("--docx", action="store_true")
    finish.add_argument("--python", default=None)
    finish.set_defaults(func=cmd_finish)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
