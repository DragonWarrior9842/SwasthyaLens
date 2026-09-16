import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.extraction import ProcessingFailure, extract
from app.core.extraction_process import ExtractionFailure, normalize, parse_tsv
from app.factory import create_app
from tests.auth_support import ProviderFixture, auth_settings
from tests.extraction_fixtures import LINES, TOKENS, document, image_bytes


def test_native_multipage_provenance_without_ocr() -> None:
    result = extract(document(("native", "native")), "application/pdf", auth_settings())
    assert [page.page_number for page in result.pages] == [1, 2]
    for number, page in enumerate(result.pages, 1):
        assert page.method == "native_text" and page.confidence is None
        assert f"Source page {number}" in page.text
        assert all(token in page.text for token in TOKENS)
        assert page.spans and LINES[0] in page.spans[0].text
    assert "not_used" in result.processor


@pytest.mark.parametrize(
    ("data", "category"),
    [
        (b"%PDF-1.4\ninvalid", "corrupt_document"),
        (document(()), "corrupt_document"),
        (document(("native",) * 21), "page_limit_exceeded"),
        (document(size=10000), "resource_limit_exceeded"),
    ],
)
def test_pdf_failures(data: bytes, category: str) -> None:
    with pytest.raises(ProcessingFailure) as error:
        extract(data, "application/pdf", auth_settings())
    assert error.value.category == category


def test_bad_image() -> None:
    with pytest.raises(ProcessingFailure) as error:
        extract(b"invalid", "image/png", auth_settings())
    assert error.value.category == "corrupt_document"


def test_encrypted_pdf_has_explicit_failure() -> None:
    fixture = Path(__file__).parent / "fixtures" / "encrypted.pdf"
    with pytest.raises(ProcessingFailure) as error:
        extract(fixture.read_bytes(), "application/pdf", auth_settings())
    assert error.value.category == "encrypted_document"


def test_timeout_kills_child_and_removes_temporary_source() -> None:
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        with patch("app.core.extraction.subprocess.Popen", return_value=child) as launch:
            with pytest.raises(ProcessingFailure) as error:
                extract(
                    document(),
                    "application/pdf",
                    auth_settings(report_processing_timeout_seconds=5),
                )
        assert error.value.category == "timeout" and child.poll() is not None
        assert not Path(launch.call_args.args[0][3]).parent.exists()
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)


def test_missing_ocr_is_explicit() -> None:
    with pytest.raises(ProcessingFailure) as error:
        extract(image_bytes(), "image/png", auth_settings(ocr_tessdata_dir="missing-models"))
    assert error.value.category == "ocr_unavailable"


def test_normalization_does_not_correct_values() -> None:
    assert (
        normalize("13.2\r\n18 2.4 mg/dL g/dL ng/mL mIU/L\x00")
        == "13.2\n18 2.4 mg/dL g/dL ng/mL mIU/L"
    )
    assert normalize("हिंदी १३.२") == "हिंदी १३.२"


@pytest.mark.parametrize(
    "tsv",
    [
        "garbage",
        "9\t1\t1\t1\t1\t1\t0\t0\t10\t10\t90\tvalue\n",
        "5\t1\t1\t1\t1\t1\t-1\t0\t10\t10\t90\tvalue\n",
        "5\t1\t1\t1\t1\t1\t0\t0\t101\t10\t90\tvalue\n",
        "5\t1\t1\t1\t1\t1\t0\t0\t10\t10\tnan\tvalue\n",
        "5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t101\tvalue\n",
        "5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t90\tvalue\textra\n",
    ],
)
def test_malformed_ocr_output_fails_closed(tsv: str) -> None:
    with pytest.raises(ExtractionFailure, match="ocr_failure"):
        parse_tsv(tsv, 100, 100)


def test_ocr_output_preserves_tokens_boxes_and_line_groups() -> None:
    tsv = (
        "5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t90\t13.2\n"
        "5\t1\t1\t1\t1\t2\t11\t0\t20\t10\t80\tg/dL\n"
        "5\t1\t1\t1\t2\t1\t0\t11\t20\t10\t70\tहिंदी\n"
    )
    text, spans = parse_tsv(tsv, 100, 100)
    assert text == "13.2 g/dL\nहिंदी"
    assert spans[1].bbox == (11, 0, 31, 10) and spans[1].confidence == 80
    assert parse_tsv("", 100, 100) == ("", [])


def test_processing_api_anonymous_csrf_and_invalid_identifier() -> None:
    provider = ProviderFixture()
    with TestClient(
        create_app(auth_settings(), provider_transport=httpx.MockTransport(provider.handle))
    ) as client:
        for suffix in ("processing", "extraction"):
            assert client.get(f"/reports/{uuid4()}/{suffix}").status_code == 401
        assert (
            client.post(
                f"/reports/{uuid4()}/process", json={"idempotency_key": str(uuid4())}
            ).status_code
            == 403
        )
        client.cookies.set("sl_access", provider.token())
        assert client.get("/reports/not-a-uuid/processing").status_code == 422
        provider.active = False
        assert client.get(f"/reports/{uuid4()}/extraction").status_code == 401


@pytest.mark.skipif(
    os.environ.get("RUN_OCR_EVALUATION") != "1",
    reason="Requires approved local OCR runtime and explicit evaluation opt-in",
)
@pytest.mark.parametrize("kind", ["scan", "mixed", "png", "jpeg", "rotated", "blank", "hindi"])
def test_real_ocr_quality(kind: str) -> None:
    models = os.environ.get("OCR_EVALUATION_MODELS")
    assert models and Path(models).is_dir(), "Configure OCR_EVALUATION_MODELS"
    media = "application/pdf"
    if kind == "hindi":
        data = (Path(__file__).parent / "fixtures" / "hindi-mixed.png").read_bytes()
        media = "image/png"
    elif kind in {"png", "jpeg", "rotated"}:
        data = image_bytes("JPEG" if kind == "jpeg" else "PNG", rotated=kind == "rotated")
        media = "image/jpeg" if kind == "jpeg" else "image/png"
    else:
        data = document(("native", "scan") if kind == "mixed" else (kind,))
    result = extract(data, media, auth_settings(ocr_tessdata_dir=models))
    if kind == "blank":
        assert result.pages[0].text == "" and "no_text" in result.pages[0].warnings
        return
    assert result.pages[-1].method == "ocr"
    assert all(token in result.pages[-1].text for token in TOKENS)
    if kind == "mixed":
        assert result.pages[0].method == "native_text"
    if kind == "rotated":
        assert result.pages[0].rotation == 90
    if kind == "hindi":
        assert "हिंदी परीक्षण रिपोर्ट" in result.pages[0].text
        assert "नमूना 13.2 g/dL" in result.pages[0].text
