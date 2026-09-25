# Complete validation report — Namma Kavacham AI

- Date: 2026-09-25
- Branch: `deploy-render` (starting point `0ec3386`)
- Scope: whole application (backend API, rules, government KB, AI fallback, threat intelligence, frontend
  workflow, OCR / camera / speech, security, accessibility, responsive layout, deployment config)

## Executive summary

**Tested:** the backend API with 34 black-box request cases (plus 4 method/route checks); a 32-message risk / language / government matrix
through the real endpoint; every AI-provider and VirusTotal failure state (existing mocked tests, mapped one by
one); frontend error states; the full UI flow in headless Chrome at 7 widths in English and Tamil; keyboard
focus order; accessible names; secrets; production configuration.

**Fixed:** 7 confirmed defects (1 High, 4 Medium, 2 Low), each with a regression test (see the bug register).
The most important were a UPI ID being scored as a fake government domain, correct Tamil safety advice being
scored HIGH, a malformed server response blanking the page, and the UI naming Gemini while Groq is configured.

**Open:** no blocking defect found. Known limitations remain (curated KB coverage, pattern-based language
rules, no real-device or native-Tamil review, no live deployment check). A synthetic test matrix is not a
measure of real-world detection accuracy.

**Status:** READY WITH DOCUMENTED LIMITATIONS (reason at the end).

## Environment

| Item | Value |
|---|---|
| OS | Windows 11 (10.0.26200) |
| Python | 3.11.9 (FastAPI 0.115.6, Starlette 0.41.3, Pydantic 2.13.5, httpx 0.28.1) |
| Node / npm | 24.20.0 / 11.19.0 (Vite 8.3, Vitest 5.0, TypeScript 7) |
| Browser | Headless Chrome 153.0.8010.53, driven over the DevTools protocol (no extra dependencies) |
| Real devices / emulators | None available |
| Not available | Firefox, Safari / iOS Safari, Android Chrome, native screen readers, ESLint, axe, Playwright (MCP server failed to connect) |

## Baseline results (before any change)

| Check | Result | Evidence |
|---|---|---|
| Git state | clean, `deploy-render` = `origin/deploy-render` at `0ec3386` | `git status -sb` |
| Backend tests | 265 passed | `python -m pytest -q -p nonet` |
| Outbound network during backend tests | none | socket/DNS-blocking pytest plugin |
| Frontend tests | 136 passed (10 files) | `npm test` |
| Typecheck | pass | `npm run typecheck` |
| Production build | pass | `npm run build` |
| Lint / browser test configuration | none configured | `package.json` scripts |

## Final results

| Check | Result | Evidence |
|---|---|---|
| Backend tests | **284 passed**, 0 failed (+19 regression tests) | `python -m pytest -q -p nonet` |
| Outbound network during backend tests | **none** | nonet plugin output |
| Frontend tests | **143 passed**, 0 failed (+7 tests; 1 test corrected, see BUG-005) | `npm test` |
| Typecheck | pass | `npm run typecheck` |
| Production build | pass | `npm run build` |
| Headless Chrome, 7 widths × 5 screens (home, input, review, report EN, report TA) | 0 horizontal overflow, 0 console errors, report rendered at every width | DevTools-protocol script |
| Keyboard focus | logical order, visible focus on all 14 stops checked | same script |
| Accessible names | 0 unnamed buttons/links, 0 unlabelled inputs, 0 images without alt, 1 `h1` per page | same script |
| Secret scan | clean (only known fake test keys) | `git grep` + `git log -p` patterns |
| Tests removed or weakened | none; one assertion that encoded BUG-005 was corrected | diff review |

## Feature coverage

| Feature | Automated | Manual | Integration | Status |
|---|---|---|---|---|
| `/v1/analyze` validation and errors | unit + endpoint tests; 34-case probe | — | TestClient | Verified locally |
| Deterministic message rules (EN / TA / Tanglish) | unit tests; 32-case matrix | — | endpoint | Verified locally (synthetic inputs) |
| URL / domain heuristics | unit tests; probe | — | endpoint | Verified locally |
| Risk engine and levels | unit tests; matrix | — | endpoint | Verified locally |
| Government claims + curated KB (7 entries) | unit + endpoint tests | — | endpoint | Verified locally |
| AI explanation (Groq / Gemini) | mocked provider tests | — | endpoint with fake explainers | Verified with mocks; **no live call** |
| Template fallback | unit + endpoint tests | — | endpoint + browser | Verified locally |
| VirusTotal | mocked transport tests | — | endpoint with fake provider | Verified with mocks; **no live call** |
| Review / consent gate, provenance | component tests | — | browser (text path) | Verified with browser automation (text path) |
| OCR (tesseract.js) | component + service tests (engine mocked) | — | — | Verified with mocks only; not on real screenshots |
| Camera | component + service tests (media APIs mocked) | — | — | Verified with mocks only |
| Read-aloud (speech synthesis) | component + service tests (speech API mocked) | — | — | Verified with mocks only |
| Report UI, EN/TA | component tests | — | headless Chrome | Verified with browser automation |
| Responsive layout | — | — | headless Chrome 320–1440 px | Verified with browser automation (Chromium only) |
| Render deployment | config review | — | — | **Not tested live** |

## Bug register

| ID | Severity | Description | Fix | Regression test | Status |
|---|---|---|---|---|---|
| BUG-001 | High | The name part of a UPI ID (`laptop.gov@ybl`) was extracted as a link and scored as a high-confidence government lookalike domain (+30) | Bare-domain URL pattern must not be followed by `@` (`url_analyzer._URL_RE`) | `test_upi_id_is_not_extracted_as_a_link`, `test_real_links_next_to_upi_ids_are_still_extracted` | Fixed |
| BUG-002 | Medium | A bare domain mentioned in text (`pmkisan.gov.in`, `cybercrime.gov.in`) was flagged "does not use https" because the parser adds `http://`; benign messages gained points | `no_https` only when `http://` / `hxxp://` is written explicitly | `test_bare_domain_is_not_flagged_as_no_https`, `test_explicit_http_is_still_flagged` | Fixed |
| BUG-003 | Medium | Tamil safety advice using the negative imperative ("OTP யாருக்கும் சொல்லாதீங்க" = "don't tell anyone the OTP") was scored as a credential request (HIGH 60) | Negation now recognises -ாதீர்கள் / -ாதீங்க / -ாதீர் / -ாதே directly after the verb; Tamil verb patterns made lazy so a match ends at the nearest verb | 3 advice cases + `test_share_then_tell_no_one_is_still_a_credential_request` (the scam line stays flagged; this test caught a regression in the first version of the fix) | Fixed |
| BUG-004 | Low | Natural word order missed: Tamil "9876543210 அழைக்கவும்" (number, then "call") and Tanglish "50 rupees fee ah … anuppunga" | Added the reversed-order callback pattern and a Tanglish fee-then-send pattern | 3 tests incl. negated "அழைக்க வேண்டாம்" | Fixed |
| BUG-005 | Medium | The check-status panel always said "AI explanation (Gemini)" and `/healthz` reported only `gemini_configured`, even with Groq configured. The existing test asserted the wrong label with a "template" fixture | Label derived from `provider_flags.ai_provider`; `/healthz` adds `ai_provider` (name only; `gemini_configured` kept for compatibility) | `names the configured AI provider`, `test_healthz_reports_active_ai_provider_without_secrets` (3 configs, asserts no key text) | Fixed |
| BUG-006 | Medium | A 200 response with missing fields (proxy page, partial body) crashed rendering (`TypeError … assessment_status`), leaving a blank report area with no retry | `submitAnalysis` shape-checks the fields the report reads and raises the normal recoverable error | 5 cases: `{}`, missing `risk`, non-JSON, 429, 500 | Fixed |
| BUG-007 | Low | At 320 px in Tamil the report was 28 px wider than the screen (page scrolled sideways) because long hostnames could not break inside grid items; two tap targets were under 24 px | `[overflow-wrap:anywhere]` on the report container; `min-h-6` on "Clear"; padded official-site links | Headless Chrome re-run: 0 overflow in 35 width/screen combinations; no targets < 24 px except the visually hidden skip link | Fixed |

## Observations (not changed; documented)

| Observation | Why not changed |
|---|---|
| An English warning that quotes a whole scam line scores HIGH (48) | Detecting quotation is not reliable with patterns; documented in README limitations |
| A friend's UPI request ("send my share to ramesh@okaxis") scores MEDIUM via the older payment rule | Pre-existing, pinned by a test, already documented |
| "PM-KISAN instalment of Rs 2,000 has been credited … pmkisan.gov.in" scores MEDIUM (government phrasing) | Cautious by design; message identity is never verified |
| "Digital arrest … call officer" scores only MEDIUM | Detection tuning, not a defect; would need a new rule |
| Defanged links (`hxxp://evil[.]com`) are not extracted; `javascript:` text is not a link | Pattern limitation; nothing is rendered as a link |
| API accepts `source: url_input` with text that is not a URL (frontend validates) | Harmless: analysed as text |

## Security findings

- **Fixed:** BUG-005 provider-status accuracy; BUG-006 unhandled malformed response.
- **Verified:**
  - Responses and errors:
    - All 34 probe responses were free of tracebacks, file paths and key-shaped strings.
    - Errors use one `{error, detail}` shape, and validation errors never echo the submitted input.
  - Limits and uploads:
    - Body limits return 422 (configured 8,000 characters) or 422 (hard limit 20,000).
    - A 9 MB upload returns 413, a wrong file type 415, an empty file 422, and a `../` filename is ignored.
  - CORS: allowed origins are explicit and credentials are off; an unknown origin's preflight is rejected with 400.
  - Production: `/docs`, `/redoc` and `/openapi.json` are off (tested), and a 500 returns a generic body (tested).
  - Rendering: no `dangerouslySetInnerHTML`. The only `href` built from backend data is the official-site link, restricted to https on `.gov.in`/`.nic.in`; image previews are local `blob:` URLs that are revoked.
  - Logging: logs record counts and statuses only, never message text (code review).
  - AI data boundary: the model receives only facts, never the message (tested). Prompt injection doesn't change the level, evidence or government status (tested).
- **Accepted limitation:** no rate limiting in the app (rely on the platform); `/healthz` reveals which
  providers are enabled (names and booleans only).
- **Not tested:** security headers (none configured); load or abuse testing; the live Render edge.
- **Blocked:** none.

## AI and provider validation

- **Configuration:** a provider is active only when `LLM_PROVIDER` selects it, it is enabled, and it has a key;
  otherwise the template explanation is used (tested for Groq and Gemini). The Render Blueprint selects Groq.
- **Fallback and retry:** the template is used on timeout, connection error, auth error, 5xx, 429, malformed
  output and failed validation. At most one retry, only for 429 with a short `Retry-After` or for 5xx
  (existing tests, re-run).
- **Validation:** output that changes the level, claims the message is safe, invents a domain or number, or
  leaks a key is rejected; the risk data is identical with and without the AI.
- **Live tests:** none. No Gemini, Groq or VirusTotal request was made (network-blocked test run; the browser
  run used a backend started with every provider switched off). Quota behaviour is known only from mocks.
- **Provider labels:** fixed (BUG-005).

## Localization results

- **English:** 17 matrix cases behaved as expected (benign LOW, scams HIGH/CRITICAL), with the observations above.
- **Tamil:** OTP / suspension / fee / free-benefit / electricity threats detected; Tamil negation ("வேண்டாம்",
  "கேட்காது", and after BUG-003 "-ாதீங்க") not flagged; "ரூ.100" amounts handled.
- **Tanglish:** OTP + block threats, fee-then-send (after BUG-004) and negation ("share pannatheenga") behave as
  expected; coverage is pattern-based, not a model of every dialect or spelling.
- **Mixed:** English + Tamil + URL / UPI / phone inputs processed without errors or lost characters; Tamil
  renders in the report in Chrome.
- **Native review pending:** all Tamil wording (`docs/tamil-review.md`, unchanged).
- **Confirmed localization bugs:** BUG-003, BUG-004 (fixed), BUG-007 (Tamil layout, fixed).
- **Deferred:** cloud Tamil speech.

## Browser and device results

| Environment | Result |
|---|---|
| Headless Chrome 153 on Windows 11, 320/375/390/768/1024/1280/1440 px | Full text flow to report in EN and TA; no overflow after BUG-007; no console errors |
| Firefox, Safari, iOS Safari, Android Chrome | **Not tested** (not available) |
| Real camera, real screenshots, on-device Tamil voice | **Not tested** (no device); covered by mocked tests only |
| Native screen reader | **Not tested**; only static checks of names, labels and headings |
| Colour contrast | **Not tested** (no contrast tool configured) |

## Deployment readiness

- **Verified locally:** build and start commands, health endpoint, production docs switch, CORS handling,
  frontend API base URL logic, template fallback with no keys.
- **Render configuration review:**
  - Python 3.11.9; start command `uvicorn` with no `--reload` or debug flag; SPA rewrite present.
  - Secrets are `sync: false`, and all variable names match the code and README.
  - No Node version is pinned for the static site (README explains `NODE_VERSION`).
- **Live deployment:** not tested.
- **Required post-deployment checks:**
  - `/healthz` shows `"ai_provider":"groq"` once `GROQ_API_KEY` is set.
  - `/docs` returns 404.
  - A sample check completes from the static site, which shows that CORS and `VITE_API_BASE_URL` are correct.
  - The camera works over the https site on a phone.
  - Tamil read-aloud works on a device that has a Tamil voice.

## Remaining risks

- OCR accuracy on real screenshots; the first OCR use needs the jsDelivr CDN.
- The camera needs https (or localhost).
- Tamil read-aloud depends on an on-device Tamil voice.
- Tamil wording is not natively reviewed.
- The curated KB covers 7 services only, and there is no live verification of government records.
- The language rules are pattern-based; see the observations above for known false positives and false negatives.
- No real-device, non-Chromium or screen-reader testing.
- No live provider or deployment test.

## Final status

**READY WITH DOCUMENTED LIMITATIONS.** Every automated check passes, and every defect found in this pass was
fixed with a regression test and re-verified. No known blocking issue remains. The status is not
"READY FOR PR REVIEW" because real-device, non-Chromium, screen-reader, native-Tamil and live-deployment
validation have not been performed; those limitations are listed above and in the README.
