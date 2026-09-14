"""Public errors contain no provider responses or submitted values."""

from dataclasses import dataclass


@dataclass
class ApiProblem(Exception):
    status: int
    code: str
    message: str
    clear_session: bool = False


def unauthenticated() -> ApiProblem:
    return ApiProblem(401, "unauthenticated", "Please sign in again.", clear_session=True)


def unavailable() -> ApiProblem:
    return ApiProblem(503, "service_unavailable", "The account service is temporarily unavailable.")
