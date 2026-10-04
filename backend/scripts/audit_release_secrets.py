"""Read-only finite-pattern/known-local-secret scan. Never prints matched contents.

Inspects tracked working files, reachable Git blobs, and the default release build.
Local configuration is read only to compare secret bytes, never copied to output.
This is not a substitute for manual review or a complete secret-detection service.
"""

import base64
import json
import re
import subprocess
from pathlib import Path

from dotenv import dotenv_values

root = Path(__file__).resolve().parents[2]
secret_names = {
    "AI_API_KEY",
    "CSRF_SIGNING_KEY",
    "REPORT_PROCESSING_KEY",
    "TEST_USER_A_PASSWORD",
    "TEST_USER_B_PASSWORD",
    "SUPABASE_SERVICE_ROLE_KEY",
}
known = set()
for directory in (root, root / "backend"):
    for path in directory.glob(".env*"):
        if path.is_file() and not path.name.endswith("example"):
            known.update(
                value.encode()
                for key, value in dotenv_values(path).items()
                if key in secret_names and value
            )
patterns = {
    "private-key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "google-key": rb"AIza[0-9A-Za-z_-]{35}",
    "openai-key": rb"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}",
    "supabase-secret": rb"sb_secret_[A-Za-z0-9_-]{30,}",
    "github-token": rb"(?:ghp_|github_pat_)[A-Za-z0-9_]{35,}",
}
findings = set()
alphabet_matches = set()


def check(data: bytes, location: str) -> None:
    for value in known:
        hits = list(re.finditer(re.escape(value), data))
        if not hits:
            continue
        alphabets = [
            match
            for suffix in (b"abcdef", b"ABCDEF")
            for match in re.finditer(re.escape(bytes(range(48, 58)) + suffix), data)
        ]
        # Reviewed false positive: a short test credential matches only substrings
        # of this public algorithm alphabet, never a credential literal/assignment.
        if len(value) < 12 and all(
            any(a.start() <= h.start() and h.end() <= a.end() for a in alphabets) for h in hits
        ):
            alphabet_matches.add(location)
        else:
            findings.add((location, "configured-secret"))
    for category, pattern in patterns.items():
        if re.search(pattern, data):
            findings.add((location, category))
    for token in re.findall(rb"eyJ[A-Za-z0-9_-]+\.([A-Za-z0-9_-]+)\.[A-Za-z0-9_-]+", data):
        try:
            payload = json.loads(base64.urlsafe_b64decode(token + b"=" * (-len(token) % 4)))
            if isinstance(payload, dict) and payload.get("role") == "service_role":
                findings.add((location, "service-role-jwt"))
        except (ValueError, UnicodeError):
            pass


tracked = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
).split(b"\0")
for name in filter(None, tracked):
    path = root / name.decode("utf-8")
    if path.is_file():
        check(path.read_bytes(), "working:" + name.decode("utf-8"))
objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"], cwd=root).splitlines()
process = subprocess.Popen(
    ["git", "cat-file", "--batch"], cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE
)
assert process.stdin is not None and process.stdout is not None
blobs = 0
for line in objects:
    identifier, _, name = line.partition(b" ")
    process.stdin.write(identifier + b"\n")
    process.stdin.flush()
    header = process.stdout.readline().split()
    data = process.stdout.read(int(header[2]))
    process.stdout.read(1)
    if header[1] == b"blob":
        blobs += 1
        check(data, "history:" + name.decode("utf-8", errors="replace"))
process.stdin.close()
if process.wait() != 0:
    raise RuntimeError("Git blob audit did not complete")
bundle = list((root / "frontend/dist").rglob("*"))
for path in bundle:
    if path.is_file():
        check(path.read_bytes(), "bundle:" + str(path.relative_to(root)))
print(
    json.dumps(
        {
            "reachable_blobs": blobs,
            "known_values_compared": len(known),
            "bundle_files": sum(p.is_file() for p in bundle),
            "reviewed_public_alphabet_matches": len(alphabet_matches),
            "findings": [
                {"path": path, "category": category} for path, category in sorted(findings)
            ],
        }
    )
)
raise SystemExit(1 if findings else 0)
