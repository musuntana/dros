"""Offline comparisons use deliberately fabricated files: not scientific outputs."""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from workflows.rnaseq.compare import compare_runs
from workflows.rnaseq.phase0 import collect_artifacts, save_manifest


def _run(path: Path, text: str = "gene\nA\n", **changes: object) -> Path:
    (path / "execution").mkdir(parents=True)
    (path / "results").mkdir()
    (path / "results" / "genes.tsv").write_text(text)
    manifest = {
        "schema_version": "dros.nfcore-smoke.v1",
        "run_id": str(uuid4()),
        "pipeline": "nf-core/rnaseq",
        "pipeline_revision": "3.27.0",
        "profile": "test,docker",
        "test_data_source": "nf-core/rnaseq official test profile (remote test data)",
        "status": "succeeded",
        "exit_code": 0,
        "artifacts": collect_artifacts(path),
    }
    manifest.update(changes)
    save_manifest(path, manifest)
    return path


def test_identical_results(tmp_path: Path) -> None:
    code, report = compare_runs(_run(tmp_path / "a"), _run(tmp_path / "b"))
    assert code == 0
    assert report["verdict"] == "identical_outputs"
    assert report["scientific_validation"] == "not_assessed"


def test_changed_results(tmp_path: Path) -> None:
    code, report = compare_runs(_run(tmp_path / "a"), _run(tmp_path / "b", "gene\nB\n"))
    assert code == 1
    assert report["verdict"] == "different_outputs"
    assert report["counts"]["changed"] == 1


def test_missing_and_added_files(tmp_path: Path) -> None:
    a, b = _run(tmp_path / "a"), _run(tmp_path / "b")
    (b / "results/genes.tsv").rename(b / "results/other.tsv")
    manifest = json.loads((b / "evidence-manifest.json").read_text())
    manifest["artifacts"] = collect_artifacts(b)
    save_manifest(b, manifest)
    code, report = compare_runs(a, b)
    assert code == 1
    assert report["left_only"] == ["results/genes.tsv"]
    assert report["right_only"] == ["results/other.tsv"]


def test_input_configuration_mismatch(tmp_path: Path) -> None:
    code, report = compare_runs(_run(tmp_path / "a"), _run(tmp_path / "b", pipeline_revision="3.26.0"))
    assert code == 2
    assert report["verdict"] == "invalid_evidence"  # unsupported revision fails source verification


def test_profile_mismatch(tmp_path: Path) -> None:
    code, report = compare_runs(_run(tmp_path / "a"), _run(tmp_path / "b", profile="different"))
    assert code == 2
    assert report["verdict"] == "configuration_mismatch"


def test_tampered_file_not_compared(tmp_path: Path) -> None:
    a, b = _run(tmp_path / "a"), _run(tmp_path / "b")
    (b / "results/genes.tsv").write_text("fraud\n")
    code, report = compare_runs(a, b)
    assert code == 2
    assert report["verdict"] == "invalid_evidence"


def test_blocked_not_comparable(tmp_path: Path) -> None:
    code, report = compare_runs(_run(tmp_path / "a"), _run(tmp_path / "b", status="blocked", exit_code=None))
    assert code == 2
    assert report["verdict"] == "not_comparable"


def test_same_directory_not_independent(tmp_path: Path) -> None:
    run = _run(tmp_path / "a")
    code, report = compare_runs(run, run)
    assert code == 2
    assert "distinct" in report["blocking_reasons"][0]


def test_same_run_id_not_independent(tmp_path: Path) -> None:
    a, b = _run(tmp_path / "a"), _run(tmp_path / "b")
    manifest_a = json.loads((a / "evidence-manifest.json").read_text())
    manifest_b = json.loads((b / "evidence-manifest.json").read_text())
    manifest_b["run_id"] = manifest_a["run_id"]
    save_manifest(b, manifest_b)
    code, report = compare_runs(a, b)
    assert code == 2
    assert "same run_id" in report["blocking_reasons"][0]


def test_no_output_files(tmp_path: Path) -> None:
    a, b = _run(tmp_path / "a"), _run(tmp_path / "b")
    (b / "results/genes.tsv").unlink()
    manifest = json.loads((b / "evidence-manifest.json").read_text())
    manifest["artifacts"] = collect_artifacts(b)
    save_manifest(b, manifest)
    code, report = compare_runs(a, b)
    assert code == 2
    assert report["verdict"] == "not_comparable"
