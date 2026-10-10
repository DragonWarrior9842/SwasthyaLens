# Phase 13 manual acceptance still required

2026-10-10. **Phase 13 is complete; VOICE PHYSICAL ACCEPTANCE = PENDING.** Voice implementation and automated simulation passed. These device/deployment checks remain open after formal closure. Simulated tests do not establish physical recognition, microphone permission or device speech quality. Default release proposal: `VITE_ENABLE_VOICE=false`; typed input remains available. No physical results were supplied. No Phase 14 work is authorized.

Use synthetic phrases only. Record date, browser/OS version, device, installed local English/Hindi packs and each PASS/FAIL/unsupported result. Never record audio, health information, credentials or tokens in evidence. Test Windows Chrome and Windows Edge separately; Android Chrome is optional when a device is available. Use a separately approved voice-enabled acceptance build, never silently replace the voice-disabled release artifact.

| Check | Exact action and expected result |
|---|---|
| Local capability | Open Assistant, opt in for this visit. Confirm local recognition capability/pack state is reported truthfully. An unsupported browser offers typing without cloud recognition fallback. |
| Permission grant | Grant microphone permission when prompted. Start must show listening and an accessible status; no microphone use before explicit Start. |
| Permission denial | In a fresh browser permission state, deny permission. An actionable message appears, controls recover and typing remains usable. Do not disable browser security to pass. |
| Start / Stop | Start, say “Explain this synthetic report”, then Stop. Listening ends and the transcript enters the editable composer. |
| Cancel | Start again, speak, then Cancel. Listening ends without committing that capture or sending a message. |
| Edit / no auto-send | Edit the transcript by keyboard. No message/provider request occurs until explicit Send. Keep AI disabled during this checklist. |
| English | Select English with a locally installed pack; test a short synthetic phrase and record the actual transcription quality. |
| Hindi | If the local Hindi pack exists, select Hindi and say a short synthetic phrase such as “यह एक परीक्षण है”. Record actual recognition. Missing pack is unsupported, not PASS. |
| Missing pack | Select a language without an installed local pack. Verify clear fallback to typing; no silent remote recognition or automatic pack download. |
| TTS | Read a bounded synthetic response aloud. Confirm explicit playback, language/voice selection and intelligibility; unavailable voices must be reported honestly. |
| Pause / resume / stop | Where supported, pause, resume and stop TTS. State/status and buttons match actual playback. Mark unsupported capabilities explicitly. |
| Navigation | While listening and separately while speaking, navigate away. Both activities cancel; returning must not restart them. |
| Logout | While listening and separately while speaking, sign out. Both cancel and account content clears; a second user cannot recover the transcript. |
| Keyboard / mobile | Reach each control by keyboard, verify visible focus and labels/status announcements. On optional Android, repeat at narrow width and with the software keyboard. |

Screen-reader and physical keyboard review remains a manual complement to automated accessibility checks. Review authentication, Dashboard, Reports and review, History, Trends, Assistant, Settings, Exports and Notifications in English and long Hindi content. Verify heading/landmark order, error association, focus after navigation/dialogs/errors and status announcements. Automated results are scoped checks, not WCAG certification.

Production acceptance separately requires HTTPS/headers/cookies, exact Auth URLs, reliable signup/recovery delivery where enabled, isolated staging, full migration replay, backup/restore, OCR worker/private-temp isolation, sanitized gateway logs and incident ownership. Follow the [single Phase 14 prerequisite list](../deploy/README.md#phase-14-prerequisites) and [operations runbook](phase-13-operations.md); none of those deployed controls is established by a localhost browser run.
