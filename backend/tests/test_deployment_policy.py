"""Gateway headers must stay aligned with the frontend build and live ASGI policy."""

import ast
import re
import shlex
from configparser import ConfigParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.factory import create_app
from tests.test_release_security import release_settings

ROOT = Path(__file__).resolve().parents[2]


def test_systemd_service_security_contract() -> None:
    """Assert the declared policy only; this does not start a service or enforce cgroups."""
    unit = ConfigParser(interpolation=None)
    unit.read(ROOT / "deploy/systemd/swasthyalens.service", encoding="utf-8")
    service = unit["Service"]
    assert service["User"] == service["Group"] == "swasthyalens"
    command = shlex.split(service["ExecStart"])
    assert command == [
        "/opt/swasthyalens/current/backend/.venv/bin/python",
        "-m",
        "uvicorn",
        "app.release:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--workers",
        "1",
        "--no-access-log",
        "--no-proxy-headers",
        "--no-server-header",
    ]
    for key, value in {
        "NoNewPrivileges": "true",
        "CapabilityBoundingSet": "",
        "AmbientCapabilities": "",
        "ProtectSystem": "strict",
        "ProtectHome": "true",
        "ReadWritePaths": "/tmp",
        "InaccessiblePaths": "/etc/swasthyalens",
        "UMask": "0077",
        "MemoryMax": "2560M",
        "CPUQuota": "200%",
        "TasksMax": "64",
        "LimitNOFILE": "1024",
        "LimitCORE": "0",
        "KillMode": "control-group",
        "TimeoutStopSec": "135",
        "Restart": "on-failure",
        "RestartSec": "5",
    }.items():
        assert service[key] == value, key
    assert shlex.split(service["TemporaryFileSystem"]) == [
        "/tmp:rw,nosuid,nodev,noexec,size=256M,mode=1777",
        "/var/tmp:ro",
    ]
    assert unit["Unit"]["StartLimitIntervalSec"] == "300"
    assert unit["Unit"]["StartLimitBurst"] == "3"


def nginx_headers(name: str) -> dict[str, str]:
    result = {}
    for line in (ROOT / "deploy/nginx" / name).read_text(encoding="utf-8").splitlines():
        if line.startswith("add_header "):
            command, key, value, always = shlex.split(line.removesuffix(";"))
            assert command == "add_header" and always == "always"
            result[key.lower()] = value
    return result


def test_gateway_preserves_frontend_build_policy() -> None:
    source = (ROOT / "frontend/vite.config.ts").read_text(encoding="utf-8")
    headers = nginx_headers("security-headers.conf")
    fields = re.findall(r"^  '([\w-]+)': (.+),$", source, re.MULTILINE)
    assert fields
    for key, literal in fields:
        assert headers[key.lower()] == ast.literal_eval(literal)
    assert headers["cache-control"] == "no-store"


@pytest.mark.usefixtures("isolate_release_flags")
def test_gateway_preserves_api_policy_including_error_responses() -> None:
    settings = release_settings()
    expected = nginx_headers("api-location.conf")
    with TestClient(create_app(settings), base_url=settings.app_origin) as client:
        for path in ("/health", "/missing"):
            response = client.get(path)
            for key, value in expected.items():
                assert response.headers[key] == value
