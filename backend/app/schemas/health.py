"""Response schema for the API liveness check."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    status: Literal["ok"]
    service: Literal["swasthyalens-api"]
