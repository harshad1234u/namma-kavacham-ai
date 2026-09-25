# Namma Kavacham AI (நம்ம கவசம்)

Verify before you trust. Know before you act.

A web-first, bilingual (English/Tamil) scam-risk checker for suspicious messages, links, and screenshots.
Deterministic checks decide the risk level; AI only explains; a missing or unavailable check is never shown as safe.

Scope and design decisions live in [docs/](docs/). The UI follows the Stitch reference in
[stitch_namma_kavacham_ai_ux_prototype/](stitch_namma_kavacham_ai_ux_prototype/).

## Status: Phase 3 (hardening & demo readiness)

| Area | State |
|---|---|
| `POST /v1/analyze` (paste / type / URL / screenshot upload) | Built |
| Review & explicit-consent gate before any request | Built |
| Bilingual deterministic message rules, URL/domain heuristics | Built |
| VirusTotal URL lookup (behind `VIRUSTOTAL_ENABLED`) | Built, verified live |
| Risk engine (LOW/MEDIUM/HIGH/CRITICAL + evidence) | Built |
| Curated government KB (5 categories, cited official sources) | Built — `backend/app/data/government_kb.json` |
| Government claim detection + KB comparison (6 statuses) | Built |
| Groq EN/TA explanation (`openai/gpt-oss-20b`, strict JSON schema, one bounded retry) with validation + template fallback | Built, mock-tested (`LLM_PROVIDER=groq`, `GROQ_ENABLED`, `GROQ_API_KEY`) |
| Gemini explanation | Kept, off by default (`LLM_PROVIDER=gemini`, `GEMINI_ENABLED`) |
| Redacted logging, upload validation, size limits | Built |
| Tanglish urgency ("account block aagidum") + Tanglish advisory negation | Built (Phase 3) |
| API docs hidden when `ENVIRONMENT=production`; unexpected errors return a generic 500 with no traceback | Built (Phase 3) |
| Screenshot OCR | Deferred — stub: user types the visible text |

The knowledge base is a small curated reference, not live verification. Each fact quotes its official
source; update `last_reviewed` and the `retrieved` dates when you re-check them. The AI provider never receives
the submitted message — only the deterministic findings — and cannot change the risk level.

## Run locally

Backend (Python 3.11):

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Keys and flags are read from the repo-root `.env` or `backend/.env` (both gitignored); see
`backend/.env.example` for the variable names. Set `VIRUSTOTAL_ENABLED=true` to turn on link lookups.
API docs: http://localhost:8000/docs

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

The frontend calls the backend on the same host at port 8000, so a phone on the same Wi-Fi can open
`http://<laptop-LAN-IP>:5173`. Add that origin to `CORS_ALLOWED_ORIGINS` in `.env` first.

## Tests

```bash
cd backend && .venv/Scripts/python -m pytest -q     # 194 tests, no network needed
cd frontend && npm test                              # 30 tests
```

## Deploy to Render

[render.yaml](render.yaml) defines two services: the API (`backend`, Python 3.11.9) and the static
site (`frontend`, SPA rewrite `/*` → `/index.html`). No secret is stored in the file.

1. Render dashboard → **New → Blueprint** → select this repository. It creates `namma-kavacham-api`
   and `namma-kavacham-web`.
2. When prompted for values, enter your keys (`GEMINI_API_KEY`, optionally `VIRUSTOTAL_API_KEY`). The two
   URLs are not known yet — leave them blank for now.
3. After the first deploy, copy each service's URL and set:
   - API → `CORS_ALLOWED_ORIGINS` = the static site origin, e.g. `https://namma-kavacham-web.onrender.com`
     (exactly one origin, no trailing slash or path).
   - Static site → `VITE_API_BASE_URL` = the API URL, e.g. `https://namma-kavacham-api.onrender.com`.
4. Redeploy **both** services. `VITE_API_BASE_URL` is read at build time, so the site must be rebuilt.
5. Check `https://<api>/healthz` returns `{"status":"ok",...}`, then run a sample check from the site.

With `ENVIRONMENT=production` the API hides `/docs` and `/openapi.json`. Free-plan services sleep when
idle; open `/healthz` a minute before a demo to wake the API. Set `VIRUSTOTAL_ENABLED=true` only if a key
is configured; without AI provider quota (or with `LLM_PROVIDER=template`), reports use the template explanation.

## Known limitations

- **No screenshot OCR.** Deferred deliberately: Tamil-capable OCR needs a system Tesseract install or a
  1 GB+ model, and sending screenshots to Gemini would break the rule that Gemini never sees the message.
  The UI asks the user to type the visible text.
- **Tanglish coverage is pattern-based.** Threats are detected only when a service word (account, SIM,
  EB, Aadhaar…) precedes the verb (`block aagidum`). An advisory that quotes a scam phrase
  ("block aagidum nu varra SMS…") can still score MEDIUM — the English rules share this limitation.
- **Groq free-tier quota (30 RPM, 8k tokens/min, 1k requests/day for gpt-oss-20b).** When the quota is exhausted (HTTP 429) every report falls back to the
  template explanation. The risk result is unaffected; use a key with quota for live demos.
- **Curated KB is static.** Five categories; anything else is `not_found_in_curated_kb`, never "safe".
- Uploads over 1 MB are spooled by the multipart parser to an OS temp file that is deleted when the
  request ends; the app itself never stores or logs images.
