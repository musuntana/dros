from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from ..schemas.domain import AssertionRead, GateEvaluationRead, ManuscriptBlockRead, ManuscriptRead
from ..schemas.enums import AssertionState, GateName, GateStatus, LicenseClass, LineageKind, VerifierStatus


@dataclass(slots=True)
class GateEvaluationBundle:
    evaluations: list[GateEvaluationRead] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EvidenceControlPlane:
    repository: object

    def evaluate_assertion(
        self,
        *,
        project_id: UUID,
        assertion: AssertionRead,
        verification_id: UUID,
        evaluated_at,
    ) -> GateEvaluationBundle:
        evidence_links = self._list_assertion_links(project_id, assertion.id)
        citation_reasons, citation_details = self._evaluate_citation_resolver_links(evidence_links)
        binder_reasons, binder_details = self._evaluate_assertion_binder(project_id, assertion, evidence_links)
        consistency_reasons, consistency_details = self._evaluate_assertion_data_consistency(assertion)
        license_reasons, license_details = self._evaluate_license_guard_links(evidence_links)

        evaluations = [
            self._build_gate_evaluation(
                verification_id=verification_id,
                gate_name=GateName.CITATION_RESOLVER,
                target_kind=LineageKind.ASSERTION,
                target_id=assertion.id,
                reasons=citation_reasons,
                details_json={
                    "assertion_id": str(assertion.id),
                    "checked_links": len(evidence_links),
                    **citation_details,
                },
                evaluated_at=evaluated_at,
            ),
            self._build_gate_evaluation(
                verification_id=verification_id,
                gate_name=GateName.CLAIM_EVIDENCE_BINDER,
                target_kind=LineageKind.ASSERTION,
                target_id=assertion.id,
                reasons=binder_reasons,
                details_json={
                    "assertion_id": str(assertion.id),
                    **binder_details,
                },
                evaluated_at=evaluated_at,
            ),
            self._build_gate_evaluation(
                verification_id=verification_id,
                gate_name=GateName.DATA_CONSISTENCY_CHECKER,
                target_kind=LineageKind.ASSERTION,
                target_id=assertion.id,
                reasons=consistency_reasons,
                details_json={
                    "assertion_id": str(assertion.id),
                    **consistency_details,
                },
                evaluated_at=evaluated_at,
            ),
            self._build_gate_evaluation(
                verification_id=verification_id,
                gate_name=GateName.LICENSE_GUARD,
                target_kind=LineageKind.ASSERTION,
                target_id=assertion.id,
                reasons=license_reasons,
                details_json={
                    "assertion_id": str(assertion.id),
                    "checked_links": len(evidence_links),
                    **license_details,
                },
                evaluated_at=evaluated_at,
            ),
        ]
        return GateEvaluationBundle(
            evaluations=evaluations,
            blocking_reasons=self._collect_blocking_reasons(evaluations),
        )

    def evaluate_manuscript(
        self,
        *,
        project_id: UUID,
        manuscript: ManuscriptRead,
        blocks: list[ManuscriptBlockRead],
        verification_id: UUID,
        evaluated_at,
    ) -> GateEvaluationBundle:
        evidence_links = self._collect_block_evidence_links(project_id, blocks)
        citation_reasons, citation_details = self._evaluate_citation_resolver_links(evidence_links)
        binder_reasons, binder_details = self._evaluate_manuscript_binder(project_id, manuscript, blocks)
        consistency_reasons, consistency_details = self._evaluate_manuscript_data_consistency(project_id, blocks)
        license_reasons, license_details = self._evaluate_license_guard_links(evidence_links)

        evaluations = [
            self._build_gate_evaluation(
                verification_id=verification_id,
                gate_name=GateName.CITATION_RESOLVER,
                target_kind=LineageKind.MANUSCRIPT,
                target_id=manuscript.id,
                reasons=citation_reasons,
                details_json={
                    "manuscript_id": str(manuscript.id),
                    "version_no": manuscript.current_version_no,
                    "block_count": len(blocks),
                    **citation_details,
                },
                evaluated_at=evaluated_at,
            ),
            self._build_gate_evaluation(
                verification_id=verification_id,
                gate_name=GateName.CLAIM_EVIDENCE_BINDER,
                target_kind=LineageKind.MANUSCRIPT,
                target_id=manuscript.id,
                reasons=binder_reasons,
                details_json={
                    "manuscript_id": str(manuscript.id),
                    "version_no": manuscript.current_version_no,
                    "block_count": len(blocks),
                    **binder_details,
                },
                evaluated_at=evaluated_at,
            ),
            self._build_gate_evaluation(
                verification_id=verification_id,
                gate_name=GateName.DATA_CONSISTENCY_CHECKER,
                target_kind=LineageKind.MANUSCRIPT,
                target_id=manuscript.id,
                reasons=consistency_reasons,
                details_json={
                    "manuscript_id": str(manuscript.id),
                    "version_no": manuscript.current_version_no,
                    "block_count": len(blocks),
                    **consistency_details,
                },
                evaluated_at=evaluated_at,
            ),
            self._build_gate_evaluation(
                verification_id=verification_id,
                gate_name=GateName.LICENSE_GUARD,
                target_kind=LineageKind.MANUSCRIPT,
                target_id=manuscript.id,
                reasons=license_reasons,
                details_json={
                    "manuscript_id": str(manuscript.id),
                    "version_no": manuscript.current_version_no,
                    "block_count": len(blocks),
                    **license_details,
                },
                evaluated_at=evaluated_at,
            ),
        ]
        return GateEvaluationBundle(
            evaluations=evaluations,
            blocking_reasons=self._collect_blocking_reasons(evaluations),
        )

    def evaluate_evidence_link(self, *, link) -> list[str]:
        source = self.repository.store.evidence_sources.get(link.evidence_source_id)
        if source is None:
            return [f"evidence source {link.evidence_source_id} not found"]
        reasons: list[str] = []
        if not self._has_evidence_identifier(source):
            reasons.append(f"evidence source {source.id} missing canonical identifiers")
        if source.source_type.value in {"pubmed", "pmc"} and source.pmid is None and source.pmcid is None and source.doi_norm is None:
            reasons.append(f"evidence source {source.id} unresolved for pubmed/pmc identifiers")
        license_reasons, _ = self._evaluate_license_guard_links([link])
        reasons.extend(license_reasons)
        return list(dict.fromkeys(reasons))

    def _build_gate_evaluation(
        self,
        *,
        verification_id: UUID,
        gate_name: GateName,
        target_kind: LineageKind,
        target_id: UUID,
        reasons: list[str],
        details_json: dict[str, object],
        evaluated_at,
    ) -> GateEvaluationRead:
        return GateEvaluationRead(
            verification_id=verification_id,
            gate_name=gate_name,
            target_kind=target_kind,
            target_id=target_id,
            status=GateStatus.BLOCKED if reasons else GateStatus.PASSED,
            details_json={**details_json, "reasons": list(dict.fromkeys(reasons))},
            evaluated_by=None,
            evaluated_at=evaluated_at,
        )

    def _evaluate_citation_resolver_links(self, evidence_links) -> tuple[list[str], dict[str, object]]:
        reasons: list[str] = []
        missing_identifiers: list[str] = []
        unresolved_sources: list[str] = []
        missing_sources: list[str] = []
        for link in evidence_links:
            source = self.repository.store.evidence_sources.get(link.evidence_source_id)
            if source is None:
                missing_sources.append(str(link.evidence_source_id))
                reasons.append(f"evidence source {link.evidence_source_id} not found")
                continue
            if not self._has_evidence_identifier(source):
                missing_identifiers.append(str(source.id))
                reasons.append(f"evidence source {source.id} missing canonical identifiers")
            if source.source_type.value in {"pubmed", "pmc"} and source.pmid is None and source.pmcid is None and source.doi_norm is None:
                unresolved_sources.append(str(source.id))
                reasons.append(f"evidence source {source.id} unresolved for pubmed/pmc identifiers")
        return (
            list(dict.fromkeys(reasons)),
            {
                "missing_sources": sorted(set(missing_sources)),
                "missing_identifiers": sorted(set(missing_identifiers)),
                "unresolved_sources": sorted(set(unresolved_sources)),
            },
        )

    def _evaluate_assertion_binder(
        self,
        project_id: UUID,
        assertion: AssertionRead,
        evidence_links,
    ) -> tuple[list[str], dict[str, object]]:
        reasons: list[str] = []
        broken_chains: list[dict[str, str]] = []
        binding_errors: list[str] = []
        if assertion.source_artifact_id is not None:
            artifact = self.repository.store.artifacts.get(assertion.source_artifact_id)
            if artifact is None or artifact.project_id != project_id:
                binding_errors.append("source_artifact_missing")
                reasons.append(f"assertion {assertion.id} source artifact is missing")
            elif artifact.superseded_by is not None:
                broken_chains.append(
                    {
                        "assertion_id": str(assertion.id),
                        "reason": "source_artifact superseded without replacement",
                    }
                )
                reasons.append(f"assertion {assertion.id} source artifact was superseded")
        elif not evidence_links:
            binding_errors.append("missing_source_binding")
            reasons.append(f"assertion {assertion.id} missing source_artifact_id or evidence_links")
        if evidence_links and not any(link.verifier_status == VerifierStatus.PASSED for link in evidence_links):
            binding_errors.append("no_verified_evidence_link")
            reasons.append(f"assertion {assertion.id} evidence links are not verified")
        return (
            list(dict.fromkeys(reasons)),
            {
                "has_source_artifact": assertion.source_artifact_id is not None,
                "has_source_run": assertion.source_run_id is not None,
                "linked_evidence_count": len(evidence_links),
                "broken_chains": broken_chains,
                "binding_errors": sorted(set(binding_errors)),
            },
        )

    def _evaluate_assertion_data_consistency(self, assertion: AssertionRead) -> tuple[list[str], dict[str, object]]:
        reasons: list[str] = []
        inconsistencies: list[dict[str, object]] = []
        if assertion.numeric_payload_json and not assertion.source_span_json:
            reasons.append(f"assertion {assertion.id} numeric payload missing source_span_json")
            inconsistencies.append(
                {
                    "assertion_id": str(assertion.id),
                    "field": "source_span_json",
                    "reason": "numeric payload missing source span",
                }
            )
        numeric_tokens = self._extract_numeric_tokens(assertion.text_norm)
        payload_tokens = {
            str(value)
            for value in assertion.numeric_payload_json.values()
            if isinstance(value, int | float)
        }
        extra_tokens = sorted(token for token in numeric_tokens if token not in payload_tokens)
        if extra_tokens:
            reasons.append(f"assertion {assertion.id} text_norm contains ungrounded numeric tokens: {', '.join(extra_tokens)}")
            inconsistencies.append(
                {
                    "assertion_id": str(assertion.id),
                    "field": "text_norm",
                    "reason": "ungrounded numeric tokens",
                    "text_tokens": extra_tokens,
                }
            )
        return (
            list(dict.fromkeys(reasons)),
            {
                "numeric_fields": sorted(assertion.numeric_payload_json.keys()),
                "inconsistencies": inconsistencies,
            },
        )

    def _evaluate_license_guard_links(self, evidence_links) -> tuple[list[str], dict[str, object]]:
        reasons: list[str] = []
        restricted_sources: list[str] = []
        metadata_only_span_violations: list[str] = []
        for link in evidence_links:
            source = self.repository.store.evidence_sources.get(link.evidence_source_id)
            if source is None:
                continue
            if source.license_class == LicenseClass.RESTRICTED:
                restricted_sources.append(str(source.id))
                reasons.append(f"evidence source {source.id} license is restricted")
            uses_span_level_support = any(
                value is not None
                for value in [link.source_chunk_id, link.source_span_start, link.source_span_end, link.excerpt_hash]
            )
            if source.license_class == LicenseClass.METADATA_ONLY and uses_span_level_support:
                metadata_only_span_violations.append(str(source.id))
                reasons.append(f"evidence source {source.id} metadata_only cannot support excerpt or span binding")
        return (
            list(dict.fromkeys(reasons)),
            {
                "restricted_sources": sorted(set(restricted_sources)),
                "metadata_only_span_violations": sorted(set(metadata_only_span_violations)),
            },
        )

    def _evaluate_manuscript_binder(
        self,
        project_id: UUID,
        manuscript: ManuscriptRead,
        blocks: list[ManuscriptBlockRead],
    ) -> tuple[list[str], dict[str, object]]:
        reasons: list[str] = []
        orphan_blocks: list[str] = []
        missing_assertions: list[str] = []
        unverified_assertions: list[str] = []
        missing_block_links: list[dict[str, str]] = []
        missing_sources: list[str] = []
        broken_chains: list[dict[str, str]] = []
        for block in blocks:
            if not block.assertion_ids:
                orphan_blocks.append(str(block.id))
                reasons.append(f"block {block.id} missing assertion_ids")
                continue
            for assertion_id in block.assertion_ids:
                assertion = self.repository.store.assertions.get(assertion_id)
                if assertion is None or assertion.project_id != project_id:
                    missing_assertions.append(str(assertion_id))
                    reasons.append(f"assertion {assertion_id} not found")
                    continue
                if assertion.state != AssertionState.VERIFIED:
                    unverified_assertions.append(str(assertion.id))
                    reasons.append(f"assertion {assertion_id} is not verified")
                if (block.id, assertion_id) not in self.repository.store.block_assertion_links:
                    missing_block_links.append({"block_id": str(block.id), "assertion_id": str(assertion_id)})
                    reasons.append(f"block {block.id} missing block_assertion_link for {assertion_id}")
                assertion_links = self._list_assertion_links(project_id, assertion_id)
                if assertion.source_artifact_id is None and not assertion_links:
                    missing_sources.append(str(assertion.id))
                    reasons.append(f"assertion {assertion_id} missing source_artifact_id or evidence_links")
                if assertion.source_artifact_id is not None:
                    artifact = self.repository.store.artifacts.get(assertion.source_artifact_id)
                    if artifact is not None and artifact.superseded_by is not None:
                        broken_chains.append(
                            {
                                "assertion_id": str(assertion.id),
                                "reason": "source_artifact superseded without replacement",
                            }
                        )
                        reasons.append(f"assertion {assertion.id} source artifact was superseded")

        dangling_assertions = [
            str(assertion.id)
            for assertion in self.repository.store.assertions.values()
            if assertion.project_id == project_id
            and assertion.state == AssertionState.VERIFIED
            and not self._has_any_block_reference(assertion.id)
        ]
        for assertion_id in dangling_assertions:
            reasons.append(f"assertion {assertion_id} is dangling")

        return (
            list(dict.fromkeys(reasons)),
            {
                "manuscript_id": str(manuscript.id),
                "version_no": manuscript.current_version_no,
                "orphan_blocks": sorted(set(orphan_blocks)),
                "missing_assertions": sorted(set(missing_assertions)),
                "unverified_assertions": sorted(set(unverified_assertions)),
                "missing_block_links": missing_block_links,
                "missing_sources": sorted(set(missing_sources)),
                "dangling_assertions": sorted(set(dangling_assertions)),
                "broken_chains": broken_chains,
            },
        )

    def _evaluate_manuscript_data_consistency(
        self,
        project_id: UUID,
        blocks: list[ManuscriptBlockRead],
    ) -> tuple[list[str], dict[str, object]]:
        reasons: list[str] = []
        inconsistencies: list[dict[str, object]] = []
        for block in blocks:
            assertion_numeric_tokens: set[str] = set()
            values_by_field: dict[str, set[str]] = {}
            for assertion_id in block.assertion_ids:
                assertion = self.repository.store.assertions.get(assertion_id)
                if assertion is None or assertion.project_id != project_id:
                    continue
                assertion_numeric_tokens.update(
                    str(value)
                    for value in assertion.numeric_payload_json.values()
                    if isinstance(value, int | float)
                )
                for field, value in assertion.numeric_payload_json.items():
                    if isinstance(value, int | float):
                        values_by_field.setdefault(field, set()).add(str(value))
            block_numeric_tokens = self._extract_numeric_tokens(block.content_md)
            extra_tokens = sorted(token for token in block_numeric_tokens if token not in assertion_numeric_tokens)
            if extra_tokens:
                reasons.append(f"block {block.id} contains ungrounded numeric tokens: {', '.join(extra_tokens)}")
                inconsistencies.append(
                    {
                        "block_id": str(block.id),
                        "field": "content_md",
                        "reason": "ungrounded numeric tokens",
                        "text_tokens": extra_tokens,
                    }
                )
            for field, values in sorted(values_by_field.items()):
                if len(values) > 1:
                    reasons.append(f"block {block.id} contains conflicting assertion values for {field}")
                    inconsistencies.append(
                        {
                            "block_id": str(block.id),
                            "field": field,
                            "reason": "conflicting assertion payload values",
                            "values": sorted(values),
                        }
                    )
        return (
            list(dict.fromkeys(reasons)),
            {
                "inconsistencies": inconsistencies,
            },
        )

    def _collect_block_evidence_links(self, project_id: UUID, blocks: list[ManuscriptBlockRead]):
        assertion_ids = {assertion_id for block in blocks for assertion_id in block.assertion_ids}
        return [
            link
            for link in self.repository.store.evidence_links.values()
            if link.project_id == project_id and link.assertion_id in assertion_ids
        ]

    def _list_assertion_links(self, project_id: UUID, assertion_id: UUID):
        return [
            link
            for link in self.repository.store.evidence_links.values()
            if link.project_id == project_id and link.assertion_id == assertion_id
        ]

    def _has_any_block_reference(self, assertion_id: UUID) -> bool:
        return any(link.assertion_id == assertion_id for link in self.repository.store.block_assertion_links.values())

    @staticmethod
    def _collect_blocking_reasons(evaluations: list[GateEvaluationRead]) -> list[str]:
        reasons: list[str] = []
        for evaluation in evaluations:
            reasons.extend(evaluation.details_json.get("reasons", []))
        return list(dict.fromkeys(reasons))

    @staticmethod
    def _extract_numeric_tokens(text: str) -> set[str]:
        normalized = text.replace("%", " ").replace(",", " ").replace("(", " ").replace(")", " ")
        return {
            token.rstrip(".")
            for token in normalized.split()
            if any(char.isdigit() for char in token)
        }

    @staticmethod
    def _has_evidence_identifier(source) -> bool:
        return any([source.external_id_norm, source.pmid, source.pmcid, source.doi_norm])
