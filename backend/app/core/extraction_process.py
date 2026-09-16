"""Credential-free parser child. Invoked only with generated paths/configuration."""

import csv
import hashlib
import io
import json
import math
import sys
import unicodedata
import warnings
from contextlib import closing
from pathlib import Path
from typing import Literal

from app.core.extraction_limits import contain_memory
from app.schemas.extraction import Span

MAX_PIXELS = 12_000_000


class ExtractionFailure(Exception):
    pass


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    return "".join(c for c in text if c in "\n\t" or unicodedata.category(c) not in {"Cc", "Cs"})


def dimensions(width: float, height: float) -> None:
    if not all(math.isfinite(v) and 0 < v <= 10000 for v in (width, height)):
        raise ExtractionFailure("resource_limit_exceeded")
    if width * height > MAX_PIXELS:
        raise ExtractionFailure("resource_limit_exceeded")


def parse_tsv(tsv: str, width: int, height: int) -> tuple[str, list[Span]]:
    """Validate the engine boundary before accepting any machine-derived text."""
    if len(tsv.encode()) > 750000:
        raise ExtractionFailure("resource_limit_exceeded")
    spans: list[Span] = []
    lines: dict[tuple[str, str, str], list[str]] = {}
    header = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
        "left\ttop\twidth\theight\tconf\ttext\n"
    )
    try:
        for row in csv.DictReader(
            io.StringIO(header + tsv), delimiter="\t", quoting=csv.QUOTE_NONE
        ):
            if None in row or any(value is None for value in row.values()):
                raise ValueError
            if row["level"] not in {"1", "2", "3", "4", "5"}:
                raise ValueError
            if row["level"] != "5" or not row["text"].strip():
                continue
            text = normalize(row["text"])
            x, y, w, h = (int(row[key]) for key in ("left", "top", "width", "height"))
            if min(x, y, w, h) < 0 or x + w > width or y + h > height:
                raise ValueError
            score = float(row["conf"])
            spans.append(Span(text=text, bbox=(x, y, x + w, y + h), confidence=score))
            if len(spans) > 2000:
                raise ExtractionFailure("resource_limit_exceeded")
            key = (row["block_num"], row["par_num"], row["line_num"])
            lines.setdefault(key, []).append(text)
        text = "\n".join(" ".join(line) for line in lines.values())
        if len(text) > 20000:
            raise ExtractionFailure("resource_limit_exceeded")
        return text, spans
    except (KeyError, TypeError, ValueError):
        raise ExtractionFailure("ocr_failure") from None


def main() -> None:
    # No settings, provider client or application secrets are loaded in this process.
    containment = contain_memory()
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    warnings.simplefilter("error", Image.DecompressionBombWarning)
    from app.schemas.extraction import ExtractedPage, ExtractionOutput

    source, destination, config_file = map(Path, sys.argv[1:])
    config = json.loads(config_file.read_text(encoding="utf-8"))
    model_path = config["models"]
    engine = "not_used"
    model_hashes: dict[str, str | int] = {
        "languages": "eng+hin",
        "dpi": 250,
        "strategy": "native-first-v1",
        "orientation_min_score": 8,
        "max_pages": config["max_pages"],
    }

    def ocr(image: Image.Image, number: int) -> ExtractedPage:
        nonlocal engine
        dimensions(*image.size)
        try:
            import tesserocr
        except (ImportError, OSError):
            raise ExtractionFailure("ocr_unavailable") from None
        if engine == "not_used":
            engine = str(tesserocr.tesseract_version()).splitlines()[0][:100]
            # Deployment must explicitly provide all models; hashes version actual artifacts.
            if not model_path:
                raise ExtractionFailure("ocr_unavailable")
            for lang in ("eng", "hin", "osd"):
                model = Path(model_path) / f"{lang}.traineddata"
                if not model.is_file():
                    raise ExtractionFailure("ocr_unavailable")
                model_hashes[f"{lang}_sha256"] = hashlib.sha256(model.read_bytes()).hexdigest()
        rotation = 0
        page_warnings: list[
            Literal["no_text", "orientation_uncertain", "layout_requires_review"]
        ] = ["layout_requires_review"]
        try:
            with tesserocr.PyTessBaseAPI(
                path=model_path, lang="osd", psm=tesserocr.PSM.OSD_ONLY
            ) as api:
                api.SetImage(image)
                orientation = api.DetectOrientationScript()
            if orientation and orientation["orient_conf"] >= 8:
                rotation = (-int(orientation["orient_deg"])) % 360
                image = image.rotate(-rotation, expand=True)
            if not orientation or orientation["orient_conf"] < 15:
                page_warnings.append("orientation_uncertain")
            with tesserocr.PyTessBaseAPI(
                path=model_path, lang="eng+hin", psm=tesserocr.PSM.AUTO, oem=tesserocr.OEM.LSTM_ONLY
            ) as api:
                api.SetImage(image)
                if not api.Recognize(timeout=30000):
                    raise ExtractionFailure("timeout")
                tsv = str(api.GetTSVText(0))
        except RuntimeError:
            raise ExtractionFailure("ocr_failure") from None
        text, spans = parse_tsv(tsv, image.width, image.height)
        try:
            if not text:
                page_warnings.append("no_text")
            return ExtractedPage(
                page_number=number,
                text=text,
                method="ocr",
                width=image.width,
                height=image.height,
                coordinate_system="oriented_pixels_top_left",
                rotation=rotation,
                confidence=sum(s.confidence or 0 for s in spans) / len(spans) if spans else None,
                warnings=page_warnings,
                spans=spans,
            )
        except (KeyError, TypeError, ValueError):
            raise ExtractionFailure("ocr_failure") from None

    pages = []
    if config["media_type"] == "application/pdf":
        try:
            document = pdfium.PdfDocument(source)
        except pdfium.PdfiumError as error:
            raise ExtractionFailure(
                "encrypted_document" if error.err_code == 4 else "corrupt_document"
            ) from None
        with document:
            if raw.FPDF_GetSecurityHandlerRevision(document) >= 0:
                raise ExtractionFailure("encrypted_document")
            if len(document) == 0:
                raise ExtractionFailure("corrupt_document")
            if len(document) > config["max_pages"]:
                raise ExtractionFailure("page_limit_exceeded")
            for index in range(len(document)):
                with closing(document[index]) as page:
                    width, height = page.get_size()
                    if not all(math.isfinite(v) and 0 < v <= 1440 for v in (width, height)):
                        raise ExtractionFailure("resource_limit_exceeded")
                    with closing(page.get_textpage()) as textpage:
                        if textpage.count_chars() > 20000:
                            raise ExtractionFailure("resource_limit_exceeded")
                        text = normalize(textpage.get_text_range())
                        meaningful = sum(c.isalnum() for c in text)
                        usable = meaningful >= 24 and text.count("\ufffd") <= max(
                            1, len(text) // 100
                        )
                        # Large raster content with only a small header is not a native page.
                        image_area = 0.0
                        for obj in page.get_objects(filter=[raw.FPDF_PAGEOBJ_IMAGE]):
                            left, bottom, right, top = obj.get_bounds()
                            image_area += abs((right - left) * (top - bottom))
                        if image_area > width * height * 0.5 and meaningful < 200:
                            usable = False
                        if usable:
                            spans = []
                            count = textpage.count_rects()
                            if count > 2000:
                                raise ExtractionFailure("resource_limit_exceeded")
                            for rect in range(count):
                                bounds = textpage.get_rect(rect)
                                spans.append(
                                    Span(
                                        text=normalize(textpage.get_text_bounded(*bounds)),
                                        bbox=bounds,
                                    )
                                )
                            pages.append(
                                ExtractedPage(
                                    page_number=index + 1,
                                    text=text,
                                    method="native_text",
                                    width=width,
                                    height=height,
                                    coordinate_system="pdf_points_bottom_left",
                                    rotation=page.get_rotation(),
                                    warnings=["layout_requires_review"],
                                    spans=spans,
                                )
                            )
                            continue
                    scale = 250 / 72
                    dimensions(math.ceil(width * scale), math.ceil(height * scale))
                    with closing(
                        page.render(scale=scale, may_draw_forms=False, draw_annots=False)
                    ) as bitmap:
                        pages.append(ocr(bitmap.to_pil(), index + 1))
    else:
        try:
            with Image.open(source) as image:
                if image.format not in {"PNG", "JPEG"} or getattr(image, "n_frames", 1) != 1:
                    raise ExtractionFailure("unsupported_document")
                dimensions(*image.size)
                image.load()
                oriented = ImageOps.exif_transpose(image)
                # Composite transparency on white without changing source bytes.
                rgba = oriented.convert("RGBA")
                canvas = Image.new("RGBA", rgba.size, "white")
                canvas.alpha_composite(rgba)
                prepared = canvas.convert("RGB")
                # Evaluated on the synthetic image set; enlarge only within the pixel cap.
                scale = 2 if prepared.width * prepared.height <= MAX_PIXELS // 4 else 1
                if scale == 2:
                    prepared = prepared.resize(
                        (prepared.width * 2, prepared.height * 2), Image.Resampling.BICUBIC
                    )
                pages.append(ocr(prepared, 1))
                model_hashes["image_scale"] = scale
                model_hashes["image_resampling"] = "bicubic" if scale == 2 else "none"
                model_hashes["image_orientation"] = "EXIF transpose before OCR"
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise ExtractionFailure("resource_limit_exceeded") from None
        except (OSError, ValueError):
            raise ExtractionFailure("corrupt_document") from None
    result = ExtractionOutput(
        processor=(
            f"native-first-v1; pypdfium2 {pdfium.PYPDFIUM_INFO.version}; "
            f"PDFium {pdfium.PDFIUM_INFO.version}; {engine}"
        ),
        configuration=model_hashes,
        pages=pages,
    )
    encoded = result.model_dump_json()
    if len(encoded.encode()) > 750000:
        raise ExtractionFailure("resource_limit_exceeded")
    destination.write_text(encoded, encoding="utf-8")
    _ = containment


if __name__ == "__main__":
    try:
        main()
    except ExtractionFailure as error:
        Path(sys.argv[2]).write_text(json.dumps({"failure": str(error)}), encoding="utf-8")
    except MemoryError:
        Path(sys.argv[2]).write_text('{"failure":"resource_limit_exceeded"}', encoding="utf-8")
    except Exception:
        Path(sys.argv[2]).write_text('{"failure":"extractor_failure"}', encoding="utf-8")
