# ADR-0001: Optional nf-core scientific execution boundary

Status: Proposed — 2026-10-10

## Context

DR-OS already owns project-scoped `dataset_snapshot`, `analysis_run`, `artifact`, `assertion`, `evidence_link`, workflow transitions and audit records. Its current `DeterministicAnalysisRunner` is a development-only inline execution path; its results must not be described as real nf-core output. The BioAI plan calls for a CPU-first, reproducible RNA-seq golden path, not a second platform.

## Decision

- Introduce an **opt-in standalone** `workflows/rnaseq/phase0.py` adapter calling Nextflow `nf-core/rnaseq` at requested release `3.27.0` with the official `test,docker` profile. It does **not** serve an API, change DR-OS ledger state, publish research assertions or bypass the Template Registry.
- Record the exact argv, unique run ID, timestamps, exit status and artifact inventory with local SHA256 digests. Never overwrite an existing run directory.
- Provide an independent `verify` command that detects missing/modified/untracked results and unsafe artifact paths. Successful verification only establishes local integrity; it is not execution success, trusted provenance or scientific validity.
- Mark missing pipeline commit resolution, input file digests and container digest verification as **false**, never inferred from the tag or from successful exit. The signed/authenticated provenance protocol is future work.
- Before integrating into DR-OS, pass explicit template approval, PHI/data-policy gates, tenant authorization, auditable job state, artifact emitter and independent science acceptance. Nextflow remains the only scientific dependency/workflow executor. Do not add Kubernetes, GPU or a competing scheduler in Phase 0.

## Next acceptance gates

1. Execute the real nf-core test workload with Nextflow, Java and Docker daemon installed; retain actual trace, process log, MultiQC and outputs.
2. Record **resolved** workflow commit, pipeline input/reference SHA256, tool versions and actual container image digests.
3. Separately integrate `nf-core/differentialabundance` after a real expression matrix and valid experimental design are available; RNA-seq test success is not differential expression.
4. Add approved, project-scoped backend adapter via existing DR-OS ledger, artifact service, event and audit boundaries before enabling Web submission.
5. Require clean-environment replay and scientific QA; treat byte integrity, successful execution and valid scientific inference as separate gates.

## Rejected

Rebuilding the DR-OS application as a new BioAI backend, using simulated output as execution proof, and allowing arbitrary command execution from the request handler.
