# CivicInsight AI: architecture, methods and limits

> **Principle.** Official government sources provide the evidence. NVIDIA NIM understands the citizen's language
> and explains the evidence. Deterministic engines make every decision. Missing data is never a conclusion.

## 1. Architecture

```
                      ┌──────────────── React/Vite (Vercel) ────────────────┐
                      │ Home · Ask/Verify · Find schemes · Scheme page +    │
                      │ eligibility · Report a need · Dashboard · Hotspot   │
                      │ detail · Languages · Stay Safe (/safety, /analyze)  │
                      └───────────────────────┬─────────────────────────────┘
                                              │ JSON / multipart
┌─────────────────────────────── FastAPI (Render) ─────────────────────────────────────────┐
│ /v1/schemes/*  Government Intelligence          /v1/development/*  Development Intel.     │
│   understand ─► curated KB ─► verify (rules)      classify ─► store ─► aggregate ─► gap    │
│        │          │ miss                           (rules + optional Sarvam-M, closed      │
│        │          ▼                                 vocabulary)      ─► priority ─► hotspot│
│        │    official retrieval (registry ─► fetch ─► chunk ─► Nemotron/keyword rank)       │
│        ▼          ▼                                                   ─► policy insight    │
│   Sarvam-M: understanding (consent) · explanation/translation (validated, labelled)       │
│ /v1/analyze    Stay Safe (unchanged: rules, risk engine, URL analysis, VirusTotal, ML)     │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

Code: `backend/app/civic/` (`languages.py`, `settings.py`, `nim/`, `retrieval/`, `schemes/`, `development/`),
data: `backend/app/data/civic/`. The Stay Safe pipeline (`app/api/analyze.py` and `app/services/*`) is untouched.

## 2. NVIDIA NIM

| Role | Model (env) | Used for | Never used for |
|---|---|---|---|
| Chat | `NVIDIA_NIM_SARVAM_MODEL` = `sarvamai/sarvam-m` | query understanding (closed JSON vocabulary), explanation, translation, policy insight | verification status, eligibility, priority, scheme facts |
| Embeddings | `NVIDIA_NIM_EMBEDDING_MODEL` = `nvidia/nemotron-3-embed-1b` | ranking official passages (`input_type` query/passage) | anything else |

* `NIMProvider` → `SarvamMProvider`, `NemotronEmbeddingProvider` (`app/civic/nim/provider.py`): OpenAI-compatible
  HTTP, one retry on 429/5xx, safe error reasons only, guided JSON (`nvext.guided_json`) with a retry without it if an
  endpoint rejects it, `<think>` blocks stripped.
* **Availability note (26 Sep 2026):** `nvidia/nemotron-3-embed-1b` is in the public hosted catalog;
  **Sarvam-M is not listed there.** The model id and endpoint are configurable; run `scripts/check_nim.py` with your key.
* AI is off unless `AI_ENABLED=true` **and** a key is set. With AI off (or NIM failing) every feature still works
  deterministically, and responses say so (`explanation.status`, `understanding.method`, `/v1/meta/ai`).

### Guards (`app/civic/nim/guard.py`)
* **PII minimisation** before any call: Aadhaar-like, PAN, phone, email, OTP-near-keyword, UPI ids → `[kind]`.
* **Consent:** citizen text (chat or query embedding) is sent only when the request has `ai_consent: true`, which
  the UI shows only when AI is enabled. Explanations/insights never receive citizen text, only decided results and
  public official evidence.
* **Delimited prompts** (`<CITIZEN_MESSAGE>`, `<OFFICIAL_GOVERNMENT_EVIDENCE>`, `<VERIFICATION_RESULT>`,
  `<DEVELOPMENT_FACTS>`), closing tags stripped from content, canary token.
* **Output validation:** scheme ids must be in the catalog; a scheme name must appear verbatim in the citizen's text;
  tags/profile/category values must be in fixed vocabularies; explanations are rejected if they contain any number or
  URL not in the evidence, any non-`.gov.in/.nic.in` URL, the canary or key, or are not in the requested script;
  translations must preserve numbers, URLs, domains, abbreviations and helplines. Rejected → deterministic template
  (translated when possible, else English, always labelled).

## 3. Official-source retrieval (`app/civic/retrieval`)
* **Registry, not search.** Only pages in the reviewed registry are fetched: every source cited by the curated KB
  plus `data/civic/official_sources.json` (Stand-Up India, PMAY-U about, Udyam, JJM, SBM-G, NHM, DBT, …).
  No general web search exists (MyScheme's API needs a key; its pages are JavaScript-only).
* `https` on `*.gov.in` / `*.nic.in` only; TLS always verified; redirects off those domains, non-HTML, >3 MB and
  JavaScript shells (<200 chars of text) are rejected. User-supplied URLs are parsed, **never fetched**.
* Pages are chunked (~700 chars, sentence overlap), ranked by Nemotron cosine similarity (with consent and AI on) or
  a script-agnostic keyword score, and cached for 6 h. Each evidence item carries URL, title, domain, retrieval time,
  passage and an **exact quote** (a verbatim substring of the page).
* Fetched content is evidence for that query only. **It never enters the curated KB**; KB updates are a manual,
  reviewed process (`scripts/fetch_official_text.py`, `scripts/verify_scheme_sources.py`).

## 4. Verification flow (`app/civic/schemes/verify.py`)

```
citizen text ─► understand (rules; Sarvam-M only with consent) ─► KB match?
   ├─ yes ─► rule checks on structured KB facts ─► status
   └─ no  ─► official retrieval ─► does an official passage mention the named scheme?
                ├─ sources unreadable / nothing named ─► UNABLE_TO_VERIFY
                ├─ no mention ─► NOT_FOUND ("not found in the official sources checked; this does not mean it is fake")
                └─ mention ─► amount/link checks against those passages ─► SUPPORTED / PARTIALLY_SUPPORTED
```

| Status | Rule |
|---|---|
| SUPPORTED | every checked aspect is backed by the official source |
| PARTIALLY_SUPPORTED | scheme confirmed; some claimed detail not stated by the source |
| CONTRADICTED | an official source settles the point differently: an amount for the **same period** (e.g. "₹10,000 every year" vs PM-KISAN's quoted "₹6,000 per year"), or an application link on a lookalike of the scheme's official domain |
| NOT_FOUND | official sources were read and none mentions the named scheme |
| UNABLE_TO_VERIFY | "Unable to verify from the currently available official sources." |

An amount the source does not state for that period is **not covered**, never false.

## 5. Scheme knowledge base v2 (`data/civic/schemes/*.json`)
Every statement (description, benefits, eligibility criteria, documents, steps) is tied to a source and a quote;
the loader rejects any statement whose quote is not among the source's recorded verbatim quotes, any non-official
source/channel URL, unknown attributes/tags/languages, and duplicate aliases. `criteria_complete` is true only when the
sources state the full rules. All quotes were checked against the live pages on 2026-09-26.

| Scheme | Official source(s) |
|---|---|
| PM-KISAN | pmkisan.gov.in |
| PM Ujjwala Yojana | pmuy.gov.in (apply, about, home) |
| PM Jan-Dhan Yojana | pmjdy.gov.in/scheme |
| PM Vishwakarma | pmvishwakarma.gov.in |
| PM SVANidhi | pmsvanidhi.mohua.gov.in |
| PMAY-Gramin | pmayg.dord.gov.in (about, "Am I eligible?") |
| PMAY-Urban 2.0 | pmaymis.gov.in |
| PMSBY, PMJJBY, Atal Pension Yojana, PM MUDRA | financialservices.gov.in |
| MGNREGA | nrega.dord.gov.in |
| National Scholarship Portal | scholarships.gov.in |

**Attempted and dropped** (no validated official text on 2026-09-26): AB PM-JAY (pmjay.gov.in unreachable,
nha.gov.in certificate error, PIB 403), Sukanya Samriddhi (nsiindia.gov.in certificate error, India Post page 404),
PMFBY (JavaScript-only), PMMVY (no readable content), Jal Jeevan Mission (no citizen-facing quotable text; kept in the
retrieval registry). State schemes: FUTURE.

**Eligibility outcomes:** `eligible_on_available_info` (all rules checkable, complete and met), `possibly_eligible`
(checkable rules met, others must be confirmed with the office), `not_enough_information`, `criteria_not_satisfied`.
Questions exist only for machine-checkable attributes; the implementing authority decides.

## 6. Development Intelligence (`app/civic/development`)
* **Taxonomy:** 12 categories × issue types, keywords in English/Hindi/Tamil/romanised; adding one = one entry.
* **Classifier:** keyword scoring (issue words break ties) → category, issue type, urgency, language; unclear → the
  citizen chooses. Sarvam-M only with consent, only when keywords fail or the script is not covered, only values in the
  taxonomy. The citizen's own choice always wins.
* **Aggregation:** issue = (demo locality or State+District) × category; clusters (complaint themes) = issue types.
  Public outputs contain counts and theme labels only — never citizen text. "My reports" returns only ids the
  caller holds (kept in tab memory).
* **Development Priority Engine** (weights configurable via `DEV_WEIGHT_*`):

| Component | Default weight | Value (0–1) | Missing data |
|---|---|---|---|
| Citizen demand | 30 | `log(1+reports)/log(1+150)` | always available |
| Population impact | 25 | `population / 200,000` | not assessed: "Population impact cannot be assessed from available data." |
| Infrastructure gap | 20 | `1 − (facilities per 10k ÷ analytical benchmark)` | not assessed: "Infrastructure data unavailable." |
| Urgency | 10 | `(high + 0.5·medium) / reports` | always available |
| Investment gap | 15 | 1.0 no matching project; proposed .8, delayed .7, planned .6, approved .5, ongoing .3, completed .2 | not assessed: "No matching investment information is available in the current dataset." |

Score = Σ(weight·value) ÷ Σ(assessed weights) × 100, with each component's points shown. If assessed weight
< 50 % → **unable to assess** (no score). Levels: 80–100 Critical, 60–79 High, 40–59 Medium, 0–39 Lower.
Benchmarks are analytical references for the demo, **not official norms**. Gap level: mean of assessed demand rate,
infrastructure gap and investment gap (≥ .66 high, ≥ .33 medium) with reasons. Hotspot: ≥ 20 reports and High/Critical.
The score is an analytical aid, not a government decision.

## 7. Data provenance
| Dataset | Type | Notes |
|---|---|---|
| Scheme KB | official | verbatim quotes from `.gov.in` pages, retrieval dates |
| State/UT list (36) | official | dbtbharat.gov.in, 2026-09-26 |
| Demo localities, demographics, infrastructure, projects, 535 requests | **demo (synthetic)** | `scripts/generate_dev_demo_data.py` (seed 26); real district names for geography only; fictional "Demo Area A/B/C"; every figure invented; one area without demographics and two without infrastructure on purpose |

Every API response carries `source.type` (`demo` / `official`); the UI shows "Demonstration data" vs
"Official/public data" badges and a persistent demo banner on the dashboard. Replacing demo data = dropping official
files with `source.type: "official"` into `data/civic/development/`.

## 8. Languages
All 22 Scheduled Languages + English are selectable (native names, RTL for Urdu/Kashmiri/Sindhi, per-script Noto
fonts). Support is per capability and published at `/v1/meta/languages`:
* **UI:** authored in English, Hindi, Tamil (Hindi/Tamil await native review); others show English with a notice.
* **Understanding:** rules for English/Hindi/Tamil (+ romanised); Sarvam-M (when enabled) for bn, gu, kn, ml, mr, or,
  pa, te; others none.
* **Scheme text:** English originals; machine translation on request (AI on), validated and labelled.
* Voice: browser Web Speech API, opt-in with a notice (audio may go to the browser vendor); `xx-IN` locales; typing
  always works. Speech availability depends on the browser.

## 9. Privacy & security
No accounts, cookies or analytics; localStorage holds only the language choice. Photos are type/size-checked and
discarded (only `photo_attached` is kept). Citizen text is PII-minimised before storage and before any AI call.
Logs carry codes and counts only (redacting logger + new sensitive keys). CORS, body limits and the generic 500 from
the existing app apply. No secrets in the repo; the NIM key is never logged, echoed or returned.

## 10. Status

| Feature | Status |
|---|---|
| Scheme KB (13 central schemes), verify, discover, eligibility, official channels | IMPLEMENTED |
| Official-source retrieval (registry, exact quotes, keyword ranking) | IMPLEMENTED |
| Nemotron embedding ranking, Sarvam-M understanding/explanation/translation | IMPLEMENTED, **not yet verified against live NIM** (Sarvam-M not in the hosted catalog) |
| Development requests, classification, aggregation, gap, priority, hotspots, dashboard, insight | IMPLEMENTED |
| Demographic / infrastructure / investment data, citizen request volume | DEMO |
| 22-language support | PARTIAL (see §8) |
| Voice input | PARTIAL (browser-dependent, opt-in) |
| Photo analysis | NOT IMPLEMENTED (photos discarded) |
| Persistence (requests survive restarts), authentication, rate limiting | NOT IMPLEMENTED |
| State schemes, open web search, official demographic/infra/investment feeds, native language review | FUTURE |

## 11. Known limitations
* Requests live in process memory: restarts (Render free tier sleeps) reset citizen reports to the demo seed.
* No rate limiting: with AI on, repeated requests cost NIM calls; public report submission is capped at 5,000 in memory.
* Keyword classifier/understanding misses unseen phrasing; answer options (e.g. gender, occupation) and backend
  category/issue labels are English in the UI.
* The grounding validator checks numbers/URLs/script, not meaning: an AI sentence could still misstate a stance. The
  deterministic status is always shown above the AI text and labelled.
* Retrieval covers only the registry; a real scheme outside it may be NOT_FOUND (never called fake).
* Several official sites fail TLS validation or serve JavaScript-only pages; they are excluded, not bypassed.
* Frontend main bundle ≈ 519 kB (Leaflet is split out and loaded only when the map is opened; OSM tiles are a
  third-party call shown with a notice).

## 12. Path to real-world deployment
Database + retention policy for requests; authentication/role separation for policymaker views; rate limiting and
abuse controls; official data feeds (Census/NFHS-style demographics, facility registries, PFMS/project MIS) replacing
`demo` files; state scheme KBs with a review workflow; native-speaker review of every language; evaluated Sarvam-M
quality per language before marking support; a government integration only with explicit agreements.
