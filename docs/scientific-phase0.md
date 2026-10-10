# DR-OS Scientific Phase 0 — RNA-seq Smoke Test

The initial implementation is an **optional CLI only**. It does not register DR-OS `AnalysisRun` records or export `Assertion`s. It uses public nf-core test data only.

## Prerequisites

Java, Nextflow, Docker CLI + running Docker daemon, CPU/RAM/disk for the official nf-core/rnaseq test profile, network access, and Python. The runner requests nf-core/rnaseq revision `3.27.0` but does not independently lock the resolved git SHA, upstream input digests, or image digests.

Run from repository root:

```bash
python workflows/rnaseq/phase0.py run ./experiments/rnaseq-test-001
python workflows/rnaseq/phase0.py verify ./experiments/rnaseq-test-001
python -m pytest -q tests/test_rnaseq_phase0.py
```

Use a **new** directory for each run. Nextflow generates `execution/run.log`, trace, report, timeline and `results/` outputs when available. The standalone CLI records `evidence-manifest.json` containing run ID, exact command, requested pipeline tag, timestamps, status, exit code, blocking reasons, execution environment and SHA256 file inventory.

If the required executables are unavailable, it exits 2 and writes an explicit **blocked** manifest. Other nonzero workflow returns are **failed**; success requires exit 0 and actual trace/output files. Results from fixtures or tests are **never** reported as scientific success.

**Distinguish three gates:** Offline unit tests verify contract behavior; the actual Nextflow run verifies execution; scientific validity requires separate domain checks. The `verify` command validates local artifact content and coverage even for blocked or failed runs. Its “INTEGRITY PASS” does **not** mean workflow execution or scientific validation succeeded. Local checksums cannot authenticate a maliciously re-written manifest without independent trust/signature.

Known limitations: no resolved commit/container lock, no trustworthy remote test-data hash recording, no independent clean replay, no data-policy service integration, no research claims, no Web integration, no differential expression, and no production scheduler. See [ADR-0001](adr/0001-scientific-execution-boundary.md).
