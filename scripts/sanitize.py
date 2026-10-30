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

# Path-scoped exemptions (2026-10-30, per Joe): HHH report pages are
# intentionally published holdings data, so the "HIVE cost basis" pattern is
# not applied under these directories. Every other pattern still applies
# there, and this pattern stays fully active everywhere else.
EXEMPT_LABEL_DIRS = {
    "HIVE cost basis": [("shadowmonkey", "hhh-daily"), ("shadowmonkey", "hhh-weekly")],
}

def _exempt(path: Path, label: str) -> bool:
    parts = path.resolve().parts
    for seq in EXEMPT_LABEL_DIRS.get(label, []):
        n = len(seq)
        if any(parts[i:i+n] == seq for i in range(len(parts) - n + 1)):
            return True
    return False
SELF_PATH = Path(__file__).resolve()

def check_file(path: Path) -> list:
    if path.resolve() == SELF_PATH:
        # This file's own FORBIDDEN list contains the pattern strings
        # themselves (e.g. "HIVE.*cost.*basis" as a regex literally
        # matches itself as plain text) -- always a false positive,
        # never an actual leak. Found 2026-08-18 on the first real run.
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    return [f"{path}: [{label}]" for pat, label in FORBIDDEN
            if re.search(pat, text, re.IGNORECASE) and not _exempt(path, label)]

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
