"""Compare independently collected nf-core test-run results, without claiming scientific validity.

Usage: python -m workflows.rnaseq.compare path/to/run-1 path/to/run-2
Output is JSON on stdout. Exit: 0 identical, 1 differences, 2 unverifiable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .phase0 import MANIFEST_NAME, verify

IDENTITY_FIELDS = ("pipeline", "pipeline_revision", "profile", "test_data_source")
RESULT_PREFIX = "results/"


def _result_files(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        entry["path"]: {"sha256": entry["sha256"], "size_bytes": entry["size_bytes"]}
        for entry in manifest["artifacts"]
        if entry["path"].startswith(RESULT_PREFIX)
    }


def compare_runs(left: Path, right: Path) -> tuple[int, dict[str, Any]]:
    """Only compare byte identity of tracked result artifacts; do not infer biology."""
    left, right = left.resolve(), right.resolve()
    report: dict[str, Any] = {
        "schema_version": "dros.rnaseq-comparison.v1",
        "run_directories": {"left": str(left), "right": str(right)},
        "verdict": "not_comparable",
        "output_byte_equality": None,
        "limitations": [
            "Manifest SHA256 hashes validate local bytes, not who created them",
            "Official test-profile data identity is not independently attested",
            "Resolved workflow commits and image digests are not yet verified",
            "Byte equality is not a claim of scientific correctness or reproducibility",
        ],
        "scientific_validation": "not_assessed",
    }
    if left == right:
        report["blocking_reasons"] = ["comparison requires two distinct run directories"]
        return 2, report

    invalid = {
        "left": verify(left),
        "right": verify(right),
    }
    if any(invalid.values()):
        report["verdict"] = "invalid_evidence"
        report["integrity_errors"] = invalid
        return 2, report

    first = json.loads((left / MANIFEST_NAME).read_text(encoding="utf-8"))
    second = json.loads((right / MANIFEST_NAME).read_text(encoding="utf-8"))
    left_id, right_id = first.get("run_id"), second.get("run_id")
    if not (isinstance(left_id, str) and left_id and isinstance(right_id, str) and right_id):
        report["blocking_reasons"] = ["run_id is missing; cannot establish separate runs"]
        return 2, report
    if left_id == right_id:
        report["blocking_reasons"] = ["same run_id; cannot treat it as independent replay"]
        return 2, report

    report["run_ids"] = {"left": left_id, "right": right_id}
    report["execution_statuses"] = {
        "left": first["status"],
        "right": second["status"],
    }
    if first["status"] != "succeeded" or second["status"] != "succeeded":
        report["blocking_reasons"] = ["both runs must have execution status succeeded"]
        return 2, report

    mismatches = {
        field: {"left": first.get(field), "right": second.get(field)}
        for field in IDENTITY_FIELDS
        if first.get(field) != second.get(field)
    }
    if mismatches:
        report["verdict"] = "configuration_mismatch"
        report["configuration_differences"] = mismatches
        return 2, report

    old_files = _result_files(first)
    new_files = _result_files(second)
    if not old_files or not new_files:
        report["blocking_reasons"] = ["both runs must have recorded output files under results/"]
        return 2, report

    left_only = sorted(set(old_files) - set(new_files))
    right_only = sorted(set(new_files) - set(old_files))
    changed = [
        {
            "path": path,
            "left": old_files[path],
            "right": new_files[path],
        }
        for path in sorted(set(old_files) & set(new_files))
        if old_files[path] != new_files[path]
    ]

    equal = not left_only and not right_only and not changed
    report.update({
        "verdict": "identical_outputs" if equal else "different_outputs",
        "output_byte_equality": equal,
        "counts": {
            "left": len(old_files),
            "right": len(new_files),
            "changed": len(changed),
            "left_only": len(left_only),
            "right_only": len(right_only),
        },
        "left_only": left_only,
        "right_only": right_only,
        "changed": changed,
    })
    return (0 if equal else 1), report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()
    status, report = compare_runs(args.left, args.right)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
