# Phase 5 extraction decision

Decision recorded before implementation, after the clean Phase 4 baseline at
`2daa612`: deterministic, bounded, explicitly requested candidate extraction.

Phase 4 provides immutable ordered page text, native line rectangles or OCR word
rectangles, coordinate systems, OCR confidence, and versioned processing attempts.
Native PDF text can collapse column whitespace. OCR text can contain ambiguous
characters. Neither representation warrants treating a parsed value as validated.

| Approach | Decision |
| --- | --- |
| Deterministic parsing | Use explicit table headers and bounded physical rows. Abstain on ambiguous column relationships. |
| Regex / lexical rules | Use small anchored grammars within a row/cell, never pair labels and values across the page. Preserve raw strings and exact decimal strings. |
| Table / layout | Prefer explicit pipe cells; support compact rows only with an unambiguous header and decomposition. Attach matching source span indices; no invented boxes. Reject repeated side-by-side headers. |
| Controlled aliases | Small versioned JSON dictionary, exact case-insensitive whitespace-normalized lookup. Unknown labels survive unmapped. No fuzzy matching. |
| Local NLP | Not justified by these fixtures; adds models and uncertain semantics without solving source pairing. |
| Structured LLM | Not needed for the supported formats. No provider, credentials, disclosure of report text, or AI explanations. Broader irregular reports remain unsupported. |

Explicit extraction selects a completed owner-scoped Phase 4 attempt. Each new
idempotency key creates a retained attempt (maximum three per source attempt).
Bounded synchronous parsing uses at most 20 pages, 400,000 input characters,
512 characters per row, 200 candidates, and a five-second parser deadline.
Durable processing leases recover interrupted requests. No automatic chains.

Three minimal tables hold attempts, immutable machine candidates, and append-only
user review revisions. Ownership derives through Phase 4 and the report. Existing
report deletion intent cascades through all three. Worker-secret checks supplement,
never replace, active-session and owner checks. Browsers cannot submit machine text.

Every result initially needs review. User confirmation is personal review, not
clinical validation. Corrections preserve the original result and source text.
Units are not normalized or converted. Only printed flags are retained; calculated
range status remains unknown. No observations or longitudinal history are written.

Evaluation must distinguish supported synthetic rows from intentionally unsupported
layouts, include false-pairing negatives, and measure field correctness and misses.
Tiny synthetic results cannot establish general medical extraction accuracy.
