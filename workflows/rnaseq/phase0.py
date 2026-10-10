"""Opt-in nf-core/rnaseq smoke execution and independent file-integrity verification.

Not a DR-OS runner backend: it must not register assertions or claim scientific validity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PIPELINE = "nf-core/rnaseq"
REVISION = "3.27.0"
SCHEMA_VERSION = "dros.nfcore-smoke.v1"
MANIFEST_NAME = "evidence-manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collect_artifacts(root: Path) -> list[dict[str, object]]:
    """Record regular files only; refuse symlinks, including symlinked directories."""
    artifacts: list[dict[str, object]] = []
    for directory in (root / "execution", root / "results"):
        if directory.is_symlink():
            raise ValueError(f"symlink in evidence tree: {directory}")
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"symlink in evidence tree: {path}")
            if path.is_file():
                artifacts.append({
                    "path": path.relative_to(root).as_posix(),
                    "sha256": checksum(path),
                    "size_bytes": path.stat().st_size,
                })
    return artifacts


def save_manifest(root: Path, manifest: dict[str, object]) -> None:
    target = root / MANIFEST_NAME
    temporary = root / f".{MANIFEST_NAME}.tmp"
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


def verify(root: Path) -> list[str]:
    """Verify local file integrity; never interpret this as scientific validation."""
    errors: list[str] = []
    try:
        manifest = json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"cannot read manifest: {exc}"]
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        return ["unknown manifest schema"]
    if manifest.get("pipeline") != PIPELINE or manifest.get("pipeline_revision") != REVISION:
        errors.append("unexpected pipeline identity")
    if manifest.get("status") not in {"succeeded", "failed", "blocked"}:
        errors.append("invalid execution status")
    if manifest.get("status") == "succeeded" and manifest.get("exit_code") != 0:
        errors.append("succeeded requires exit_code=0")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return errors + ["artifacts must be a list"]
    seen: set[str] = set()
    expected: set[str] = set()
    for entry in artifacts:
        if not isinstance(entry, dict):
            errors.append("invalid artifact entry")
            continue
        rel = entry.get("path")
        if not isinstance(rel, str) or not rel or "\\" in rel:
            errors.append("invalid artifact path")
            continue
        parts = Path(rel).parts
        if len(parts) < 2 or parts[0] not in {"execution", "results"} or any(p in {"..", "."} for p in parts):
            errors.append(f"unsafe artifact path: {rel}")
            continue
        if rel in seen:
            errors.append(f"duplicate artifact: {rel}")
            continue
        seen.add(rel)
        expected.add(rel)
        path = root / rel
        if path.is_symlink() or not path.is_file():
            errors.append(f"missing or symlink artifact: {rel}")
            continue
        if not isinstance(entry.get("size_bytes"), int) or path.stat().st_size != entry["size_bytes"]:
            errors.append(f"size mismatch: {rel}")
        if not isinstance(entry.get("sha256"), str) or checksum(path) != entry["sha256"]:
            errors.append(f"sha256 mismatch: {rel}")
    try:
        actual = {item["path"] for item in collect_artifacts(root)}
        if actual != expected:
            errors.append(f"artifact inventory mismatch: missing={sorted(actual - expected)}, stale={sorted(expected - actual)}")
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def run(root: Path) -> int:
    if root.exists():
        print("run directory already exists; use a new directory for independent runs", file=sys.stderr)
        return 2
    root.mkdir(parents=True)
    (root / "execution").mkdir()
    (root / "results").mkdir()
    started_at = utc_now()
    command = [
        "nextflow", "run", PIPELINE, "-r", REVISION, "-profile", "test,docker",
        "--outdir", str((root / "results").resolve()),
        "-with-trace", str((root / "execution/trace.txt").resolve()),
        "-with-report", str((root / "execution/report.html").resolve()),
        "-with-timeline", str((root / "execution/timeline.html").resolve()),
    ]
    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(uuid4()),
        "started_at": started_at,
        "pipeline": PIPELINE,
        "pipeline_revision": REVISION,
        "profile": "test,docker",
        "command": command,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "test_data_source": "nf-core/rnaseq official test profile (remote test data)",
        "test_data_checksums_verified": False,
        "workflow_commit_verified": False,
        "container_digests_verified": False,
        "scientific_validation": "not_assessed",
        "status": "blocked",
        "exit_code": None,
        "blocking_reasons": [],
    }
    required = {"nextflow": shutil.which("nextflow"), "docker": shutil.which("docker")}
    missing = [name for name, binary in required.items() if binary is None]
    try:
        if missing:
            manifest["blocking_reasons"] = [f"missing executable: {name}" for name in missing]
            returncode = 2
        else:
            manifest["status"] = "failed"
            with (root / "execution/run.log").open("wb") as log:
                try:
                    proc = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=False)
                    manifest["exit_code"] = proc.returncode
                    returncode = proc.returncode
                except OSError as exc:
                    manifest["blocking_reasons"] = [f"executor start failed: {exc}"]
                    returncode = 2
            if returncode == 0:
                if not (root / "execution/trace.txt").is_file() or not any(p.is_file() for p in (root / "results").rglob("*")):
                    manifest["blocking_reasons"] = ["Nextflow exited 0 but required trace or results are missing"]
                    returncode = 1
                else:
                    manifest["status"] = "succeeded"
            elif manifest["exit_code"] is not None:
                manifest["blocking_reasons"] = ["Nextflow returned a nonzero exit code; inspect execution/run.log"]
        return returncode
    finally:
        manifest["finished_at"] = utc_now()
        try:
            manifest["artifacts"] = collect_artifacts(root)
        except ValueError as exc:
            manifest["status"] = "failed"
            manifest["blocking_reasons"] = [*manifest["blocking_reasons"], str(exc)]
            manifest["artifacts"] = []
        save_manifest(root, manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "verify"):
        sub.add_parser(name).add_argument("run_dir", type=Path)
    args = parser.parse_args()
    if args.command == "run":
        result = run(args.run_dir.resolve())
        print(f"execution exit={result}; inspect {args.run_dir / MANIFEST_NAME}")
        return result
    errors = verify(args.run_dir.resolve())
    if errors:
        print("INTEGRITY FAILED:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    print("INTEGRITY PASS (not an execution or science PASS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
