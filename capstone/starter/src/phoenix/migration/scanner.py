"""Scan source code for patterns that typically break after an HMS -> UC migration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PATTERNS: dict[str, re.Pattern[str]] = {
    "MOUNT_PATH": re.compile(r"['\"`](?:dbfs:)?/mnt/"),
    "DBFS_PATH": re.compile(r"['\"`]dbfs:/(?!mnt/)"),
    "INPUT_FILE_NAME": re.compile(r"\binput_file_name\s*\("),
    "SPARK_CONTEXT_OR_RDD": re.compile(r"\bsparkContext\b|\bsc\.\w+\(|\.rdd\b"),
    "STORAGE_KEY_IN_CONF": re.compile(r"fs\.azure\.account\.key|fs\.s3a\.(access|secret)\.key"),
    # FROM/JOIN/TABLE followed by exactly schema.table (not catalog.schema.table, not a Python "from a.b import")
    "TWO_LEVEL_NAME": re.compile(
        r"\b(?:FROM|JOIN|TABLE|VIEW|INTO|UPDATE|saveAsTable\(|table\()\s*['\"`]?([A-Za-z_]\w*)\.([A-Za-z_]\w*)\b(?!\.)(?!\s+import\b)",
        re.IGNORECASE,
    ),
}


@dataclass(frozen=True)
class Finding:
    file: str
    line_no: int
    rule: str
    line: str


def scan_text(text: str, file: str = "<text>") -> list[Finding]:
    findings: list[Finding] = []
    for i, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append(Finding(file, i, rule, line.strip()))
    return findings


def scan_path(root: str | Path, suffixes: tuple[str, ...] = (".py", ".sql", ".scala")) -> list[Finding]:
    root = Path(root)
    findings: list[Finding] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in suffixes:
            findings.extend(scan_text(path.read_text(encoding="utf-8", errors="replace"), str(path)))
    return findings


if __name__ == "__main__":  # python -m phoenix.migration.scanner legacy_code/
    import sys

    results = scan_path(sys.argv[1] if len(sys.argv) > 1 else ".")
    for f in results:
        print(f"{f.file}:{f.line_no}: [{f.rule}] {f.line}")
    print(f"\n{len(results)} finding(s)")
    sys.exit(1 if results else 0)
