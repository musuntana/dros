"""Offline contract tests; do not execute the real nf-core pipeline."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from workflows.rnaseq.phase0 import MANIFEST_NAME, collect_artifacts, run, save_manifest, verify


def fixture_run(root: Path) -> dict:
    (root / "execution").mkdir(parents=True)
    (root / "results").mkdir()
    (root / "results" / "table.tsv").write_text("gene\tvalue\nA\t1\n", encoding="utf-8")
    manifest = {
        "schema_version": "dros.nfcore-smoke.v1",
        "pipeline": "nf-core/rnaseq",
        "pipeline_revision": "3.27.0",
        "status": "succeeded",
        "exit_code": 0,
        "artifacts": collect_artifacts(root),
    }
    save_manifest(root, manifest)
    return manifest


def test_round_trip(tmp_path: Path) -> None:
    fixture_run(tmp_path)
    assert verify(tmp_path) == []


def test_detects_tampering(tmp_path: Path) -> None:
    fixture_run(tmp_path)
    (tmp_path / "results/table.tsv").write_text("tampered", encoding="utf-8")
    assert any("mismatch" in msg for msg in verify(tmp_path))


def test_rejects_traversal(tmp_path: Path) -> None:
    manifest = fixture_run(tmp_path)
    manifest["artifacts"][0]["path"] = "results/../../outside.txt"
    save_manifest(tmp_path, manifest)
    assert any("unsafe" in msg for msg in verify(tmp_path))


def test_rejects_added_untracked_file(tmp_path: Path) -> None:
    fixture_run(tmp_path)
    (tmp_path / "results/new.txt").write_text("unknown")
    assert any("inventory mismatch" in msg for msg in verify(tmp_path))


def test_rejects_symlink(tmp_path: Path) -> None:
    fixture_run(tmp_path)
    (tmp_path / "results/shortcut").symlink_to(tmp_path / "results/table.tsv")
    assert any("symlink" in msg for msg in verify(tmp_path))


def test_rejects_malformed_and_fake_success(tmp_path: Path) -> None:
    manifest = fixture_run(tmp_path)
    manifest["exit_code"] = 42
    save_manifest(tmp_path, manifest)
    assert any("exit_code" in msg for msg in verify(tmp_path))
    (tmp_path / MANIFEST_NAME).write_text("garbage", encoding="utf-8")
    assert any("cannot read" in msg for msg in verify(tmp_path))


def test_missing_dependencies_remains_blocked(tmp_path: Path) -> None:
    root = tmp_path / "one-run"
    with patch("workflows.rnaseq.phase0.shutil.which", return_value=None):
        assert run(root) == 2
    manifest = json.loads((root / MANIFEST_NAME).read_text())
    assert manifest["status"] == "blocked"
    assert manifest["exit_code"] is None
    assert manifest["scientific_validation"] == "not_assessed"
    assert "missing executable" in manifest["blocking_reasons"][0]
    assert verify(root) == []


def test_refuses_overwrite(tmp_path: Path) -> None:
    root = tmp_path / "existing"
    root.mkdir()
    assert run(root) == 2
    assert not (root / MANIFEST_NAME).exists()
