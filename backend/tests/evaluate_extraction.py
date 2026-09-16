"""Reproducible synthetic quality evaluation; never pass patient records here."""

import argparse
import json
from pathlib import Path

from app.core.extraction import ProcessingFailure, extract
from tests.auth_support import auth_settings
from tests.extraction_fixtures import LINES, TOKENS, write_fixtures


def edit_distance(expected: list[str], actual: list[str]) -> int:
    previous = list(range(len(actual) + 1))
    for index, token in enumerate(expected, 1):
        current = [index]
        for column, other in enumerate(actual, 1):
            current.append(
                min(current[-1] + 1, previous[column] + 1, previous[column - 1] + (token != other))
            )
        previous = current
    return previous[-1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--models", required=True)
    parser.add_argument("--hindi-font")
    args = parser.parse_args()
    write_fixtures(args.output / "fixtures", args.hindi_font)
    cases = [
        "native.pdf",
        "multipage.pdf",
        "scanned.pdf",
        "mixed.pdf",
        "english.png",
        "english.jpeg",
        "rotated.png",
        "blank.pdf",
        "hindi-mixed.png",
    ]
    records: list[dict[str, object]] = []
    failed = False
    for name in cases:
        fixture = args.output / "fixtures" / name
        media = {".pdf": "application/pdf", ".png": "image/png", ".jpeg": "image/jpeg"}[
            fixture.suffix
        ]
        record: dict[str, object] = {"fixture": name}
        try:
            result = extract(
                fixture.read_bytes(), media, auth_settings(ocr_tessdata_dir=args.models)
            )
            page_scores = []
            for page in result.pages:
                expected = "\n".join(LINES)
                if page.method == "native_text":
                    expected += f"\nSource page {page.page_number}"
                if name == "hindi-mixed.png":
                    expected += "\nहिंदी परीक्षण रिपोर्ट\nनमूना 13.2 g/dL"
                if name == "blank.pdf":
                    expected = ""
                reference, actual = " ".join(expected.split()), " ".join(page.text.split())
                char_error = edit_distance(list(reference), list(actual)) / max(1, len(reference))
                word_error = edit_distance(reference.split(), actual.split()) / max(
                    1, len(reference.split())
                )
                tokens = {token: token in page.text for token in TOKENS} if expected else {}
                acceptable = all(tokens.values()) and char_error <= 0.05 and word_error <= 0.1
                failed |= not acceptable
                page_scores.append(
                    {
                        "page": page.page_number,
                        "method": page.method,
                        "character_error_rate": char_error,
                        "word_error_rate": word_error,
                        "tokens": tokens,
                        "rotation": page.rotation,
                        "warnings": page.warnings,
                        "passes_thresholds": acceptable,
                    }
                )
            record.update(status="completed", pages=page_scores)
            # Only generated synthetic content is written by this evaluation command.
            (args.output / f"{name}.result.json").write_text(
                result.model_dump_json(indent=2), encoding="utf-8"
            )
        except ProcessingFailure as error:
            record.update(status="failed", failure=error.category)
            failed = True
        records.append(record)
    (args.output / "quality-results.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(records, indent=2, ensure_ascii=True))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
