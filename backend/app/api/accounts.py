"""Owned profile/settings routes deliberately accept no target-user identifier."""

from fastapi import APIRouter, Depends

from app.api.dependencies import Auth, CurrentUser, protect_write
from app.core.errors import ApiProblem
from app.schemas.accounts import Profile, ProfilePatch, SettingsPatch, UserSettings

router = APIRouter(tags=["Account"])


@router.get("/profile", response_model=Profile)
def profile(current: CurrentUser, auth: Auth) -> Profile:
    return auth.accounts.profile(current.identity, current.access_token)


@router.patch("/profile", response_model=Profile, dependencies=[Depends(protect_write)])
def update_profile(body: ProfilePatch, current: CurrentUser, auth: Auth) -> Profile:
    if not body.model_fields_set:
        raise ApiProblem(422, "validation_error", "Provide at least one field to update.")
    return auth.accounts.profile(
        current.identity,
        current.access_token,
        body.model_dump(exclude_unset=True),
    )


@router.get("/settings", response_model=UserSettings)
def settings(current: CurrentUser, auth: Auth) -> UserSettings:
    return auth.accounts.settings(current.identity, current.access_token)


@router.patch("/settings", response_model=UserSettings, dependencies=[Depends(protect_write)])
def update_settings(body: SettingsPatch, current: CurrentUser, auth: Auth) -> UserSettings:
    if not body.model_fields_set:
        raise ApiProblem(422, "validation_error", "Provide at least one field to update.")
    return auth.accounts.settings(
        current.identity,
        current.access_token,
        body.model_dump(exclude_unset=True),
    )
