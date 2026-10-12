"""Offline Linux template checks against synthetic files and a loopback-only stub.

No installation, real credentials, DNS lookup, Supabase or provider requests.
Requires nginx, openssl and systemd-analyze on the disposable verification runner.
"""

import http.client
import json
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    for tool in ("nginx", "openssl", "systemd-analyze"):
        if not shutil.which(tool):
            raise SystemExit(f"Required Linux verification tool unavailable: {tool}")
    with tempfile.TemporaryDirectory(prefix="sl-deploy-check-") as directory:
        root = Path(directory)
        frontend = root / "frontend"
        frontend.mkdir()
        (frontend / "index.html").write_text("synthetic SPA", encoding="utf-8")
        (frontend / "assets").mkdir()
        (frontend / "assets/app.js").write_text("/* synthetic asset */", encoding="utf-8")
        (frontend / ".env").write_text("synthetic-private-file", encoding="utf-8")
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-subj",
                "/CN=staging.invalid",
                "-keyout",
                str(root / "key.pem"),
                "-out",
                str(root / "cert.pem"),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        requests: list[dict[str, object]] = []

        class Stub(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                requests.append({"path": self.path, "headers": dict(self.headers)})
                self.send_response(200 if self.path == "/health" else 404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"synthetic"}')

            def do_PUT(self) -> None:
                data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                requests.append({"method": "PUT", "path": self.path, "bytes": len(data)})
                self.send_response(503 if self.path == "/synthetic-failure" else 200)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                pass

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        sockets = [socket.socket(), socket.socket()]
        for listener in sockets:
            listener.bind(("127.0.0.1", 0))
        http_port, https_port = [listener.getsockname()[1] for listener in sockets]
        for listener in sockets:
            listener.close()
        replacements = {
            "STAGING_HOSTNAME": "staging.invalid",
            "TLS_CERTIFICATE_FILE": str(root / "cert.pem"),
            "TLS_PRIVATE_KEY_FILE": str(root / "key.pem"),
            "/opt/swasthyalens/current/frontend/dist": str(frontend),
            "/etc/nginx/snippets/swasthyalens-security.conf": str(root / "headers.conf"),
            "/etc/nginx/snippets/swasthyalens-api.conf": str(root / "api.conf"),
            "http://127.0.0.1:8000/": f"http://127.0.0.1:{upstream.server_port}/",
            "listen 80": f"listen 127.0.0.1:{http_port}",
            "listen 443": f"listen 127.0.0.1:{https_port}",
        }

        def render(name: str) -> str:
            value = (repo / "deploy/nginx" / name).read_text(encoding="utf-8")
            # Test IPv4 loopback only; production template retains both IP families.
            value = "\n".join(line for line in value.splitlines() if "listen [::]" not in line)
            for old, new in replacements.items():
                value = value.replace(old, new)
            return value

        (root / "headers.conf").write_text(render("security-headers.conf"), encoding="utf-8")
        (root / "api.conf").write_text(render("api-location.conf"), encoding="utf-8")
        config = root / "nginx.conf"
        config.write_text(
            f"pid {root}/nginx.pid;\nerror_log /dev/null crit;\nevents {{}}\nhttp {{\n"
            f"client_body_temp_path {root}/body;\nproxy_temp_path {root}/proxy;\n"
            + render("staging.conf.template")
            + "\n}\n",
            encoding="utf-8",
        )
        subprocess.run(["nginx", "-t", "-p", str(root), "-c", str(config)], check=True)
        unit = (repo / "deploy/systemd/swasthyalens.service").read_text(encoding="utf-8")
        # Validate unit directives without requiring deployment paths to exist on CI.
        unit = unit.replace(
            "/opt/swasthyalens/current/backend/.venv/bin/python", "/usr/bin/python3"
        )
        (root / "swasthyalens.service").write_text(unit, encoding="utf-8")
        subprocess.run(
            ["systemd-analyze", "verify", str(root / "swasthyalens.service")], check=True
        )
        nginx = subprocess.Popen(
            ["nginx", "-p", str(root), "-c", str(config), "-g", "daemon off; master_process off;"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        def get(
            path: str,
            headers: dict[str, str] | None = None,
            method: str = "GET",
            body: bytes | None = None,
        ) -> tuple[int, dict[str, str], bytes]:
            # Synthetic self-signed certificate only; never used by the application.
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(
                "staging.invalid", https_port, context=context, timeout=5
            )
            conn._create_connection = lambda *a, **k: socket.create_connection(
                ("127.0.0.1", https_port), 5
            )
            try:
                conn.request(method, path, body=body, headers=headers or {})
                response = conn.getresponse()
                return response.status, dict(response.getheaders()), response.read()
            finally:
                conn.close()

        try:
            for _ in range(50):
                if nginx.poll() is not None:
                    raise RuntimeError("Synthetic Nginx exited before verification")
                try:
                    with socket.create_connection(("127.0.0.1", https_port), 0.1):
                        break
                except OSError:
                    time.sleep(0.1)
            status, response_headers, body = get("/auth/sign-in")
            assert status == 200 and body == b"synthetic SPA"
            assert response_headers["Cache-Control"] == "no-store"
            assert response_headers["Strict-Transport-Security"] == "max-age=31536000"
            assert "frame-ancestors 'none'" in response_headers["Content-Security-Policy"]
            before = len(requests)
            try:
                get("/api/health", {"Host": "forged.invalid"})
            except http.client.RemoteDisconnected:
                pass  # Nginx 444 closes the connection without an HTTP response.
            else:
                raise AssertionError("Unexpected Host was not rejected with a closed connection")
            assert len(requests) == before
            status, response_headers, _ = get(
                "/api/health",
                {
                    "Authorization": "synthetic-never-forward",
                    "X-Forwarded-Host": "forged.invalid",
                    "Forwarded": "for=192.0.2.1;proto=https;host=forged.invalid",
                    "X-Forwarded-For": "192.0.2.1",
                    "X-Forwarded-Proto": "https",
                    "X-Real-IP": "192.0.2.1",
                    "X-Request-ID": "synthetic-forged-id",
                    "Cookie": "synthetic-cookie",
                    "X-CSRF-Token": "synthetic-csrf",
                    "Origin": "https://staging.invalid",
                },
            )
            assert status == 200 and requests[-1]["path"] == "/health"
            forwarded = {k.lower(): v for k, v in requests[-1]["headers"].items()}
            assert forwarded["host"] == "staging.invalid"
            assert forwarded["cookie"] == "synthetic-cookie"
            assert forwarded["x-csrf-token"] == "synthetic-csrf"
            assert forwarded["origin"] == "https://staging.invalid"
            assert (
                not {
                    "authorization",
                    "forwarded",
                    "x-forwarded-host",
                    "x-forwarded-for",
                    "x-forwarded-proto",
                    "x-real-ip",
                    "x-request-id",
                }
                & forwarded.keys()
            )
            assert "script-src" not in response_headers["Content-Security-Policy"]
            assert response_headers["Cache-Control"] == "no-store"
            for path in (
                "/.env",
                "/assets/missing.js",
                "/api",
                "/api/missing",
                "/security-headers.json",
            ):
                status, response_headers, body = get(path)
                assert status == 404 and b"synthetic SPA" not in body
                assert response_headers["X-Content-Type-Options"] == "nosniff"
                assert response_headers["Cache-Control"] == "no-store"
                assert response_headers["X-Frame-Options"] == "DENY"
            before = len(requests)
            status, response_headers, body = get("/auth/sign-in", method="POST", body=b"")
            assert status == 403 and b"synthetic SPA" not in body
            assert response_headers["Cache-Control"] == "no-store"
            assert len(requests) == before
            # Stub acceptance tests gateway allowance only, not the application's 5 MiB limit.
            for size in (5_242_880, 6_291_456):
                assert get("/api/reports/synthetic/file", method="PUT", body=b"x" * size)[0] == 200
                assert requests[-1] == {
                    "method": "PUT",
                    "path": "/reports/synthetic/file",
                    "bytes": size,
                }
            # Expect prevents sending a rejected body, avoiding client broken-pipe races.
            before = len(requests)
            assert (
                get(
                    "/api/reports/synthetic/file",
                    method="PUT",
                    headers={"Content-Length": str(6 * 1024 * 1024 + 1), "Expect": "100-continue"},
                )[0]
                == 413
            )
            assert len(requests) == before
            # One observed dispatch plus the explicit policy; not a multi-node failover test.
            assert "proxy_next_upstream off;" in render("api-location.conf").splitlines()
            before = len(requests)
            status, response_headers, _ = get("/api/synthetic-failure", method="PUT", body=b"x")
            assert status == 503 and len(requests) == before + 1
            assert requests[-1] == {"method": "PUT", "path": "/synthetic-failure", "bytes": 1}
            assert response_headers["Cache-Control"] == "no-store"
            assert response_headers["X-Content-Type-Options"] == "nosniff"
            assert response_headers["Content-Security-Policy"].startswith("default-src 'none'")
            plain = http.client.HTTPConnection("127.0.0.1", http_port, timeout=5)
            try:
                plain.request(
                    "GET", "/private?token=synthetic", headers={"Host": "staging.invalid"}
                )
                redirected = plain.getresponse()
                assert redirected.status == 308
                assert redirected.getheader("Location") == "https://staging.invalid/"
                redirected.read()
            finally:
                plain.close()
            print(
                json.dumps(
                    {
                        "nginx_syntax": "PASS",
                        "systemd_syntax": "PASS",
                        "synthetic_loopback_gateway": "PASS",
                        "deployed_acceptance": "PENDING",
                    }
                )
            )
        finally:
            nginx.terminate()
            nginx.wait(timeout=10)
            upstream.shutdown()
            upstream.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
