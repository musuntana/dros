from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from ..repositories.base import append_audit_event
from ..schemas.agents import SearchResultItem
from ..schemas.api import (
    CreateEvidenceLinkRequest,
    CreateEvidenceLinkResponse,
    EvidenceSearchRequest,
    EvidenceLinkListResponse,
    EvidenceSearchResponse,
    EvidenceSourceListResponse,
    ResolveEvidenceRequest,
    ResolveEvidenceResponse,
    UpsertEvidenceSourceRequest,
    UpsertEvidenceSourceResponse,
)
from ..schemas.domain import EvidenceLinkRead, EvidenceSourceRead, LineageEdgeRead, WorkflowInstanceRead, WorkflowTaskRead
from ..schemas.enums import (
    LineageEdgeType,
    LineageKind,
    TaskState,
    VerifierStatus,
    WorkflowBackend,
    WorkflowState,
)
from .base import BaseService
from .ncbi_adapter import NCBIAdapter, NCBIAdapterError, NCBIEvidenceRecord


@dataclass(slots=True)
class EvidenceService(BaseService):
    repository: object

    def search(self, project_id: UUID, payload: EvidenceSearchRequest) -> EvidenceSearchResponse:
        self._require_project(project_id, "evidence:read")
        query = (payload.query or payload.pico_question or "").strip()
        terms = {term.lower() for term in query.split() if term.strip()}
        max_results = self._requested_max_results(payload.filters)
        search_scope = self._search_scope(payload.filters)
        project_results = self._search_project_cache(project_id, terms=terms, limit=max_results)
        external_results: list[SearchResultItem] = []
        external_error: str | None = None
        external_enabled = False

        results = project_results
        result_origin = "project_cache" if results else "no_results"

        if search_scope == "project_cache_only":
            pass
        elif search_scope == "project_cache_first":
            if not results:
                external_results, external_error, external_enabled = self._search_external(query, max_results=max_results)
                if external_results:
                    results = external_results
                    result_origin = "ncbi_entrez"
                elif external_error is not None:
                    result_origin = "external_error"
                elif not external_enabled:
                    result_origin = "external_unavailable"
        elif search_scope == "external_first":
            external_results, external_error, external_enabled = self._search_external(query, max_results=max_results)
            if external_results:
                results = self._merge_results(external_results, project_results, limit=max_results)
                result_origin = "ncbi_entrez"
            elif project_results:
                results = project_results
                result_origin = "project_cache_fallback"
            elif external_error is not None:
                results = []
                result_origin = "external_error"
            elif not external_enabled:
                results = []
                result_origin = "external_unavailable"
            else:
                results = []
                result_origin = "no_results"
        else:  # external_only
            external_results, external_error, external_enabled = self._search_external(query, max_results=max_results)
            results = external_results
            if external_results:
                result_origin = "ncbi_entrez"
            elif external_error is not None:
                result_origin = "external_error"
            elif not external_enabled:
                result_origin = "external_unavailable"
            else:
                result_origin = "no_results"
        now = self.now()
        workflow = WorkflowInstanceRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            workflow_type="literature_search",
            state=WorkflowState.RETRIEVED,
            current_step="retrieved",
            parent_workflow_id=None,
            started_by=self.repository.principal_id,
            runtime_backend=WorkflowBackend.QUEUE_WORKERS,
            started_at=now,
            ended_at=now,
        )
        self.repository.store.workflow_instances[workflow.id] = workflow
        task = WorkflowTaskRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            workflow_instance_id=workflow.id,
            task_key="search",
            task_type="literature_search",
            state=TaskState.COMPLETED,
            assignee_id=self.repository.principal_id,
            input_payload_json=payload.model_dump(),
            output_payload_json={
                "query": query,
                "search_scope": search_scope,
                "result_count": len(results),
                "project_result_count": len(project_results),
                "external_result_count": len(external_results),
                "result_origin": result_origin,
                "external_error": external_error,
            },
            retry_count=0,
            scheduled_at=now,
            completed_at=now,
            created_at=now,
        )
        self.repository.store.workflow_tasks[task.id] = task
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="evidence.search.executed",
            target_kind=LineageKind.WORKFLOW_INSTANCE,
            target_id=workflow.id,
            payload_json={
                "query": query,
                "search_scope": search_scope,
                "result_count": len(results),
                "project_result_count": len(project_results),
                "external_result_count": len(external_results),
                "result_origin": result_origin,
                "external_error": external_error,
            },
        )
        return EvidenceSearchResponse(workflow_instance_id=workflow.id, results=results)

    def resolve(self, project_id: UUID, payload: ResolveEvidenceRequest) -> ResolveEvidenceResponse:
        self._require_project(project_id, "evidence:read")
        resolved: list[EvidenceSourceRead] = []
        unresolved: list[str] = []
        external_resolved_count = 0
        external_error_count = 0
        adapter = self._external_adapter()
        for identifier in payload.identifiers:
            source = self._find_source(identifier)
            if source is None and adapter is not None:
                try:
                    record = adapter.resolve_identifier(identifier)
                except NCBIAdapterError:
                    record = None
                    external_error_count += 1
                if record is not None:
                    source = self._upsert_external_record(project_id, record)
                    external_resolved_count += 1
            if source is None:
                unresolved.append(identifier)
                continue
            self._bind_source(project_id, source.id)
            resolved.append(source)
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="evidence.resolve.executed",
            target_kind=LineageKind.PROJECT,
            target_id=project_id,
            payload_json={
                "resolved_count": len(resolved),
                "unresolved_count": len(unresolved),
                "external_resolved_count": external_resolved_count,
                "external_error_count": external_error_count,
                "identifiers": payload.identifiers,
            },
        )
        return ResolveEvidenceResponse(resolved=resolved, unresolved=unresolved)

    def upsert_source(self, project_id: UUID, payload: UpsertEvidenceSourceRequest) -> UpsertEvidenceSourceResponse:
        self._require_project(project_id, "evidence:write")
        evidence_source = self._upsert_source_record(
            project_id=project_id,
            source_type=payload.source_type,
            external_id_norm=self._normalize_identifier(payload.external_id_norm),
            title=payload.title,
            doi_norm=self._normalize_identifier(payload.doi_norm),
            journal=payload.journal,
            pub_year=payload.pub_year,
            pmid=self._normalize_identifier(payload.pmid),
            pmcid=self._normalize_identifier(payload.pmcid),
            license_class=payload.license_class,
            oa_subset_flag=payload.oa_subset_flag,
            metadata_json=payload.metadata_json,
            cached_at=self.now(),
        )
        self._bind_source(project_id, evidence_source.id)
        return UpsertEvidenceSourceResponse(evidence_source=evidence_source)

    def list_sources(self, project_id: UUID, *, limit: int, offset: int) -> EvidenceSourceListResponse:
        self._require_project(project_id, "evidence:read")
        sources = [
            source
            for source_id in self._project_source_ids(project_id)
            if (source := self.repository.store.evidence_sources.get(source_id)) is not None
        ]
        sources.sort(key=lambda source: source.cached_at, reverse=True)
        return EvidenceSourceListResponse(items=self.paginate(sources, limit=limit, offset=offset))

    def list_evidence_links(self, project_id: UUID, *, limit: int, offset: int) -> EvidenceLinkListResponse:
        self._require_project(project_id, "evidence:read")
        links = sorted(
            [
                link
                for link in self.repository.store.evidence_links.values()
                if link.project_id == project_id
            ],
            key=lambda link: link.created_at,
            reverse=True,
        )
        return EvidenceLinkListResponse(items=self.paginate(links, limit=limit, offset=offset))

    def create_evidence_link(self, project_id: UUID, payload: CreateEvidenceLinkRequest) -> CreateEvidenceLinkResponse:
        self._require_project(project_id, "evidence:write")
        self._require_assertion(project_id, payload.assertion_id, "evidence:write")
        evidence_source = self._require_source(payload.evidence_source_id)
        self._bind_source(project_id, evidence_source.id)

        existing = next(
            (
                link
                for link in self.repository.store.evidence_links.values()
                if link.project_id == project_id
                and link.assertion_id == payload.assertion_id
                and link.evidence_source_id == payload.evidence_source_id
                and link.relation_type == payload.relation_type
                and link.source_chunk_id == payload.source_chunk_id
                and link.source_span_start == payload.source_span_start
                and link.source_span_end == payload.source_span_end
                and link.excerpt_hash == payload.excerpt_hash
            ),
            None,
        )
        if existing is not None:
            return CreateEvidenceLinkResponse(evidence_link=existing)

        link = EvidenceLinkRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            assertion_id=payload.assertion_id,
            evidence_source_id=payload.evidence_source_id,
            relation_type=payload.relation_type,
            source_chunk_id=payload.source_chunk_id,
            source_span_start=payload.source_span_start,
            source_span_end=payload.source_span_end,
            excerpt_hash=payload.excerpt_hash,
            verifier_status=VerifierStatus.PENDING,
            confidence=payload.confidence,
            created_at=self.now(),
        )
        self.repository.store.evidence_links[link.id] = link
        edge = LineageEdgeRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            from_kind=LineageKind.EVIDENCE_SOURCE,
            from_id=evidence_source.id,
            edge_type=LineageEdgeType.GROUNDS,
            to_kind=LineageKind.ASSERTION,
            to_id=payload.assertion_id,
            created_at=self.now(),
        )
        self.repository.store.lineage_edges[edge.id] = edge
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="evidence.link.created",
            target_kind=LineageKind.EVIDENCE_SOURCE,
            target_id=evidence_source.id,
            payload_json={
                "assertion_id": str(payload.assertion_id),
                "relation_type": payload.relation_type.value,
            },
        )
        return CreateEvidenceLinkResponse(evidence_link=link)

    def _require_project(self, project_id: UUID, *required_scopes: str) -> None:
        self.repository.require_project(project_id, required_scopes=tuple(required_scopes))

    def _require_assertion(self, project_id: UUID, assertion_id: UUID, *required_scopes: str) -> object:
        return self.repository.require_project_scoped(
            "assertions",
            project_id,
            assertion_id,
            "assertion",
            required_scopes=tuple(required_scopes),
        )

    def _require_source(self, evidence_source_id: UUID) -> EvidenceSourceRead:
        source = self.repository.store.evidence_sources.get(evidence_source_id)
        if source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"evidence source {evidence_source_id} not found",
            )
        return source

    def _find_existing_source(
        self,
        *,
        external_id_norm: str,
        doi_norm: str | None,
        pmid: str | None,
        pmcid: str | None,
    ) -> EvidenceSourceRead | None:
        for source in self.repository.store.evidence_sources.values():
            if external_id_norm and source.external_id_norm == external_id_norm:
                return source
            if doi_norm and source.doi_norm == doi_norm:
                return source
            if pmid and source.pmid == pmid:
                return source
            if pmcid and source.pmcid == pmcid:
                return source
        return None

    def _find_source(self, identifier: str) -> EvidenceSourceRead | None:
        normalized = self._normalize_identifier(identifier)
        for source in self.repository.store.evidence_sources.values():
            if normalized in {
                source.external_id_norm,
                source.doi_norm,
                source.pmid,
                source.pmcid,
            }:
                return source
        return None

    @staticmethod
    def _normalize_identifier(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.upper().startswith("PMC"):
            return normalized.upper()
        if "/" in normalized:
            return normalized.lower()
        return normalized

    def _upsert_external_record(self, project_id: UUID, record: NCBIEvidenceRecord) -> EvidenceSourceRead:
        return self._upsert_source_record(
            project_id=project_id,
            source_type=record.source_type(),
            external_id_norm=record.external_id_norm(),
            title=record.title,
            doi_norm=self._normalize_identifier(record.doi),
            journal=record.journal,
            pub_year=record.year,
            pmid=self._normalize_identifier(record.pmid),
            pmcid=self._normalize_identifier(record.pmcid),
            license_class=record.license_class,
            oa_subset_flag=record.oa_subset_flag,
            metadata_json=record.metadata_json,
            cached_at=self.now(),
        )

    def _upsert_source_record(
        self,
        *,
        project_id: UUID,
        source_type,
        external_id_norm: str,
        title: str,
        doi_norm: str | None,
        journal: str | None,
        pub_year: int | None,
        pmid: str | None,
        pmcid: str | None,
        license_class,
        oa_subset_flag: bool,
        metadata_json: dict[str, Any],
        cached_at,
    ) -> EvidenceSourceRead:
        existing = self._find_existing_source(
            external_id_norm=external_id_norm,
            doi_norm=doi_norm,
            pmid=pmid,
            pmcid=pmcid,
        )
        if existing is None:
            evidence_source = EvidenceSourceRead(
                id=uuid4(),
                source_type=source_type,
                external_id_norm=external_id_norm,
                doi_norm=doi_norm,
                title=title,
                journal=journal,
                pub_year=pub_year,
                pmid=pmid,
                pmcid=pmcid,
                license_class=license_class,
                oa_subset_flag=oa_subset_flag,
                metadata_json=metadata_json,
                cached_at=cached_at,
            )
            self.repository.store.evidence_sources[evidence_source.id] = evidence_source
            self._append_source_upsert_audit(project_id, evidence_source)
            return evidence_source

        updated = existing.model_copy(
            update={
                "source_type": source_type,
                "external_id_norm": external_id_norm,
                "doi_norm": doi_norm,
                "title": title,
                "journal": journal,
                "pub_year": pub_year,
                "pmid": pmid,
                "pmcid": pmcid,
                "license_class": license_class,
                "oa_subset_flag": oa_subset_flag,
                "metadata_json": metadata_json,
                "cached_at": cached_at,
            }
        )
        if updated.model_dump(mode="json") != existing.model_dump(mode="json"):
            self.repository.store.evidence_sources[existing.id] = updated
            self._append_source_upsert_audit(project_id, updated)
            return updated
        return existing

    def _append_source_upsert_audit(self, project_id: UUID, evidence_source: EvidenceSourceRead) -> None:
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="evidence.source.upserted",
            target_kind=LineageKind.EVIDENCE_SOURCE,
            target_id=evidence_source.id,
            payload_json={
                "external_id_norm": evidence_source.external_id_norm,
                "pmid": evidence_source.pmid,
                "pmcid": evidence_source.pmcid,
                "doi_norm": evidence_source.doi_norm,
                "license_class": evidence_source.license_class.value,
                "oa_subset_flag": evidence_source.oa_subset_flag,
            },
        )

    def _search_project_cache(self, project_id: UUID, *, terms: set[str], limit: int) -> list[SearchResultItem]:
        source_ids = self._project_source_ids(project_id)
        matched_sources = [
            source
            for source_id in source_ids
            if (source := self.repository.store.evidence_sources.get(source_id)) is not None
            and self._matches_query(source, terms)
        ]
        matched_sources.sort(key=lambda source: source.cached_at, reverse=True)
        results = [
            SearchResultItem(
                pmid=source.pmid,
                pmcid=source.pmcid,
                doi=source.doi_norm,
                title=source.title,
                journal=source.journal,
                year=source.pub_year,
                license_class=source.license_class,
                oa_subset_flag=source.oa_subset_flag,
                match_reason="cached_metadata_match",
                dedupe_key=self._dedupe_key(source),
            )
            for source in matched_sources
            if any([source.pmid, source.pmcid, source.doi_norm])
        ]
        return results[:limit]

    def _search_external(
        self,
        query: str,
        *,
        max_results: int,
    ) -> tuple[list[SearchResultItem], str | None, bool]:
        adapter = self._external_adapter()
        if adapter is None:
            return [], None, False
        try:
            external_records = adapter.search_pubmed(query, max_results=max_results)
        except NCBIAdapterError as exc:
            return [], str(exc), True
        return [record.to_search_result() for record in external_records], None, True

    @staticmethod
    def _merge_results(
        primary: list[SearchResultItem],
        secondary: list[SearchResultItem],
        *,
        limit: int,
    ) -> list[SearchResultItem]:
        merged: list[SearchResultItem] = []
        seen: set[str] = set()
        for result in [*primary, *secondary]:
            if result.dedupe_key in seen:
                continue
            seen.add(result.dedupe_key)
            merged.append(result)
            if len(merged) >= limit:
                break
        return merged

    @staticmethod
    def _requested_max_results(filters: dict[str, Any]) -> int:
        value = filters.get("max_results", 20)
        if not isinstance(value, int):
            return 20
        return max(1, min(value, 20))

    @staticmethod
    def _search_scope(filters: dict[str, Any]) -> str:
        raw_value = filters.get("search_scope", "project_cache_first")
        if not isinstance(raw_value, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="filters.search_scope must be a string",
            )
        normalized = raw_value.strip().lower().replace("-", "_")
        if normalized not in {
            "project_cache_first",
            "external_first",
            "project_cache_only",
            "external_only",
        }:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"unsupported filters.search_scope: {raw_value}",
            )
        return normalized

    def _external_adapter(self) -> NCBIAdapter | None:
        adapter = NCBIAdapter(repository=self.repository)
        if not adapter.settings.ncbi_enabled:
            return None
        return adapter

    @staticmethod
    def _dedupe_key(source: EvidenceSourceRead) -> str:
        if source.pmid:
            return f"PMID:{source.pmid}"
        if source.pmcid:
            return f"PMCID:{source.pmcid}"
        if source.doi_norm:
            return f"DOI:{source.doi_norm}"
        return source.external_id_norm

    @staticmethod
    def _matches_query(source: EvidenceSourceRead, terms: set[str]) -> bool:
        if not terms:
            return True
        haystack = " ".join(
            filter(
                None,
                [
                    source.title,
                    source.journal,
                    source.doi_norm,
                    source.pmid,
                    source.pmcid,
                    source.external_id_norm,
                ],
            )
        ).lower()
        return all(term in haystack for term in terms)

    def _bind_source(self, project_id: UUID, evidence_source_id: UUID) -> None:
        self.repository.store.project_evidence_bindings[(project_id, evidence_source_id)] = self.now()

    def _project_source_ids(self, project_id: UUID) -> set[UUID]:
        bound = {
            source_id
            for (bound_project_id, source_id), _ in self.repository.store.project_evidence_bindings.items()
            if bound_project_id == project_id
        }
        bound.update(
            link.evidence_source_id
            for link in self.repository.store.evidence_links.values()
            if link.project_id == project_id
        )
        return bound
