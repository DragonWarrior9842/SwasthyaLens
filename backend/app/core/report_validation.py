"""Conservative upload checks; document bytes are never instructions or executable input."""

import re
import struct
import unicodedata
import zlib

MEDIA_EXTENSIONS = {
    "application/pdf": frozenset({"pdf"}),
    "image/jpeg": frozenset({"jpg", "jpeg"}),
    "image/png": frozenset({"png"}),
}
ALLOWED_MEDIA_TYPES = frozenset(MEDIA_EXTENSIONS)


def safe_filename(value: str) -> str:
    name = unicodedata.normalize("NFC", value)
    if (
        not name
        or name != name.strip()
        or len(name) > 120
        or len(name.encode("utf-8")) > 240
        or name.startswith(".")
        or name.endswith((".", " "))
        or any(character in '/\\:*?"<>|' for character in name)
        or any(unicodedata.category(character).startswith("C") for character in name)
        or ".." in name
    ):
        raise ValueError("Use a short filename without paths or control characters")
    stem, separator, extension = name.rpartition(".")
    if (
        not separator
        or not stem.strip()
        or extension.lower() not in {"pdf", "jpg", "jpeg", "png"}
        or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])", stem.split(".")[0])
    ):
        raise ValueError("Use a PDF, JPEG or PNG filename")
    return name


def validate_file(data: bytes, media_type: str, filename: str, expected_size: int) -> None:
    """Check type agreement and bounded container structure, without extracting any content.

    These checks do not certify parser safety or replace malware scanning. Preserve the
    original bytes and force attachment downloads; future processing requires isolation.
    """
    if (
        not data
        or len(data) != expected_size
        or media_type not in MEDIA_EXTENSIONS
        or filename.rsplit(".", 1)[-1].lower() not in MEDIA_EXTENSIONS[media_type]
    ):
        raise ValueError("File type or size does not match")
    if media_type == "application/pdf":
        if (
            not re.match(rb"%PDF-(?:1\.[0-7]|2\.0)(?:\r\n|\r|\n)", data)
            or re.search(rb"\b[0-9]+\s+[0-9]+\s+obj\b", data) is None
            or re.search(rb"startxref\s+[0-9]+\s+%%EOF\s*\Z", data[-2048:]) is None
        ):
            raise ValueError("File does not have a supported PDF container")
    elif media_type == "image/png":
        _validate_png(data)
    elif media_type == "image/jpeg":
        _validate_jpeg(data)


def _validate_png(data: bytes) -> None:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Invalid PNG signature")
    offset, chunks, image_data = 8, 0, False
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("Incomplete PNG chunk")
        size = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4 : offset + 8]
        end = offset + 12 + size
        if end > len(data) or not re.fullmatch(rb"[A-Za-z]{4}", kind):
            raise ValueError("Invalid PNG chunk")
        payload = data[offset + 8 : end - 4]
        checksum = struct.unpack_from(">I", data, end - 4)[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != checksum:
            raise ValueError("Invalid PNG checksum")
        if chunks == 0:
            if kind != b"IHDR" or size != 13:
                raise ValueError("Missing PNG header")
            width, height = struct.unpack_from(">II", payload)
            if not 0 < width <= 50_000 or not 0 < height <= 50_000:
                raise ValueError("Invalid PNG dimensions")
        elif kind == b"IHDR":
            raise ValueError("Duplicate PNG header")
        if kind == b"IDAT" and size:
            image_data = True
        if kind == b"IEND":
            if size != 0 or end != len(data) or not image_data:
                raise ValueError("Invalid PNG end")
            return
        offset = end
        chunks += 1
    raise ValueError("Missing PNG end")


def _validate_jpeg(data: bytes) -> None:
    if not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        raise ValueError("Invalid JPEG signature")
    offset, frame = 2, False
    while offset < len(data) - 2:
        if data[offset] != 0xFF:
            raise ValueError("Invalid JPEG marker")
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset + 3 > len(data):
            raise ValueError("Incomplete JPEG marker")
        marker = data[offset]
        offset += 1
        size = int.from_bytes(data[offset : offset + 2], "big")
        if size < 2 or offset + size > len(data) - 2:
            raise ValueError("Invalid JPEG segment")
        if marker in {0xC0, 0xC1, 0xC2}:
            if (
                size < 8
                or not any(data[offset + 3 : offset + 5])
                or not any(data[offset + 5 : offset + 7])
            ):
                raise ValueError("Invalid JPEG frame")
            frame = True
        if marker == 0xDA:
            if not frame or offset + size >= len(data) - 2:
                raise ValueError("Missing JPEG image data")
            return
        offset += size
    raise ValueError("Missing JPEG scan")
