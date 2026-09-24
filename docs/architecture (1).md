# Namma Kavacham AI — Architecture (v2, Scope-Frozen)

## 1. Architecture Goal

Build a web-first, technically credible, explainable, bilingual (English/Tamil) citizen-safety tool in 2.5 days.

Core principle:

> **AI understands → Deterministic security engine verifies → Risk engine decides → AI explains.**

This revision removes the native Android intake path, live government-domain search, and the second threat-intel provider from the v1 architecture. Those remain valid research but are out of scope for this build.

---

## 2. High-Level Architecture

```text
                         ┌──────────────────────┐
                         │       CITIZEN        │
                         │ Paste / Type / Upload │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ React + Vite +       │
                         │ Tailwind Frontend    │
                         │ (Review & Confirm)   │
                         └──────────┬───────────┘
                                    │ HTTPS/JSON
                                    ▼
                    ┌──────────────────────────────┐
                    │     FASTAPI BACKEND          │
                    │                              │
                    │  POST /v1/analyze            │
                    └──────────────┬───────────────┘
                                   │
     ┌───────────────┬────────────┼────────────┬───────────────┐
     ▼               ▼            ▼            ▼               ▼
┌──────────┐  ┌─────────────┐ ┌─────────┐ ┌──────────────┐ ┌──────────┐
│Provenance│  │ Deterministic│ │VirusTotal│ │ Government   │ │  Gemini  │
│Normalizer│  │ Message/URL  │ │ Adapter  │ │ Claim        │ │ (explain │
│          │  │ Rules        │ │(flagged) │ │ Detector +   │ │  only)   │
│          │  │              │ │          │ │ Curated KB   │ │          │
└────┬─────┘  └──────┬───────┘ └────┬─────┘ └──────┬───────┘ └────┬─────┘
     │               │              │              │              │
     └───────────────┴──────┬───────┴──────────────┘              │
                             ▼                                     │
                   ┌─────────────────────┐                         │
                   │ EVIDENCE NORMALIZER │                         │
                   └──────────┬──────────┘                         │
                              ▼                                    │
                   ┌─────────────────────┐                         │
                   │ DETERMINISTIC RISK  │                         │
                   │       ENGINE        │                         │
                   │ (LOW/MED/HIGH/CRIT) │                         │
                   └──────────┬──────────┘                         │
                              └─────────────────┬───────────────────┘
                                                 ▼
                                   ┌─────────────────────────┐
                                   │   RESPONSE COMPOSER     │
                                   │ Evidence · Explanation  │
                                   │ Missing data · Safe next│
                                   │ steps · EN/TA           │
                                   └───────────┬─────────────┘
                                               ▼
                                            CITIZEN
```

Gemini sits beside the risk engine, not above it: it only explains, translates, and helps interpret ambiguous claim language. It cannot change a risk level or an evidence entry the deterministic engine produced.

---

## 3. AI Agent Architecture

### Number of agents: 1

One **Namma Kavacham Orchestrator** (FastAPI backend), with modular services — not independent autonomous agents:

```text
Namma Kavacham Orchestrator
│
├── Intake & Provenance
│   ├── input validation (paste / manual / screenshot upload)
│   ├── provenance tagging (pasted_text, manual_entry, ocr, ...)
│   └── review/confirmation gate before any external call
│
├── Deterministic Security Analysis
│   ├── message rules (urgency, OTP/PIN/payment requests, impersonation phrasing)
│   ├── URL extraction, normalization, domain checks
│   └── VirusTotal adapter (feature-flagged)
│
├── Government Claim Verification
│   ├── claim detection (ambiguity-preserving)
│   └── curated static KB comparison (5 categories)
│
├── Risk Aggregation
│   ├── evidence weighting across all signals above
│   └── LOW / MEDIUM / HIGH / CRITICAL + evidence list
│
└── Explanation
    ├── Gemini: English + Tamil explanation, translation, ambiguous-language interpretation
    └── never overrides deterministic risk level or evidence
```

---

## 4. Message/Text Analysis Flow

```text
Pasted / typed text
 │
 ▼
Provenance tag = pasted_text | manual_entry
 │
 ▼
User review & explicit confirmation
 │
 ▼
URL extraction (if any)
 │         │
 │         ▼
 │    URL normalization → domain checks → VirusTotal (if enabled)
 │
 ▼
Deterministic message rules
 (urgency, credential/payment requests, impersonation phrasing,
  APK-install instructions)
 │
 ▼
Government claim detector
 (ambiguity preserved — "PM scheme" stays unresolved, never guessed)
 │
 ▼
Curated KB comparison
 (supported / partially_supported / contradicted / not_found / unable_to_assess)
 │
 ▼
Risk Engine → risk level + evidence
 │
 ▼
Gemini explanation (EN + TA)
 │
 ▼
Citizen
```

Original submitted text is retained only in-memory for the duration of the request; it is never logged raw.

---

## 5. URL Verification

```text
URL (typed, or extracted from message text)
   │
   ▼
Validate & normalize (scheme, hostname, path, query)
   │
   ▼
Deterministic domain/lookalike checks
   │
   ▼
VirusTotal lookup (feature-flagged)
   ├── malicious
   ├── suspicious
   ├── not_found        ← NOT the same as "clean"
   ├── clean_or_harmless
   └── unavailable       ← provider down / timeout / quota — NOT "safe"
   │
   ▼
Risk Engine
```

**Rule:** `not_found` and `unavailable` must never be interpreted or displayed as "safe." A missing report is missing information, not a clean result.

---

## 6. Screenshot / OCR Flow (optional, best-effort)

```text
Screenshot upload
   │
   ▼
User consent to upload
   │
   ▼
OCR (best-effort; may be stubbed if time-constrained)
   │
   ▼
Extracted text shown to user, editable
   │
   ▼
User confirms / corrects
   │
   ▼
Enters the same Message/Text Analysis Flow above,
   with source = "ocr" or "user_corrected_ocr"
```

All OCR-derived fields are labeled `verification_status: "unverified"` regardless of extraction confidence. The image is deleted after analysis; it is never persisted.

---

## 7. Government Claim Verification (static curated KB — no live search)

```text
Message / claim text
      │
      ▼
Government claim detector
 (departments, schemes, Aadhaar/PAN/passport, deadlines, fees,
  requested actions, sensitive-data requests)
      │
      ▼
Ambiguity check
 (unnamed/unclear scheme → stays ambiguous, never guessed)
      │
      ▼
Curated static JSON knowledge base (5 categories)
 1. Aadhaar & identity
 2. Schemes & benefits
 3. Income tax
 4. Passport
 5. Cybercrime reporting
      │
      ▼
Comparison result:
 supported_by_curated_kb | partially_supported_by_curated_kb |
 contradicted_by_curated_kb | not_found_in_curated_kb |
 not_government_related | unable_to_assess
      │
      ▼
Risk Engine
```

**This is explicitly NOT live web verification.** The response must state that the comparison was against a curated static dataset, not a live search of government websites. A scheme existing in the KB does not prove a specific message is genuine; an official domain mentioned in a message does not validate every instruction in it.

---

## 8. Threat Intelligence (VirusTotal only — MVP)

```text
Extracted URL
      │
      ▼
sha256(normalized_url) cache lookup
      │
      ▼
VirusTotal API (behind VIRUSTOTAL_ENABLED flag)
      │
      ▼
Normalized result: {provider, indicator, status, confidence, checked_at, available}
      │
      ▼
Risk Engine
```

URLhaus, Google Web Risk, and PhishTank are Phase 2 — the `ThreatIntelProvider` protocol is written to support them later without changing the risk engine's interface, but only VirusTotal ships in the MVP.

---

## 9. Risk Engine

```text
                ┌─ Deterministic message indicators
                ├─ URL/domain checks
Input ──────────┼─ VirusTotal evidence (or "unavailable")
                ├─ Government-claim KB comparison
                └─ Input provenance / missing-metadata flags
                         │
                         ▼
                Evidence aggregation
                         │
                         ▼
                LOW / MEDIUM / HIGH / CRITICAL
```

Rules:
- A confirmed malicious URL is a strong signal on its own.
- Missing sender/provenance information is not itself proof of fraud.
- A provider outage or `unable_to_assess` is never silently converted into "safe."
- Conflicting signals (e.g. legitimate-looking KB match + unverified payment request) stay visible in the evidence list, not collapsed into one number.
- `risk_score` (if shown) is an internal explainability aid, never a presented probability.

---

## 10. Backend Module Structure

```text
app/
├── main.py
├── api/
│   └── analyze.py
├── schemas/
│   ├── analysis.py
│   ├── threat_intelligence.py
│   └── government_claim.py
├── services/
│   ├── url_analyzer.py
│   ├── message_rules.py
│   ├── threat_intelligence/
│   │   ├── base.py            # ThreatIntelProvider protocol
│   │   └── virustotal.py
│   ├── government/
│   │   ├── claim_detector.py
│   │   └── government_kb.json
│   ├── evidence_normalizer.py
│   ├── risk_engine.py
│   └── ai_explainer.py
```

## 11. Frontend Structure

```text
frontend/src/
├── pages/
│   ├── Home.jsx
│   └── Analyze.jsx        # paste / manual / upload + review/confirm
├── components/
│   ├── ReviewConfirm.jsx
│   ├── RiskCard.jsx
│   ├── EvidenceList.jsx
│   ├── GovernmentClaimCard.jsx
│   ├── MissingDataNotice.jsx
│   ├── SafeNextSteps.jsx
│   └── LanguageToggle.jsx   # EN / TA
├── services/
│   └── api.js
└── App.jsx
```

---

## 12. API Surface (single endpoint for the MVP)

```http
POST /v1/analyze
```

**Accepts:** reviewed/confirmed text, optional screenshot-derived text, optional URL, language preference, provenance metadata.

**Returns:**
```json
{
  "risk": { "level": "high", "score": 82, "verdict_scope": "message-risk assessment, not sender identity verification" },
  "evidence": [ { "signal": "credential_or_payment_request", "source": "message_body", "confidence": "high" } ],
  "url_intelligence": { "provider": "virustotal", "status": "malicious", "available": true },
  "government_claim": { "claim_status": "partially_supported_by_curated_kb", "sources": [ { "url": "https://www.myscheme.gov.in/" } ] },
  "missing_metadata": ["original_sms_timestamp"],
  "safe_next_steps": ["Do not click the link or share OTP, PIN, password, or UPI PIN.", "Verify through the organization's official app or website typed manually."],
  "explanation": { "en": "...", "ta": "..." }
}
```

A separate Android-specific endpoint is not required for the MVP.

---

## 13. Security Boundaries

- Treat all user-submitted content as untrusted.
- Explicit review/confirmation step before any content leaves the browser.
- Input size limits on text and uploaded images.
- SSRF-safe handling if the backend ever fetches a URL directly.
- VirusTotal API key stored server-side only — never in the frontend bundle or client code.
- No raw SMS/message body, screenshot, OTP, phone number, or API key in logs.
- Gemini treats message text as delimited, untrusted content; it cannot follow instructions embedded inside it (prompt-injection resistance) and cannot override deterministic findings.
- HTTPS only, in both local and Render environments.

---

## 14. Reliability / Fallback Architecture

```text
                    Request
                       │
                       ▼
              Deterministic Local Analysis
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
        Rules      URL/Domain   Curated KB
          │            │            │
          └────────────┼────────────┘
                       ▼
                  Risk Engine
                       ▲
                       │
              ┌────────┴────────┐
              │                 │
          VirusTotal        Gemini
          (optional)       (optional)
```

The deterministic path (rules + URL/domain checks + curated KB) must produce a usable risk verdict even if VirusTotal and Gemini are both unavailable. This is the actual safety claim behind the whole product — it must never be allowed to regress.

---

## 15. Deployment Architecture

```text
Primary target: laptop, local network
  Phone/browser → http://<laptop-LAN-IP>:8000 → FastAPI (uvicorn --reload)

Conditional target: Render (only if local demo is stable and time remains)
  Browser → https://<service>.onrender.com → same FastAPI app, same /v1/analyze contract
  VirusTotal key set via Render environment variables, never in the frontend
```

Do not let Render deployment work delay or displace the four core demo scenarios.

---

## 16. Architectural Principles (v2)

1. Deterministic security checks execute before, and are never overridden by, the LLM.
2. External provider unavailability is reported as `unavailable`, never treated as a clean/safe result.
3. Every extracted or user-entered field carries explicit provenance.
4. A government service or scheme existing in the curated KB does not prove any particular message is genuine.
5. The system assesses message and claim risk — it does not authenticate sender identity.
6. The product remains useful (deterministic-only) when every external service is disabled.
7. No native Android app, no live government-web search, no second threat-intel provider in this build — these are documented as Phase 2, not silently dropped.
8. Minimize data retention; delete raw uploads/text after the response is generated.
