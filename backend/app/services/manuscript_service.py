from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from ..repositories.base import append_audit_event
from ..schemas.api import (
    AssertionDetailResponse,
    AssertionListResponse,
    CreateAssertionRequest,
    CreateAssertionResponse,
    CreateManuscriptBlockRequest,
    CreateManuscriptBlockResponse,
    CreateManuscriptRequest,
    CreateManuscriptResponse,
    CreateManuscriptVersionRequest,
    CreateManuscriptVersionResponse,
    ManuscriptBlockListResponse,
    ManuscriptDetailResponse,
    ManuscriptListResponse,
    RenderManuscriptResponse,
)
from ..schemas.domain import (
    AssertionRead,
    BlockAssertionLinkRead,
    LineageEdgeRead,
    ManuscriptBlockRead,
    ManuscriptRead,
)
from ..schemas.enums import (
    AssertionState,
    BlockState,
    BlockType,
    LineageEdgeType,
    LineageKind,
    ManuscriptState,
    SectionKey,
)
from .base import BaseService


@dataclass(slots=True)
class ManuscriptService(BaseService):
    repository: object

    def create_manuscript(self, project_id: UUID, payload: CreateManuscriptRequest) -> CreateManuscriptResponse:
        project = self._require_project(project_id, "manuscripts:write")
        manuscript = ManuscriptRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            manuscript_type=payload.manuscript_type,
            title=payload.title,
            state=ManuscriptState.DRAFT,
            current_version_no=1,
            style_profile_json=payload.style_profile_json,
            target_journal=payload.target_journal,
            created_by=self.repository.principal_id,
            created_at=self.now(),
            updated_at=self.now(),
        )
        self.repository.store.manuscripts[manuscript.id] = manuscript
        self.repository.store.projects[project.id] = project.model_copy(
            update={"active_manuscript_id": manuscript.id, "updated_at": self.now()}
        )
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="manuscript.created",
            target_kind=LineageKind.MANUSCRIPT,
            target_id=manuscript.id,
            payload_json={"title": manuscript.title, "manuscript_type": manuscript.manuscript_type.value},
        )
        return CreateManuscriptResponse(manuscript=manuscript)

    def list_manuscripts(self, project_id: UUID) -> ManuscriptListResponse:
        self._require_project(project_id, "manuscripts:read")
        items = [
            manuscript
            for manuscript in self.repository.store.manuscripts.values()
            if manuscript.project_id == project_id
        ]
        items.sort(key=lambda manuscript: manuscript.created_at, reverse=True)
        return ManuscriptListResponse(items=items)

    def get_manuscript(self, project_id: UUID, manuscript_id: UUID) -> ManuscriptDetailResponse:
        manuscript = self._require_manuscript(project_id, manuscript_id, "manuscripts:read")
        return ManuscriptDetailResponse(manuscript=manuscript)

    def create_assertion(self, project_id: UUID, payload: CreateAssertionRequest) -> CreateAssertionResponse:
        self._require_project(project_id, "assertions:write")
        if payload.source_artifact_id is None and payload.source_run_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="assertion requires source_artifact_id or source_run_id",
            )
        superseded_assertion = None
        if payload.supersedes_assertion_id is not None:
            superseded_assertion = self._require_assertion(project_id, payload.supersedes_assertion_id, "assertions:write")

        source_run_id = payload.source_run_id
        if payload.source_artifact_id is not None:
            artifact = self._require_artifact(project_id, payload.source_artifact_id, "assertions:write")
            if source_run_id is None:
                source_run_id = artifact.run_id
        elif source_run_id is not None:
            self._require_analysis_run(project_id, source_run_id, "assertions:write")

        assertion = AssertionRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            assertion_type=payload.assertion_type,
            text_norm=payload.text_norm,
            numeric_payload_json=payload.numeric_payload_json,
            source_run_id=source_run_id,
            source_artifact_id=payload.source_artifact_id,
            source_span_json=payload.source_span_json,
            claim_hash=payload.claim_hash,
            state=AssertionState.DRAFT,
            supersedes_assertion_id=payload.supersedes_assertion_id,
            created_at=self.now(),
        )
        self.repository.store.assertions[assertion.id] = assertion

        if assertion.source_artifact_id is not None:
            edge = LineageEdgeRead(
                id=uuid4(),
                tenant_id=self.repository.tenant_id,
                project_id=project_id,
                from_kind=LineageKind.ARTIFACT,
                from_id=assertion.source_artifact_id,
                edge_type=LineageEdgeType.DERIVES,
                to_kind=LineageKind.ASSERTION,
                to_id=assertion.id,
                created_at=self.now(),
            )
            self.repository.store.lineage_edges[edge.id] = edge
        elif assertion.source_run_id is not None:
            edge = LineageEdgeRead(
                id=uuid4(),
                tenant_id=self.repository.tenant_id,
                project_id=project_id,
                from_kind=LineageKind.ANALYSIS_RUN,
                from_id=assertion.source_run_id,
                edge_type=LineageEdgeType.DERIVES,
                to_kind=LineageKind.ASSERTION,
                to_id=assertion.id,
                created_at=self.now(),
            )
            self.repository.store.lineage_edges[edge.id] = edge
        if superseded_assertion is not None:
            supersedes_edge = LineageEdgeRead(
                id=uuid4(),
                tenant_id=self.repository.tenant_id,
                project_id=project_id,
                from_kind=LineageKind.ASSERTION,
                from_id=superseded_assertion.id,
                edge_type=LineageEdgeType.SUPERSEDES,
                to_kind=LineageKind.ASSERTION,
                to_id=assertion.id,
                created_at=self.now(),
            )
            self.repository.store.lineage_edges[supersedes_edge.id] = supersedes_edge

        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="assertion.created",
            target_kind=LineageKind.ASSERTION,
            target_id=assertion.id,
            payload_json={
                "assertion_id": str(assertion.id),
                "assertion_type": assertion.assertion_type.value,
                "state": assertion.state.value,
                "source_artifact_id": str(assertion.source_artifact_id) if assertion.source_artifact_id else None,
                "source_run_id": str(assertion.source_run_id) if assertion.source_run_id else None,
                "supersedes_assertion_id": str(assertion.supersedes_assertion_id) if assertion.supersedes_assertion_id else None,
            },
        )
        if superseded_assertion is not None:
            append_audit_event(
                self.repository.store,
                project_id=project_id,
                event_type="assertion.superseded",
                target_kind=LineageKind.ASSERTION,
                target_id=superseded_assertion.id,
                payload_json={"superseded_by_assertion_id": str(assertion.id)},
            )
        return CreateAssertionResponse(assertion=assertion)

    def list_assertions(self, project_id: UUID, *, limit: int, offset: int) -> AssertionListResponse:
        self._require_project(project_id, "assertions:read")
        items = [
            assertion
            for assertion in self.repository.store.assertions.values()
            if assertion.project_id == project_id
        ]
        items.sort(key=lambda assertion: assertion.created_at, reverse=True)
        return AssertionListResponse(items=self.paginate(items, limit=limit, offset=offset))

    def get_assertion(self, project_id: UUID, assertion_id: UUID) -> AssertionDetailResponse:
        assertion = self._require_assertion(project_id, assertion_id, "assertions:read")
        evidence_links = [
            link
            for link in self.repository.store.evidence_links.values()
            if link.project_id == project_id and link.assertion_id == assertion_id
        ]
        block_links = [
            link
            for link in self.repository.store.block_assertion_links.values()
            if link.block_id in {block.id for block in self.repository.store.manuscript_blocks.values()}
            and link.assertion_id == assertion_id
        ]
        block_links.sort(key=lambda link: link.created_at)
        return AssertionDetailResponse(assertion=assertion, evidence_links=evidence_links, block_links=block_links)

    def create_block(self, project_id: UUID, manuscript_id: UUID, payload: CreateManuscriptBlockRequest) -> CreateManuscriptBlockResponse:
        manuscript = self._require_manuscript(project_id, manuscript_id, "manuscripts:write")
        for assertion_id in payload.assertion_ids:
            assertion = self._require_assertion(project_id, assertion_id, "manuscripts:write")
            if assertion.state != AssertionState.VERIFIED:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"assertion {assertion_id} is not verified",
                )
        block = ManuscriptBlockRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            manuscript_id=manuscript_id,
            version_no=manuscript.current_version_no,
            section_key=payload.section_key,
            block_order=payload.block_order,
            block_type=payload.block_type,
            content_md=payload.content_md,
            status=BlockState.VERIFIED if payload.assertion_ids else BlockState.DRAFT,
            supersedes_block_id=None,
            created_at=self.now(),
            assertion_ids=payload.assertion_ids,
        )
        self.repository.store.manuscript_blocks[block.id] = block
        for display_order, assertion_id in enumerate(payload.assertion_ids):
            link = BlockAssertionLinkRead(
                block_id=block.id,
                assertion_id=assertion_id,
                render_role="support",
                display_order=display_order,
                created_at=self.now(),
            )
            self.repository.store.block_assertion_links[(block.id, assertion_id)] = link
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="manuscript.block.created",
            target_kind=LineageKind.MANUSCRIPT_BLOCK,
            target_id=block.id,
            payload_json={"manuscript_id": str(manuscript_id), "assertion_ids": [str(assertion_id) for assertion_id in payload.assertion_ids]},
        )
        return CreateManuscriptBlockResponse(block=block)

    def list_blocks(
        self,
        project_id: UUID,
        manuscript_id: UUID,
        *,
        version_no: int | None = None,
    ) -> ManuscriptBlockListResponse:
        manuscript = self._require_manuscript(project_id, manuscript_id, "manuscripts:read")
        target_version_no = version_no or manuscript.current_version_no
        if target_version_no > manuscript.current_version_no:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"version_no {target_version_no} is ahead of current_version_no "
                    f"{manuscript.current_version_no}"
                ),
            )
        blocks = self._list_blocks_for_version(project_id, manuscript_id, target_version_no)
        return ManuscriptBlockListResponse(items=blocks)

    def create_version(
        self,
        project_id: UUID,
        manuscript_id: UUID,
        payload: CreateManuscriptVersionRequest,
    ) -> CreateManuscriptVersionResponse:
        manuscript = self._require_manuscript(project_id, manuscript_id, "manuscripts:write")
        base_version_no = payload.base_version_no or manuscript.current_version_no
        if base_version_no > manuscript.current_version_no:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"base_version_no {base_version_no} is ahead of current_version_no "
                    f"{manuscript.current_version_no}"
                ),
            )

        now = self.now()
        next_version_no = manuscript.current_version_no + 1
        base_blocks = self._list_blocks_for_version(project_id, manuscript_id, base_version_no)
        updated = manuscript.model_copy(
            update={
                "current_version_no": next_version_no,
                "state": ManuscriptState.DRAFT,
                "updated_at": now,
            }
        )
        self.repository.store.manuscripts[manuscript_id] = updated
        cloned_blocks = 0
        for base_block in base_blocks:
            cloned_block = ManuscriptBlockRead(
                id=uuid4(),
                tenant_id=self.repository.tenant_id,
                project_id=project_id,
                manuscript_id=manuscript_id,
                version_no=next_version_no,
                section_key=base_block.section_key,
                block_order=base_block.block_order,
                block_type=base_block.block_type,
                content_md=base_block.content_md,
                status=base_block.status,
                supersedes_block_id=base_block.id,
                created_at=now,
                assertion_ids=list(base_block.assertion_ids),
            )
            self.repository.store.manuscript_blocks[cloned_block.id] = cloned_block
            cloned_blocks += 1

            existing_links = [
                link
                for link in self.repository.store.block_assertion_links.values()
                if link.block_id == base_block.id
            ]
            if existing_links:
                existing_links.sort(key=lambda link: (link.display_order, str(link.assertion_id)))
                for link in existing_links:
                    self.repository.store.block_assertion_links[(cloned_block.id, link.assertion_id)] = (
                        BlockAssertionLinkRead(
                            block_id=cloned_block.id,
                            assertion_id=link.assertion_id,
                            render_role=link.render_role,
                            display_order=link.display_order,
                            created_at=now,
                        )
                    )
            else:
                for display_order, assertion_id in enumerate(base_block.assertion_ids):
                    self.repository.store.block_assertion_links[(cloned_block.id, assertion_id)] = (
                        BlockAssertionLinkRead(
                            block_id=cloned_block.id,
                            assertion_id=assertion_id,
                            render_role="support",
                            display_order=display_order,
                            created_at=now,
                        )
                    )

        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="manuscript.version.created",
            target_kind=LineageKind.MANUSCRIPT,
            target_id=manuscript_id,
            payload_json={
                "version_no": updated.current_version_no,
                "base_version_no": base_version_no,
                "reason": payload.reason,
                "copied_block_count": cloned_blocks,
            },
        )
        return CreateManuscriptVersionResponse(manuscript=updated)

    def render(self, project_id: UUID, manuscript_id: UUID) -> RenderManuscriptResponse:
        manuscript = self._require_manuscript(project_id, manuscript_id, "manuscripts:read")
        existing_blocks = self.list_blocks(project_id, manuscript_id).items
        if existing_blocks:
            return RenderManuscriptResponse(blocks=existing_blocks, warnings=[])

        assertions = [
            assertion
            for assertion in self.repository.store.assertions.values()
            if assertion.project_id == project_id and assertion.state == AssertionState.VERIFIED
        ]
        rendered_blocks: list[ManuscriptBlockRead] = []
        for order, assertion in enumerate(assertions):
            rendered_blocks.append(
                ManuscriptBlockRead(
                    id=uuid4(),
                    tenant_id=self.repository.tenant_id,
                    project_id=project_id,
                    manuscript_id=manuscript_id,
                    version_no=manuscript.current_version_no,
                    section_key=SectionKey.RESULTS,
                    block_order=order,
                    block_type=BlockType.TEXT,
                    content_md=assertion.text_norm,
                    status=BlockState.VERIFIED,
                    supersedes_block_id=None,
                    created_at=self.now(),
                    assertion_ids=[assertion.id],
                )
            )
        return RenderManuscriptResponse(
            blocks=rendered_blocks,
            warnings=[] if rendered_blocks else ["no verified assertions available for rendering"],
        )

    def _list_blocks_for_version(self, project_id: UUID, manuscript_id: UUID, version_no: int) -> list[ManuscriptBlockRead]:
        blocks = [
            block
            for block in self.repository.store.manuscript_blocks.values()
            if block.project_id == project_id
            and block.manuscript_id == manuscript_id
            and block.version_no == version_no
        ]
        blocks.sort(key=lambda block: (block.section_key.value, block.block_order, block.created_at))
        return blocks

    def _require_project(self, project_id: UUID, *required_scopes: str) -> object:
        return self.repository.require_project(project_id, required_scopes=tuple(required_scopes))

    def _require_manuscript(self, project_id: UUID, manuscript_id: UUID, *required_scopes: str) -> ManuscriptRead:
        return self.repository.require_project_scoped(
            "manuscripts",
            project_id,
            manuscript_id,
            "manuscript",
            required_scopes=tuple(required_scopes),
        )

    def _require_artifact(self, project_id: UUID, artifact_id: UUID, *required_scopes: str) -> object:
        return self.repository.require_project_scoped(
            "artifacts",
            project_id,
            artifact_id,
            "artifact",
            required_scopes=tuple(required_scopes),
        )

    def _require_analysis_run(self, project_id: UUID, run_id: UUID, *required_scopes: str) -> object:
        return self.repository.require_project_scoped(
            "analysis_runs",
            project_id,
            run_id,
            "analysis run",
            required_scopes=tuple(required_scopes),
        )

    def _require_assertion(self, project_id: UUID, assertion_id: UUID, *required_scopes: str) -> AssertionRead:
        return self.repository.require_project_scoped(
            "assertions",
            project_id,
            assertion_id,
            "assertion",
            required_scopes=tuple(required_scopes),
        )
