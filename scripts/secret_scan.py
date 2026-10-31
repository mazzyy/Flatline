#!/usr/bin/env python3
"""Fail CI if a committed file looks like it contains a secret.

This is a small regex gate, not a replacement for rotating leaked keys.
It ignores .env.example placeholders and this file's own patterns.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
}

# Patterns that mean "this is probably a real credential".
PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9]{16,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    # PayPal live (not sandbox) secret-looking values.
    re.compile(r"PAYPAL_CLIENT_SECRET\s*=\s*['\"][A-Za-z0-9_-]{20,}['\"]"),
    re.compile(r"AZURE_API_KEY\s*=\s*['\"][A-Za-z0-9+/=_-]{20,}['\"]"),
]

TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".yml",
    ".yaml",
    ".md",
    ".env",
    ".toml",
    ".txt",
    ".sh",
    ".html",
    ".css",
}


def iter_files() -> list[Path]:
    out: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name == ".env.example":
            continue
        if path.suffix and path.suffix not in TEXT_SUFFIXES and path.name not in {
            "Dockerfile",
            "Makefile",
            "LICENSE",
        }:
            continue
        out.append(path)
    return out


def main() -> int:
    hits: list[str] = []
    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern in PATTERNS:
            if pattern.search(text):
                rel = path.relative_to(ROOT)
                hits.append(f"{rel}: matched {pattern.pattern}")
    if hits:
        print("secret_scan: possible secrets committed:")
        for hit in hits:
            print(f"  {hit}")
        return 1
    print("secret_scan: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
