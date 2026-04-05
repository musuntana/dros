from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import NoReturn

from ..schemas.common import Page, PageInfo


class ServiceNotImplementedError(NotImplementedError):
    """Raised when a service skeleton has not been implemented yet."""


class BaseService:
    def require_scopes(self, *required_scopes: str) -> None:
        self.repository.require_scopes(*required_scopes)

    def require_project_scopes(self, project_id, *required_scopes: str):
        return self.repository.require_project(project_id, required_scopes=tuple(required_scopes))

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def paginate(items: Iterable[object], *, limit: int, offset: int) -> Page[object]:
        sequence = list(items)
        return Page(
            items=sequence[offset : offset + limit],
            page=PageInfo(total=len(sequence), limit=limit, offset=offset),
        )

    @classmethod
    def not_implemented(cls, operation: str) -> NoReturn:
        raise ServiceNotImplementedError(f"{cls.__name__}.{operation} is not implemented")
