"""Reproducible synthetic OCR fixtures, never application demo health data."""

import io
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LINES = [
    "SYNTHETIC TEST DOCUMENT - NOT A PATIENT REPORT",
    "Text extraction evaluation. Preserve source numbers and units.",
    "Sample label         Result         Unit",
    "Sample Alpha         13.2           g/dL",
    "Sample Beta          18             ng/mL",
    "Sample Gamma         2.4            mIU/L",
    "Sample Delta         13.2           mg/dL",
    "The original document remains authoritative.",
    "No interpretation or clinical classification is requested.",
]
TOKENS = ["13.2", "18", "2.4", "mg/dL", "g/dL", "ng/mL", "mIU/L"]


def scan(*, rotated: bool = False, hindi_font: str | None = None) -> Image.Image:
    image = Image.new("RGB", (1800, 1500), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=34)
    for index, line in enumerate(LINES):
        draw.text((80, 100 + index * 110), line, font=font, fill="black")
    if hindi_font:
        from PIL import features

        if not features.check_feature("raqm"):
            raise RuntimeError(
                "Hindi generation requires RAQM; omit --hindi-font to use the shaped fixture"
            )
        draw.text(
            (80, 1190), "हिंदी परीक्षण रिपोर्ट", font=ImageFont.truetype(hindi_font, 48), fill="black"
        )
        draw.text(
            (80, 1300), "नमूना 13.2 g/dL", font=ImageFont.truetype(hindi_font, 48), fill="black"
        )
    return image.rotate(90, expand=True) if rotated else image


def image_bytes(
    format: str = "PNG", *, rotated: bool = False, hindi_font: str | None = None
) -> bytes:
    stream = io.BytesIO()
    scan(rotated=rotated, hindi_font=hindi_font).save(stream, format=format)
    return stream.getvalue()


def document(kinds: tuple[str, ...] = ("native",), size: int = 600) -> bytes:
    objects: list[bytes] = [b"", b""]

    def add(value: bytes) -> int:
        objects.append(value)
        return len(objects)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    children = []
    for number, kind in enumerate(kinds, 1):
        resource = f"/Font << /F1 {font} 0 R >>"
        if kind == "scan":
            jpeg = image_bytes("JPEG")
            image = add(
                (
                    "<< /Type /XObject /Subtype /Image /Width 1800 /Height 1500 "
                    "/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
                    f"/Length {len(jpeg)} >>\nstream\n"
                ).encode()
                + jpeg
                + b"\nendstream"
            )
            content = b"q 540 0 0 450 30 280 cm /Im0 Do Q"
            resource += f" /XObject << /Im0 {image} 0 R >>"
        elif kind == "blank":
            content = b""
        else:
            lines = [*LINES, f"Source page {number}"]
            content = (
                "BT /F1 12 Tf 36 750 Td 32 TL "
                + " ".join(f"({line}) Tj T*" for line in lines)
                + " ET"
            ).encode()
        stream = add(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
        page = add(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {size} 800] "
                f"/Resources << {resource} >> /Contents {stream} 0 R >>"
            ).encode()
        )
        children.append(page)
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{page} 0 R' for page in children)}] "
        f"/Count {len(children)} >>"
    ).encode()
    data = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(data)


def write_fixtures(root: Path, hindi_font: str | None = None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, kinds in {
        "native": ("native",),
        "scanned": ("scan",),
        "mixed": ("native", "scan"),
        "multipage": ("native", "native"),
        "blank": ("blank",),
        "zero-page": (),
        "too-many-pages": ("native",) * 21,
    }.items():
        (root / f"{name}.pdf").write_bytes(document(kinds))
    (root / "corrupt.pdf").write_bytes(document().replace(b"/Type /Catalog", b"/Type /Invalid"))
    for ext in ("PNG", "JPEG"):
        (root / f"english.{ext.lower()}").write_bytes(image_bytes(ext))
    (root / "rotated.png").write_bytes(image_bytes(rotated=True))
    if hindi_font:
        (root / "hindi-mixed.png").write_bytes(image_bytes(hindi_font=hindi_font))
    else:
        # Browser-shaped Devanagari fixture; Pillow builds without RAQM cannot shape it.
        shutil.copyfile(
            Path(__file__).parent / "fixtures" / "hindi-mixed.png", root / "hindi-mixed.png"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--hindi-font")
    args = parser.parse_args()
    write_fixtures(args.output, args.hindi_font)
