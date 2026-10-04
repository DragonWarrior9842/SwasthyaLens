"""Keep the direct Windows OCR wheel restricted to its URL-fragment SHA-256.

uv's universal resolution can merge the same-version PyPI platform hashes into
the direct Windows requirement. Its artifact must retain its own hash instead.
Run after compiling BOTH locks; no network or configuration files are read.
"""

import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for name in ("requirements.lock", "requirements-dev.lock"):
    path = root / name
    content = path.read_text(encoding="utf-8")
    pattern = (
        r"(tesserocr @ https://[^\n]+#sha256=([a-f0-9]{64})[^\n]+ \\\n)(?:    --hash=[^\n]+\n)+"
    )
    result, count = re.subn(
        pattern, lambda match: match[1] + f"    --hash=sha256:{match[2]}\n", content
    )
    if count != 1:
        raise RuntimeError("Expected exactly one hash-pinned Windows OCR wheel per lock")
    path.write_text(result, encoding="utf-8")
print("Direct Windows OCR artifact hashes preserved in both locks.")
