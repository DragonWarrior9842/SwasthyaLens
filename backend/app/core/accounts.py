"""Current-user repositories retain both query scoping and database RLS."""

import time

from pydantic import ValidationError

from app.core.errors import unauthenticated, unavailable
from app.core.identity import VerifiedIdentity
from app.core.provider import SupabaseGateway
from app.schemas.accounts import Profile, UserSettings


class AccountsRepository:
    def __init__(self, gateway: SupabaseGateway) -> None:
        self.gateway = gateway

    def session_expiry(self, token: str) -> int:
        context = self.gateway.object(
            "POST",
            "/rest/v1/rpc/session_context",
            payload={},
            access_token=token,
        )
        active, expires = context.get("active"), context.get("expires_at")
        if type(active) is not bool:
            raise unavailable()
        if active is False:
            raise unauthenticated()
        if type(expires) is not int:
            raise unavailable()
        if expires <= int(time.time()):
            raise unauthenticated()
        return expires

    def ensure_rows(self, identity: VerifiedIdentity, token: str) -> None:
        for table, column in (("profiles", "id"), ("user_settings", "user_id")):
            self.gateway.request(
                "POST",
                f"/rest/v1/{table}",
                payload={column: str(identity.user_id)},
                access_token=token,
                params={"on_conflict": column},
                prefer="resolution=ignore-duplicates,return=minimal",
            )

    def _row(
        self,
        table: str,
        column: str,
        columns: str,
        identity: VerifiedIdentity,
        token: str,
        changes: dict[str, object] | None,
    ) -> object:
        result = self.gateway.request(
            "GET" if changes is None else "PATCH",
            f"/rest/v1/{table}",
            payload=changes,
            access_token=token,
            params={column: f"eq.{identity.user_id}", "select": columns},
            prefer="return=representation" if changes is not None else None,
        )
        if not isinstance(result, list) or len(result) != 1:
            raise unavailable()
        return result[0]

    def profile(
        self,
        identity: VerifiedIdentity,
        token: str,
        changes: dict[str, object] | None = None,
    ) -> Profile:
        row = self._row(
            "profiles",
            "id",
            "id,display_name,created_at,updated_at",
            identity,
            token,
            changes,
        )
        try:
            profile = Profile.model_validate(row)
            if profile.id != identity.user_id:
                raise unavailable()
            return profile
        except ValidationError:
            raise unavailable() from None

    def settings(
        self,
        identity: VerifiedIdentity,
        token: str,
        changes: dict[str, object] | None = None,
    ) -> UserSettings:
        row = self._row(
            "user_settings",
            "user_id",
            "user_id,preferred_language,assistant_language,timezone,created_at,updated_at",
            identity,
            token,
            changes,
        )
        try:
            settings = UserSettings.model_validate(row)
            if settings.user_id != identity.user_id:
                raise unavailable()
            return settings
        except ValidationError:
            raise unavailable() from None
