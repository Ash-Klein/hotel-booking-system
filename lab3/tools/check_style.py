"""Project-local Python style checker.

External linters could not be installed in this offline environment, so this
script implements the subset of PEP 8 / Pylint rules that the project actually
enforces: 100-column lines, no tabs or trailing whitespace, module and class
docstrings, top-level function docstrings, no bare ``except``, and no ``TODO``
markers in delivered source. It also prints the non-blank source line count,
which is used as the size evidence for the experiment report.

Usage:
    python tools/check_style.py
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [ROOT / "hotel_booking", ROOT / "tests", ROOT / "run.py"]
MAX_LINE = 100


def iter_files() -> list[Path]:
    """Return all Python files to inspect."""
    files: list[Path] = []
    for target in TARGETS:
        if target.is_file():
            files.append(target)
        else:
            files.extend(target.rglob("*.py"))
    return sorted(set(files))


def check_file(path: Path) -> list[str]:
    """Return style messages for one file."""
    messages: list[str] = []
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        messages.append("文件末尾缺少换行")
    lines = text.splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > MAX_LINE:
            messages.append(f"L{number}: 行长度 {len(line)} > {MAX_LINE}")
        if line.rstrip() != line:
            messages.append(f"L{number}: 行尾空白")
        if "\t" in line:
            messages.append(f"L{number}: 包含制表符")
        if "TODO" in line or "FIXME" in line:
            messages.append(f"L{number}: 交付代码包含 TODO/FIXME")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        messages.append(f"语法错误：{exc}")
        return messages
    if not ast.get_docstring(tree):
        messages.append("缺少模块文档字符串")
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and not ast.get_docstring(node):
            messages.append(f"L{node.lineno}: 类 {node.name} 缺少文档字符串")
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            messages.append(f"L{node.lineno}: 禁止裸 except")
    for node in tree.body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ) and not ast.get_docstring(node):
            messages.append(f"L{node.lineno}: 顶层函数 {node.name} 缺少文档字符串")
    return messages


def logical_lines(path: Path) -> int:
    """Count non-empty, non-comment source lines."""
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def main() -> int:
    """Run every check and print a compact summary."""
    files = iter_files()
    total_errors = 0
    total_lines = 0
    per_file: list[tuple[int, Path]] = []
    for path in files:
        messages = check_file(path)
        if messages:
            print(f"\n[{path.relative_to(ROOT)}]")
            for message in messages:
                print(f"  - {message}")
            total_errors += len(messages)
        lines = logical_lines(path)
        total_lines += lines
        per_file.append((lines, path))
    print("\n" + "=" * 64)
    print(f"检查文件：{len(files)} 个")
    print(f"有效源代码行：{total_lines}")
    print("规模最大的 8 个文件：")
    for lines, path in sorted(per_file, reverse=True)[:8]:
        print(f"  {lines:5d}  {path.relative_to(ROOT)}")
    if total_errors:
        print(f"风格问题：{total_errors} 个")
        return 1
    print("风格检查通过：0 个问题（行宽 ≤100、无行尾空白、无制表符、文档完整）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
