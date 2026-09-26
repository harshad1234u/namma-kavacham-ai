# CivicInsight AI

**An AI-powered Indian citizen platform that helps people discover and verify government schemes and services,
while turning multilingual citizen feedback into actionable development intelligence.**

Official government sources provide the evidence. NVIDIA NIM (Sarvam-M + Nemotron embeddings) understands the
citizen's language and explains the evidence. Deterministic engines make every decision.

| Module | What it does | Where |
|---|---|---|
| **Government Intelligence** | Ask about / verify a scheme claim against a curated KB of 13 central schemes quoted from `.gov.in` pages, falling back to live retrieval from a reviewed registry of official pages; scheme discovery; eligibility guidance (4 honest outcomes); official application channels only | `/v1/schemes/*`, `backend/app/civic/schemes`, `backend/app/civic/retrieval` |
| **Development Intelligence** | Citizens report needs (text / opt-in voice / photo); deterministic classification with optional Sarvam-M closed-vocabulary fallback; aggregation, clustering, gap + configurable priority engines, hotspots, policymaker dashboard, grounded policy insight | `/v1/development/*`, `backend/app/civic/development` |
| **Stay Safe** (original product) | Scam-risk checker for messages, links and screenshots; unchanged | `/v1/analyze`, `/safety`, `/analyze` |

Languages: all 22 Scheduled Languages can be selected; support differs per language and is published at
`/v1/meta/languages` and the in-app **Languages** page (authored UI in English, Hindi and Tamil; AI understanding and
translation for the Sarvam-M-listed Indic languages when AI is enabled; English fallback, clearly labelled, elsewhere).

Full architecture, verification rules, priority methodology, data provenance, privacy/security model and the
IMPLEMENTED / DEMO / PARTIAL / FUTURE breakdown: **[docs/civicinsight.md](docs/civicinsight.md)**.

### CivicInsight configuration (backend env)

| Variable | Default | Purpose |
|---|---|---|
| `AI_ENABLED` | `false` | Turns on NVIDIA NIM for the civic modules (also needs the key) |
| `NVIDIA_NIM_API_KEY` | — | NIM API key for the chat model (never logged or returned) |
| `NVIDIA_NIM_EMBEDDING_API_KEY` | falls back to `NVIDIA_NIM_API_KEY` | Separate key for the embedding model, if yours differs |
| `NVIDIA_NIM_BASE_URL` | `https://integrate.api.nvidia.com/v1` | NIM endpoint (hosted or self-hosted) |
| `NVIDIA_NIM_SARVAM_MODEL` | `sarvamai/sarvam-m` | Chat model for understanding, explanation, translation. **Retired on NVIDIA's hosted NIM (HTTP 410, end of life 2026-07-27)**: until a replacement is approved, chat AI falls back to deterministic behaviour |
| `NVIDIA_NIM_EMBEDDING_MODEL` | `nvidia/nemotron-3-embed-1b` | Embeddings for official-evidence retrieval |
| `RETRIEVAL_ENABLED` | `true` | Live fetch of the official-source registry |
| `DEV_WEIGHT_*`, `DEV_HOTSPOT_MIN_REPORTS`, … | see `app/civic/settings.py` | Development Priority Engine configuration |

Check NIM connectivity: `cd backend && python scripts/check_nim.py`. Re-verify every KB quote against the live
official pages: `python scripts/verify_scheme_sources.py`.

---

# Stay Safe module (formerly Namma Kavacham AI)

A bilingual (English/Tamil) scam-risk checker for suspicious messages, links, and screenshots.
Deterministic checks decide the risk level; AI only explains; a missing or unavailable check is never shown as safe.
Scope and design decisions for this module live in [docs/](docs/).

## Status: Phase 5 (government scheme checks, Tamil review draft)

All automated tests pass (see [Tests](#tests)). Nothing below has been validated on real devices or by a native
Tamil reviewer; see [Known limitations](#known-limitations).

### Implemented

| Area | State |
|---|---|
| `POST /v1/analyze` for pasted / typed text and URLs | Built |
| Review & explicit-consent gate before any request, with input provenance labels | Built |
| Bilingual deterministic message rules (English / Tamil / Tanglish), URL/domain heuristics | Built |
| Risk engine (LOW/MEDIUM/HIGH/CRITICAL + evidence); AI output cannot change level, score, evidence or government status | Built |
| Curated government KB (7 services in 5 categories, cited official sources) | Built — `backend/app/data/government_kb.json`; coverage and not-covered list in [docs/government-kb-coverage.md](docs/government-kb-coverage.md) |
| Government claim detection + KB comparison (6 statuses; the "supported" status is labelled "Matches official reference — message not confirmed") | Built |
| Official next steps and official website links on the government card, only from matched KB entries (`https` on `.gov.in` / `.nic.in`) | Built (Phase 5) |
| Scheme-scam indicators: payment to a UPI ID in an official context, applying via WhatsApp/Telegram, fee for a "free" benefit | Built (Phase 5), medium-confidence indicators |
| Screenshot text extraction in the browser (tesseract.js; English, Tamil, or both), with a confidence warning and user correction before submitting. The image never leaves the device; only the reviewed text is sent. | Built (Phase 4), automated tests only |
| Camera capture (rear camera preferred) feeding the same in-browser OCR and review | Built (Phase 4), automated tests only |
| "Listen to this report": browser speech synthesis with on-device voices only; reads a redacted summary (never the original message); pause / resume / stop / restart / speed; no autoplay; says so when no Tamil voice exists instead of switching to English | Built (Phase 4), automated tests only |
| Template explanation in English and Tamil (always available; used whenever no AI explanation is accepted) | Built |
| Redacted logging, upload validation, size limits | Built |
| Tanglish urgency ("account block aagidum") + Tanglish advisory negation | Built (Phase 3) |
| API docs hidden when `ENVIRONMENT=production`; unexpected errors return a generic 500 with no traceback | Built (Phase 3) |

### Optional (off unless configured)

| Area | How to turn it on | When unavailable |
|---|---|---|
| Groq EN/TA explanation (`openai/gpt-oss-20b`, strict JSON schema, one bounded retry on 429/5xx, output validation) | `LLM_PROVIDER=groq`, `GROQ_ENABLED=true`, `GROQ_API_KEY`. The Render Blueprint selects Groq. Mock-tested only. | Template explanation; risk result unchanged |
| Gemini explanation (alternative provider) | `LLM_PROVIDER=gemini`, `GEMINI_ENABLED=true`, `GEMINI_API_KEY`. Off in the Render Blueprint. | Template explanation; risk result unchanged |
| VirusTotal URL lookup (only the link is sent) | `VIRUSTOTAL_ENABLED=true` and `VIRUSTOTAL_API_KEY`. Off in the Render Blueprint. Mock-tested. | Reported as "link not checked", never as safe |

An AI provider is used only when it is selected by `LLM_PROVIDER`, enabled, and keyed. Otherwise, and on any
timeout, error, quota limit (HTTP 429) or failed validation, the report uses the template explanation. The AI
provider never receives the submitted message — only the deterministic findings — and cannot change the risk level.

### Deferred

| Area | Notes |
|---|---|
| Server-side screenshot OCR | The API still accepts an optional screenshot file for compatibility; it is validated and discarded without OCR (`backend/app/services/ocr_stub.py`). The web app does its OCR in the browser and never uploads images. |
| Cloud Tamil text-to-speech | Deferred in Phase 5 pending provider selection and a privacy/pricing review. Only on-device voices are used. |
| Live verification of government records | Out of scope: the KB is a static, curated reference. |

### Future work

- Native Tamil review of all wording ([docs/tamil-review.md](docs/tamil-review.md)), then applying approved changes.
- Manual testing on real devices and browsers (list under [Known limitations](#known-limitations)).
- More KB entries with verified official sources; re-check Magalir Urimai Thogai when its site's certificate is valid.

The knowledge base is a small curated reference, not live verification. Each fact quotes its official
source; update `last_reviewed` and the `retrieved` dates when you re-check them
(see [docs/government-kb-coverage.md](docs/government-kb-coverage.md)).

## Run locally

Backend (Python 3.11):

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Keys and flags are read from the repo-root `.env` or `backend/.env` (both gitignored; `backend/.env` wins);
see `backend/.env.example` for the variable names. With no keys set, the app runs with the template
explanation and no link lookups. API docs: http://localhost:8000/docs

Frontend (Node 20.19+ or 22.12+, as required by Vite 8):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

The frontend calls the backend on the same host at port 8000 unless `VITE_API_BASE_URL` is set
(`frontend/.env.example`). A phone on the same Wi-Fi can open `http://<laptop-LAN-IP>:5173`; add that origin
to `CORS_ALLOWED_ORIGINS` in `.env` first. Browsers allow the camera only on `https://` or `localhost`, so camera
capture does not work over a plain `http://` LAN address (screenshot upload and paste still do).

Screenshot OCR downloads the tesseract.js engine and language data from the jsDelivr CDN on first use (then
the browser caches them), so the first extraction needs an internet connection. Only these static files are
fetched; the image itself stays on the device.

## Tests

```bash
cd backend && .venv/Scripts/python -m pytest -q     # 284 tests, no network needed
cd frontend && npm test                              # 143 tests
cd frontend && npm run typecheck                     # TypeScript, no emit
cd frontend && npm run build                         # production build to frontend/dist
```

Tests use disabled or mocked providers; they do not call Groq, Gemini or VirusTotal.

## Deploy to Render

[render.yaml](render.yaml) defines two services: the API (`backend`, Python 3.11.9) and the static
site (`frontend`, SPA rewrite `/*` → `/index.html`). No secret is stored in the file. The Blueprint sets
`ENVIRONMENT=production`, `LLM_PROVIDER=groq`, `GROQ_ENABLED=true`, `GEMINI_ENABLED=false` and
`VIRUSTOTAL_ENABLED=false`.

1. Render dashboard → **New → Blueprint** → select this repository. It creates `namma-kavacham-api`
   and `namma-kavacham-web`.
2. Render prompts for the values marked `sync: false`:
   - `GROQ_API_KEY`: needed for AI explanations. Without it, reports use the template explanation.
   - `VIRUSTOTAL_API_KEY`: optional. Link lookups also need `VIRUSTOTAL_ENABLED=true`, which you set in the
     dashboard afterwards.
   - `CORS_ALLOWED_ORIGINS` and `VITE_API_BASE_URL`: the two service URLs are not known yet; leave them blank.
3. After the first deploy, copy each service's URL and set:
   - API → `CORS_ALLOWED_ORIGINS` = the static site origin, e.g. `https://namma-kavacham-web.onrender.com`
     (exactly one origin, no trailing slash or path).
   - Static site → `VITE_API_BASE_URL` = the API URL, e.g. `https://namma-kavacham-api.onrender.com`.
4. Redeploy **both** services. `VITE_API_BASE_URL` is read at build time, so the site must be rebuilt.
5. Check `https://<api>/healthz` returns `{"status":"ok",...}` with `"ai_provider":"groq"` (or `"template"` if no
   key is set), then run a sample check from the site.

To use Gemini instead of Groq, set `LLM_PROVIDER=gemini`, `GEMINI_ENABLED=true` and add `GEMINI_API_KEY` in the
dashboard (it is not part of the Blueprint).

With `ENVIRONMENT=production` the API hides `/docs` and `/openapi.json`. On Render's free plan, services sleep
when idle; open `/healthz` a minute before a demo to wake the API. The Blueprint does not pin a Node version for
the static site; if the build fails on Node, set `NODE_VERSION` (20.19+ or 22.12+) in its environment.

This repository has not been verified against a live Render deployment as part of Phase 5.

**Frontend on Vercel instead:** import the repo with Root Directory `frontend` and the Vite preset (default
build settings), and set `VITE_API_BASE_URL` to the backend URL. [frontend/vercel.json](frontend/vercel.json)
rewrites every route to `index.html` so that opening or refreshing `/analyze` works. Add the Vercel URL to the
backend's `CORS_ALLOWED_ORIGINS`.

## Known limitations

- **Screenshot OCR is best-effort.** Tesseract can misread small fonts, stylised sender chips, numbers and
  mixed Tamil-English text. The UI shows the recognition confidence, warns when it is low, lets the user
  correct the text, and requires the review-and-confirm step before anything is submitted. First use needs internet access to download the
  OCR engine and language data from the jsDelivr CDN.
- **Camera needs a secure context** (`https://` or `localhost`).
- **Read-aloud depends on the device.** Tamil is read aloud only if the device or browser has an on-device
  Tamil voice; otherwise the app says so. Online (remote) voices are deliberately not used.
- **Tanglish coverage is pattern-based.** Threats are detected only when a service word (account, SIM,
  EB, Aadhaar…) precedes the verb (`block aagidum`). An advisory that quotes a scam phrase
  ("block aagidum nu varra SMS…") can still score MEDIUM, and an English warning that quotes a full scam line
  ("scammers send 'your account will be blocked today, share OTP'") scored HIGH in validation.
- **Groq free-tier quota** (at the time of Phase 4: 30 RPM, 8k tokens/min, 1k requests/day for gpt-oss-20b;
  check current limits in the Groq console). When the quota is exhausted (HTTP 429) every report falls back to
  the template explanation. The risk result is unaffected; use a key with quota for live demos.
- **Curated KB is static.** Seven services; a named service outside it is `not_found_in_curated_kb`, never "safe".
  Tamil Nadu's Magalir Urimai Thogai is not covered (see [docs/government-kb-coverage.md](docs/government-kb-coverage.md)).
- **Tamil wording has not been reviewed by a native speaker.** See [docs/tamil-review.md](docs/tamil-review.md).
  Its suggestions are documentation only; none are applied in the app.
- **PM-JAY and NSP entries (Phase 5).** No helpline is listed for either, because none was confirmed from a
  fetched official page. `pmjay.gov.in` is listed as official on the strength of a PIB release; the site itself
  did not respond when checked. The Tamil names of both schemes are translations, not verified official names.
- **UPI indicator is context-based.** It cannot tell a personal UPI ID from a merchant or government one; it
  fires only when the message also has a government, benefit or fee context. The older payment rule still
  treats any UPI ID as a payment request, including a friend's.
- **Negation is window-based.** An advisory with more than four words between "never"/"do not" and the example
  (for example "never pay to any UPI ID like abc@ybl") can still be flagged.
- **No manual device testing yet.** Android Chrome, iOS Safari, Firefox, local Tamil voices, camera capture,
  real screenshot OCR, mixed Tamil-English input, keyboard and screen-reader use, and the 390px layout have not
  been tested by hand.
- If a client does upload a screenshot file to the API, uploads over 1 MB are spooled by the multipart parser to
  an OS temp file that is deleted when the request ends; the app itself never stores or logs images.
