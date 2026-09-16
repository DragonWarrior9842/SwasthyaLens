"""Explicit operator setup, never invoked by the application or on uploaded data."""

import argparse
import hashlib
import urllib.request
from pathlib import Path

REVISION = "e12c65a915945e4c28e237a9b52bc4a8f39a0cec"
OSD_REVISION = "87416418657359cb625c412a48b6e1d6d41c29bd"
HASHES = {
    "eng": "8280aed0782fe27257a68ea10fe7ef324ca0f8d85bd2fd145d1c2b560bcb66ba",
    "hin": "bd2e65a2184af08a167b0be2439e91fa5edbc4394399ca2f692b843ae26e78d6",
    "osd": "9cf5d576fcc47564f11265841e5ca839001e7e6f38ff7f7aacf46d15a96b00ff",
}

parser = argparse.ArgumentParser(description="Download fixed-revision public OCR models")
parser.add_argument("directory", type=Path)
args = parser.parse_args()
args.directory.mkdir(parents=True, exist_ok=True)
for language, expected in HASHES.items():
    target = args.directory / f"{language}.traineddata"
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        continue
    repository, revision = (
        ("tessdata_fast", OSD_REVISION) if language == "osd" else ("tessdata_best", REVISION)
    )
    url = f"https://raw.githubusercontent.com/tesseract-ocr/{repository}/{revision}/{language}.traineddata"
    with urllib.request.urlopen(url, timeout=30) as response:
        content = response.read(20_000_001)
    if len(content) > 20_000_000 or hashlib.sha256(content).hexdigest() != expected:
        raise RuntimeError("Model integrity verification failed")
    target.write_bytes(content)
print("English, Hindi and orientation model hashes verified.")
