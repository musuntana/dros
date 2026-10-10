# Scientific Phase 0 Status — 2026-10-10

- Added optional version-requested `nf-core/rnaseq` CPU/Docker smoke runner, SHA256 evidence inventory and independent integrity validator.
- **Offline test:** `python -m pytest -q tests/test_rnaseq_phase0.py` → 8 passed in a local source-only Python 3.13.5 workspace. Those tests did **not** run Nextflow.
- **Real nf-core run:** BLOCKED, not executed in this environment (both `nextflow` and `docker` absent). The blocked behavior was exercised locally and produced `status=blocked`, exit=2, and explicit missing dependency reasons.
- **Original DR-OS backend/full UI tests:** Not re-run in this isolated workspace; repository CI must be checked before merge.
- **Scientific validity and independent replication:** NOT ASSESSED.

## Exit gates

1. Real public-data Nextflow run with full trace/terminal logs, report, MultiQC and result artifacts.
2. Independently record exact pipeline commit, tool versions, reference/FASTQ checksums and container image digests; lock the environment.
3. Connect this path to approved DR-OS templates and project-scoped audit/artifact services, not via user-submitted shell arguments.
4. Separate `nf-core/differentialabundance` template for properly designed DEG statistics.

**Do not mark scientific Phase 0 accepted until real E2E evidence is collected.**

## Phase 0.2: result-byte comparison (2026-10-10)

- Added standalone `workflows/rnaseq/compare.py` for two integrity-checked, separately identified executions.
- Added 10 synthetic/fixture tests in `tests/test_rnaseq_compare.py`; fixtures are not scientific experiments.
- Added the comparison tests to scientific offline GitHub CI. Check the latest PR commit's workflow run before declaring its checks accepted.
- Comparison results intentionally distinguish identical result bytes from scientifically reproducible experimental conclusions.
- Actual upstream input checksums, exact resolved pipeline commit, container digest verification, true E2E and independent scientific validation remain **NOT COMPLETE**.
