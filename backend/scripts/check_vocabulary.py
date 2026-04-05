from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCAN_ROOTS = [
    ROOT / "AGENTS.md",
    ROOT / "backend",
    ROOT / "contracts",
    ROOT / "docs",
    ROOT / "sql",
]

EXCLUDED_PATHS = {
    ROOT / "docs" / "glossary.md",
}

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".venv",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

TEXT_EXTENSIONS = {
    ".md",
    ".py",
    ".json",
    ".sql",
    ".yml",
    ".yaml",
    ".toml",
    ".txt",
}

BANNED_PATTERNS: list[tuple[str, str]] = [
    (r"\bworkflow_run_id\b", "use workflow_instance_id"),
    (r"\bworkflow_runs\b", "use workflow_instances"),
    (r"\bworkflow_run\b", "use workflow_instance"),
    (r"\breview_events\b", "use reviews"),
    (r"\breview_event\b", "use review"),
    (r"\bevidence_records\b", "use evidence_sources"),
    (r"\bevidence_record\b", "use evidence_source"),
    (r"\bassertion_support_links\b", "use evidence_links"),
    (r"\bassertion_support_link\b", "use evidence_link"),
    (r"\bbundle_id\b", "use template_id"),
    (r"\bbundle_version\b", "use template_version"),
    (r"\bstatement_text\b", "use text_norm"),
    (r"\bclaim_text\b", "use text_norm"),
    (r"\bsupport_refs\b", "use source_refs"),
    (r"\blicense_type\b", "use license_class"),
    (r'"oa_subset"\s*:', "use oa_subset_flag"),
    (r'"section"\s*:', "use section_key"),
    (r'^\s*section\s*:', "use section_key"),
    (r'"anchors"\s*:', "use assertion_ids"),
    (r'^\s*anchors\s*:', "use assertion_ids"),
    (r"\bevidence_id\b", "use evidence_source_id"),
]

COMPILED_PATTERNS = [(re.compile(pattern, re.MULTILINE), message) for pattern, message in BANNED_PATTERNS]


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        if root.is_file():
            files.append(root)
            continue
        for path in root.rglob("*"):
            if path.is_dir():
                continue
            if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
                continue
            if path in EXCLUDED_PATHS:
                continue
            if path.suffix not in TEXT_EXTENSIONS:
                continue
            files.append(path)
    return sorted(set(files))


def main() -> int:
    failures: list[str] = []

    for path in iter_files():
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for pattern, message in COMPILED_PATTERNS:
            for match in pattern.finditer(content):
                line_no = content.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(ROOT)}:{line_no}: {message}")

    if failures:
        print("Vocabulary drift detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Vocabulary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
