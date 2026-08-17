#!/usr/bin/env python3
"""sanitize.py — Leak guard. Run before any git commit or GitHub push."""
from __future__ import annotations
import re, sys
from pathlib import Path

FORBIDDEN = [
    (r"joselitovsering@gmail\.com", "personal email"),
    (r"\bJoselito\b",               "personal name"),
    (r"HIVE.*cost.*basis",          "HIVE cost basis"),
    (r"personal_context",           "personal context ref"),
    (r"openrouter\.key",            "OpenRouter key path"),
    (r"MONKEY\s+MATTERS.*LLC.*tax", "LLC tax detail"),
    (r"ghp_[A-Za-z0-9]{36}",       "GitHub PAT"),
    (r"sk-ant-[A-Za-z0-9\-_]{40,}","Anthropic API key"),
    (r"Bearer\s+[A-Za-z0-9\-_\.]{30,}", "Bearer token"),
]

TEXT_EXTS = {".html",".htm",".json",".md",".py",".js",".ts",
             ".tsx",".css",".yml",".yaml",".txt",".j2",".jinja2"}
SKIP_DIRS = {".git",".venv","venv","__pycache__","node_modules"}

def check_file(path: Path) -> list:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    return [f"{path}: [{label}]" for pat, label in FORBIDDEN
            if re.search(pat, text, re.IGNORECASE)]

def check_tree(root: Path) -> list:
    violations = []
    for fp in root.rglob("*"):
        if any(p in SKIP_DIRS for p in fp.parts):
            continue
        if fp.is_file() and fp.suffix.lower() in TEXT_EXTS:
            violations.extend(check_file(fp))
    return violations

def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    v = check_tree(root)
    if v:
        print("SANITIZE FAILED:", file=sys.stderr)
        for line in v:
            print(f"  ✗ {line}", file=sys.stderr)
        sys.exit(1)
    print(f"sanitize OK — {root} clean")

if __name__ == "__main__":
    main()
