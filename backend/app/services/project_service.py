from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from ..auth import ROLE_SCOPE_TOKENS
from ..repositories.base import append_audit_event
from ..schemas.api import (
    AddProjectMemberRequest,
    AddProjectMemberResponse,
    CreateProjectRequest,
    CreateProjectResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectMemberListResponse,
    ReviewSummaryScopeRead,
    UpdateProjectRequest,
)
from ..schemas.domain import ManuscriptRead, ProjectMemberRead, ProjectRead, ReviewRead
from ..schemas.enums import LineageKind, ProjectRole, ProjectState, WorkflowState
from .base import BaseService


@dataclass(slots=True)
class ProjectService(BaseService):
    repository: object

    def create_project(self, payload: CreateProjectRequest) -> CreateProjectResponse:
        self.require_scopes("projects:write")
        now = self.now()
        project = ProjectRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            name=payload.name,
            project_type=payload.project_type,
            status=ProjectState.DRAFT,
            compliance_level=payload.compliance_level,
            owner_id=payload.owner_id,
            active_manuscript_id=None,
            created_at=now,
            updated_at=now,
        )
        self.repository.store.projects[project.id] = project

        membership = ProjectMemberRead(
            project_id=project.id,
            principal_id=payload.owner_id,
            role=ProjectRole.OWNER,
            scopes_json={
                "role": ProjectRole.OWNER.value,
                "scope_tokens": list(ROLE_SCOPE_TOKENS[ProjectRole.OWNER]),
                "capabilities": list(ROLE_SCOPE_TOKENS[ProjectRole.OWNER]),
            },
            joined_at=now,
        )
        self.repository.store.project_members[(project.id, payload.owner_id)] = membership
        append_audit_event(
            self.repository.store,
            project_id=project.id,
            event_type="project.created",
            target_kind=LineageKind.PROJECT,
            target_id=project.id,
            payload_json={"owner_id": str(payload.owner_id), "project_type": payload.project_type.value},
            actor_id=self.repository.actor_id,
        )
        return CreateProjectResponse(project=project)

    def list_projects(self, *, limit: int, offset: int) -> ProjectListResponse:
        self.require_scopes("projects:read")
        items = sorted(
            self.repository.list_accessible_projects(),
            key=lambda project: project.created_at,
            reverse=True,
        )
        return ProjectListResponse(items=self.paginate(items, limit=limit, offset=offset))

    def get_project(self, project_id: UUID) -> ProjectDetailResponse:
        project = self._require_project(project_id, "projects:read")
        active_workflows = sorted(
            [
                workflow
                for workflow in self.repository.store.workflow_instances.values()
                if workflow.project_id == project_id
                and workflow.ended_at is None
                and workflow.state not in {
                    WorkflowState.APPROVED,
                    WorkflowState.BLOCKED,
                    WorkflowState.EXPORTED,
                    WorkflowState.FAILED,
                }
            ],
            key=lambda workflow: workflow.started_at,
            reverse=True,
        )
        snapshots = [
            snapshot
            for snapshot in self.repository.store.dataset_snapshots.values()
            if snapshot.project_id == project_id
        ]
        latest_snapshot = max(snapshots, key=lambda snapshot: snapshot.created_at, default=None)
        active_manuscript = (
            self.repository.store.manuscripts.get(project.active_manuscript_id)
            if project.active_manuscript_id
            else None
        )
        review_summary = Counter(
            review.state.value for review in self._list_active_manuscript_reviews(project_id, active_manuscript)
        )
        review_summary_scope = (
            ReviewSummaryScopeRead(
                target_kind=LineageKind.MANUSCRIPT,
                target_id=active_manuscript.id,
                target_version_no=active_manuscript.current_version_no,
                label=active_manuscript.title,
            )
            if active_manuscript is not None
            else None
        )
        return ProjectDetailResponse(
            project=project,
            active_workflows=active_workflows,
            latest_snapshot=latest_snapshot,
            active_manuscript=active_manuscript,
            review_summary=dict(review_summary),
            review_summary_scope=review_summary_scope,
        )

    def update_project(self, project_id: UUID, payload: UpdateProjectRequest) -> ProjectDetailResponse:
        project = self._require_project(project_id, "projects:write")
        updated = project.model_copy(
            update={**payload.model_dump(exclude_unset=True), "updated_at": self.now()}
        )
        self.repository.store.projects[project_id] = updated
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="project.updated",
            target_kind=LineageKind.PROJECT,
            target_id=project_id,
            payload_json=payload.model_dump(exclude_unset=True),
            actor_id=self.repository.actor_id,
        )
        return self.get_project(project_id)

    def add_member(self, project_id: UUID, payload: AddProjectMemberRequest) -> AddProjectMemberResponse:
        self._require_project(project_id, "members:write")
        membership = ProjectMemberRead(
            project_id=project_id,
            principal_id=payload.principal_id,
            role=payload.role,
            scopes_json={
                "role": payload.role.value,
                "scope_tokens": list(ROLE_SCOPE_TOKENS[payload.role]),
                "capabilities": list(ROLE_SCOPE_TOKENS[payload.role]),
            },
            joined_at=self.now(),
        )
        self.repository.store.project_members[(project_id, payload.principal_id)] = membership
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="project.member_added",
            target_kind=LineageKind.PROJECT,
            target_id=project_id,
            payload_json={"principal_id": str(payload.principal_id), "role": payload.role.value},
            actor_id=self.repository.actor_id,
        )
        return AddProjectMemberResponse(membership=membership)

    def list_members(self, project_id: UUID) -> ProjectMemberListResponse:
        self._require_project(project_id, "projects:read")
        members = [
            membership
            for membership in self.repository.store.project_members.values()
            if membership.project_id == project_id
        ]
        members.sort(key=lambda membership: membership.joined_at)
        return ProjectMemberListResponse(items=members)

    def _require_project(self, project_id: UUID, *required_scopes: str) -> ProjectRead:
        return self.repository.require_project(project_id, required_scopes=tuple(required_scopes))

    def _list_active_manuscript_reviews(
        self,
        project_id: UUID,
        manuscript: ManuscriptRead | None,
    ) -> list[ReviewRead]:
        if manuscript is None:
            return []

        all_reviews = [
            review
            for review in self.repository.store.reviews.values()
            if review.project_id == project_id
            and review.target_kind == LineageKind.MANUSCRIPT
            and review.target_id == manuscript.id
        ]
        if not all_reviews:
            return []

        version_boundary = self._get_current_manuscript_version_boundary(project_id, manuscript)
        current_version_reviews: list[ReviewRead] = []
        for review in all_reviews:
            if review.target_version_no is not None:
                if review.target_version_no == manuscript.current_version_no:
                    current_version_reviews.append(review)
                continue

            if version_boundary is None or review.created_at >= version_boundary:
                current_version_reviews.append(review)

        current_version_reviews.sort(key=lambda review: review.created_at, reverse=True)
        return current_version_reviews

    def _get_current_manuscript_version_boundary(
        self,
        project_id: UUID,
        manuscript: ManuscriptRead,
    ) -> datetime | None:
        current_version_blocks = [
            block
            for block in self.repository.store.manuscript_blocks.values()
            if block.project_id == project_id
            and block.manuscript_id == manuscript.id
            and block.version_no == manuscript.current_version_no
        ]
        earliest_block_timestamp = self._earliest_datetime(block.created_at for block in current_version_blocks)
        version_anchor = manuscript.updated_at if manuscript.current_version_no > 1 else self._first_defined_datetime(
            manuscript.updated_at,
            manuscript.created_at,
        )
        return self._earliest_datetime(value for value in (earliest_block_timestamp, version_anchor) if value is not None)

    @staticmethod
    def _first_defined_datetime(*values: datetime | None) -> datetime | None:
        for value in values:
            if value is not None:
                return value
        return None

    @staticmethod
    def _earliest_datetime(values: Iterable[datetime]) -> datetime | None:
        earliest: datetime | None = None
        for value in values:
            if earliest is None or value < earliest:
                earliest = value
        return earliest
