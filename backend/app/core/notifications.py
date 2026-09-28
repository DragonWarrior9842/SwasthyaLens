"""Owner-verified reads and deterministic read/dismiss operations."""

from uuid import UUID

from app.core.auth_service import AuthenticatedRequest
from app.core.errors import ApiProblem
from app.core.observations import ObservationService
from app.schemas.notifications import Notification, NotificationPage


def unavailable() -> ApiProblem:
    return ApiProblem(503, "notification_unavailable", "Notifications are temporarily unavailable.")


class NotificationService:
    def __init__(self, observations: ObservationService) -> None:
        self.extraction = observations.parameters.extraction

    def call(
        self,
        operation: str,
        current: AuthenticatedRequest,
        identifier: UUID | None = None,
        offset: int = 0,
    ) -> NotificationPage:
        secret = self.extraction.settings.report_processing_key
        if secret is None:
            raise unavailable()
        value = self.extraction.reports.gateway.object(
            "POST",
            "/rest/v1/rpc/notification_call",
            access_token=current.access_token,
            purpose="reports",
            payload={
                "p_operation": operation,
                "p_id": str(identifier) if identifier else None,
                "p_offset": offset,
                "p_worker_secret": secret.get_secret_value(),
            },
        )
        try:
            if (
                UUID(str(value["user_id"])) != current.identity.user_id
                or value.get("offset") != offset
            ):
                raise ValueError
            unread = value["unread_count"]
            if type(unread) is not int:
                raise ValueError
            raw = value["items"]
            if not isinstance(raw, list) or len(raw) > 21:
                raise ValueError
            rows = [Notification.model_validate(row) for row in raw]
            if any(row.user_id != current.identity.user_id for row in rows) or len(
                {r.id for r in rows}
            ) != len(rows):
                raise ValueError
            return NotificationPage(
                user_id=current.identity.user_id,
                items=rows[:20],
                unread_count=unread,
                next_offset=offset + 20 if len(rows) > 20 else None,
            )
        except (ValueError, TypeError, KeyError):
            raise unavailable() from None
