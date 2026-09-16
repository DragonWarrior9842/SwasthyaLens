# Phase 4 extraction decision

16 September 2026. Decision recorded before installing extraction dependencies.

The Phase 3 baseline was re-inspected: React/Vite BFF, FastAPI, owner-JWT Supabase requests, private immutable source objects, deletion tombstones, no worker. Frontend lint/typecheck/137 tests/build and backend Ruff/format/mypy/189 tests passed; both real two-user integration suites passed (48.47 s). Initial sandbox cache/network failures passed on authorized rerun. No Phase 5 functionality is authorized.

## Candidates and decision

| Candidate | Assessment |
| --- | --- |
| pypdf / pdfplumber | Useful native text/layout APIs, but no PDF rasterizer; would require a second engine for scans. Large decoded content streams still require process memory isolation. |
| PyMuPDF | Strong combined text/rendering APIs; AGPL/commercial licensing introduces a separate distribution decision. |
| PDFium via pypdfium2 | Selected native text, character coordinates and bounded per-page rendering from one engine; permissive wrapper/upstream notices must accompany distribution. Never initialize forms, scripting or attachments. |
| Tesseract 5 | Selected local OCR for printed English/Hindi and mixed Latin-Devanagari, with language model files, word boxes and engine scores. CPU-only development is practical. Scores are not calibrated medical accuracy. |
| PaddleOCR | Credible local alternative with Devanagari recognition; larger ML runtime/model deployment surface. Reconsider if measured Tesseract quality is insufficient, not merely because text is returned. |
| Google Document AI / Azure Document Intelligence | Candidates for stronger managed layout OCR, but introduce per-page billing, external transmission, region/retention review and credentials. Not selected, installed or called. A future switch requires the owner's explicit provider approval. |

Sources: [PDFium APIs](https://pypdfium2.readthedocs.io/en/stable/python_api.html), [pypdf memory caveat](https://github.com/py-pdf/pypdf/blob/main/docs/user/extract-text.md), [Tesseract language/TSV APIs](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [Tesseract quality and tables](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html), [PaddleOCR language models](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html), [Google OCR](https://docs.cloud.google.com/document-ai/docs/enterprise-document-ocr).

## Intended scope and tradeoffs

- Text PDFs: inspect each page; use usable native text without OCR. Scanned pages and PNG/JPEG use OCR. Mixed PDFs choose per page. Sparse native text and large image coverage must not conceal a scanned report behind a native header.
- Preserve source report/digest, attempt, page order, extraction method, coordinate convention, text and available boxes/scores. Native text has no invented confidence. Original files remain authoritative and untouched.
- Normalize line endings and NFC, remove extraction control artifacts; never translate, correct numbers/units, infer cells or interpret medical content. Tables retain positioned source text rather than fabricated semantic rows.
- English, Hindi and mixed scripts use `eng+hin`. Model support does not prove acceptable Hindi accuracy. Reproducible synthetic fixtures must measure decimals, units, page order, rotation and Hindi behavior before acceptance.
- Respect PDF rotation and JPEG EXIF orientation. Evaluate OCR orientation detection; record applied rotations and warnings. Do not add unmeasured contrast/deskew transformations.
- Explicit process request returns durable state promptly; bounded local execution uses persisted attempts and deadlines. After an API restart or expired user authorization, attempts become retryable failures, never false completion. No provider tokens are persisted for unattended work.
- New run/page records derive ownership through reports, with active-session RLS. Attempts are immutable after completion. Deletion intent removes derived rows and prevents late completion.
- Bound upload bytes, page count, dimensions, rendered pixels, text/box output, total runtime, process memory, concurrency and attempts. Killable parsing/OCR subprocesses get no application credentials. Process isolation is resource containment; production still needs a dedicated low-privilege, network-restricted worker/container.
- Local OCR has no per-page vendor charge or new external OCR data recipient. CPU/RAM, patching, temporary-file cleanup and model packaging are operational costs. Existing Supabase remains the storage/database provider. No compliance claim is made.
- Production viability requires explicit worker isolation, shared admission controls/quotas and deployment validation. This phase's supported development workflow can require an authenticated retry after interruption; it must not advertise an unattended durable queue.

Final implementation details, measured results and any deviations belong in `phase-4-handoff.md`.

## Evaluation update

The final choice remains PDFium and local Tesseract. A hash-pinned Windows tesserocr wheel supplies the engine, with explicit Python 3.12 support. Evaluation selected the more accurate `tessdata_best` English/Hindi models, retained the pinned OSD model, and justified bounded 2× bicubic image enlargement and a lower OSD application threshold with an uncertainty warning. The original bytes are unchanged. The nine-document synthetic evaluation passed, including exact decimal/unit preservation, native/OCR page selection, a rotated image and correctly shaped Hindi. Initial fast-model and Lanczos-decimal failures are recorded in the handoff; they were not counted as passes. This small set does not establish general medical-report accuracy or production isolation.
