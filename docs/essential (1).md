# Namma Kavacham AI — ESSENTIALS (v2, Scope-Frozen)

## 1. Project Identity

**Name:** Namma Kavacham AI
**Tagline:** "Verify before you trust. Know before you act."

**Theme:** AI for Digital Public Infrastructure and Governance

**One-line description:**

> A web-first, privacy-conscious scam-risk assessment tool that lets Indian citizens paste, type, or upload a suspicious message, review exactly what was received, and get an explainable risk report — checked against real URL threat intelligence and a curated set of official government information.

---

## 2. The Core Problem

Citizens receive:
- fake government SMS and benefit/subsidy messages,
- phishing URLs impersonating government portals,
- fake Aadhaar/KYC/PAN/passport notices,
- government-impersonation messages demanding OTP/payment,
- scam screenshots forwarded as "official."

The user needs a simple, honest answer:

> "Can I trust this, and what should I do next?" — without the tool pretending to know more than it does.

---

## 3. The Core Product (MVP)

### Input channels
1. **Paste text**
2. **Manually type text**
3. **Upload a screenshot** (OCR best-effort; every OCR field labeled unverified)
4. **URL** — typed directly or extracted from message text

### What it does
- Shows the user exactly what was received and requires explicit review/confirmation before any analysis.
- Runs deterministic message + URL rules first, always.
- Checks URLs against **VirusTotal** (the one external threat-intel provider in this MVP).
- Detects government-related claims and compares them against a **small, static, curated knowledge base** — not a live search.
- Produces an explainable risk report (English + Tamil) via Gemini, which explains but never overrides the deterministic verdict.

**What it explicitly is NOT in this build:** a native Android app, an SMS-reading tool, a live government-web verifier, or a multi-provider threat-intel platform. Those are documented, deliberate deferrals — not oversights.

---

## 4. Final AI Decision

### Number of AI agents: 1

One backend orchestrator (FastAPI), not multiple autonomous agents. Modules inside it:
- Intake & Provenance
- Deterministic Security Analysis (rules + URL/domain + VirusTotal)
- Government Claim Verification (curated KB)
- Risk Aggregation
- Explanation (Gemini)

---

## 5. Models & Providers

### Gemini
Used **only** for: explanation generation, English/Tamil translation, and interpreting ambiguous claim language.
**Gemini never makes the scam/not-scam decision.** It cannot override a risk level or evidence entry the deterministic engine produced. Message text is treated as untrusted, delimited content (prompt-injection resistant).

### VirusTotal
The sole external threat-intelligence provider in the MVP, behind a feature flag (`VIRUSTOTAL_ENABLED`). Key stored backend-only.

**Deferred to Phase 2:** URLhaus, Google Web Risk, PhishTank. The `ThreatIntelProvider` protocol is written so these can be added later without changing the risk engine.

---

## 6. Risk Levels

### LOW
No significant suspicious evidence detected.

### MEDIUM
Some suspicious indicators exist, but evidence is incomplete.

### HIGH
Multiple meaningful scam/impersonation indicators exist.

### CRITICAL
Strong evidence — e.g. confirmed-malicious URL combined with impersonation or credential/payment harvesting.

Always show the evidence behind the level. Never present an internal score as a calibrated probability (no "78% chance of scam").

---

## 7. URL Rules

Check: hostname, exact domain, subdomains, typos/lookalikes, suspicious paths, misleading government-style names.

**Never use this rule:** `not a government domain = scam`. A non-government domain is not automatically fraudulent.

**VirusTotal status handling:**
- `malicious` / `suspicious` → strong risk signal.
- `not_found` → **not the same as clean** — it means "no report exists," not "safe."
- `unavailable` (timeout/quota/down) → **never** shown or treated as "safe."

---

## 8. Government Claim Verification — Static Curated KB (no live search)

The MVP explicitly does **not** perform live search across government websites. It compares a detected claim against a small, hand-written JSON knowledge base covering exactly 5 categories:

1. Aadhaar & identity services
2. Government schemes & benefits
3. Income tax
4. Passport services
5. Cybercrime reporting

Each KB entry: service/scheme name, department, official domain/URL, verified fee (only if confirmed), whether OTP/PIN/payment requests are expected, source citation, last-reviewed date.

**Comparison result — one of:**
- `supported_by_curated_kb`
- `partially_supported_by_curated_kb`
- `contradicted_by_curated_kb`
- `not_found_in_curated_kb`
- `not_government_related`
- `unable_to_assess`

**Ambiguity rule:** vague phrases ("PM scheme") are never auto-mapped to a specific scheme. The claim extractor preserves uncertainty rather than guessing.

**Disclosure requirement:** the report must state plainly that this is a comparison against a curated static dataset, not live verification of current government records. A real scheme existing in the KB does not prove a specific message is genuine.

---

## 9. Multilingual Strategy (v2 — scoped down from 6 languages to 2)

**Input:** English or Tamil, pasted/typed/OCR'd.
**Output:** the same risk report generated in **English and Tamil** via Gemini.

Additional languages (Hindi, Telugu, Kannada, Malayalam) are a documented Phase 2 item, not part of this MVP — don't commit to demoing them.

---

## 10. Sender / Provenance Handling

Because this is web-first (no Android Sharesheet), sender metadata is essentially never available automatically. The system:
- Defaults sender to unknown/unavailable unless the user explicitly types it in.
- Never infers a sender identity from a phone number appearing inside the message body (it may be a scam callback number).
- Labels every field with `provenance` (`pasted_text`, `manual_entry`, `ocr`, `user_corrected_ocr`, `url_input`) and `verification_status` (default `unverified`).
- Never claims a sender is "verified" without a defined, auditable authority — which this MVP does not have.

---

## 11. Required API

```
POST /v1/analyze
```

Single endpoint. Accepts reviewed text, optional screenshot-derived text, optional URL, language preference, provenance metadata. Returns risk level + evidence, VirusTotal result/availability, government-claim comparison, missing-metadata notices, safe next steps, and English/Tamil explanation.

No separate Android-specific endpoint is needed.

---

## 12. Final Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + Tailwind |
| Backend | Python + FastAPI |
| LLM | Gemini (explanation/translation only) |
| Threat Intel | VirusTotal (feature-flagged); URLhaus/Web Risk/PhishTank deferred |
| Government Knowledge | Curated static JSON (5 categories) — no live search, no RAG |
| Security | Python deterministic rules |
| Database | None required for MVP |
| Deployment | Laptop (primary) — Render (conditional, only if time remains) |
| Native app | None — web-first only |

---

## 13. Privacy Essentials

**Do:**
- Process statelessly; delete uploaded screenshots and raw request payloads after the response is generated.
- Require explicit review/confirmation before any content is sent for analysis.
- Mask sender values by default if shown at all (e.g. `+91******3210`).
- Keep VirusTotal (and any future provider) keys backend-only.
- Redact logs — never log raw message text, screenshots, OCR output, phone numbers, or API keys.
- Cache threat-intel results by `sha256(normalized_url)` only — never cache the full message body.

**Be careful:**
- Sending a URL to VirusTotal exposes that URL to a third party — disclose this if asked.

---

## 14. Fallbacks

**Gemini fails →** deterministic rules + URL/domain checks + curated KB comparison still produce a full risk report (just without a generated natural-language explanation).

**VirusTotal fails/unavailable →** continue with deterministic rules and KB comparison; response explicitly marks URL intelligence as `unavailable`, never "safe."

**KB has no matching entry →** return `not_found_in_curated_kb` or `unable_to_assess`; continue the rest of the analysis; state plainly what wasn't checked.

**Everything external fails →** deterministic-only analysis still returns a usable risk level — this path must never break.

---

## 15. MUST BUILD (MVP)

- [ ] React + Vite web frontend (paste / manual entry / screenshot upload)
- [ ] Review & confirmation screen before any analysis request
- [ ] FastAPI backend, single `POST /v1/analyze` endpoint
- [ ] Provenance schema on every field
- [ ] URL extraction & normalization
- [ ] Deterministic message + URL risk rules
- [ ] VirusTotal adapter behind a feature flag
- [ ] Government claim detector (ambiguity-preserving)
- [ ] Curated static government KB (5 categories)
- [ ] Deterministic risk engine combining all signals
- [ ] Gemini explanation in English and Tamil
- [ ] Local laptop demo (phone/browser on same LAN)
- [ ] Privacy-preserving logging (no raw content, no secrets)
- [ ] All four demo scenarios (A–D, see below) working end-to-end

---

## 16. Explicitly Deferred / Do Not Build

- Native Kotlin Android app / Android Sharesheet intake
- `READ_SMS`, `RECEIVE_SMS`, notification-listener, accessibility-service access
- Background monitoring of any kind
- Android-to-web handoff tokens
- Live government-domain search / RAG over government websites
- URLhaus, Google Web Risk, PhishTank integrations
- Full redirect-chain analysis
- Persistent user accounts or long-term message storage
- Mandatory Render deployment (conditional only)
- Hindi/Telugu/Kannada/Malayalam output (English + Tamil only for this MVP)
- Guaranteeing sender identity verification of any kind

---

## 17. Demo Scenarios (all four must work)

**A — Suspicious/malicious URL:** extract → normalize → deterministic checks → VirusTotal → show evidence → recommend not clicking / not entering credentials.

**B — Government benefit scam:** detect the benefit claim (preserve ambiguity if scheme is unnamed) → compare to curated KB → flag unverified payment instruction → raise risk.

**C — Government impersonation:** detect impersonation + urgency + OTP request → compare relevant claim to KB → explicitly state sender is unauthenticated → direct to the official source, not the message's contact info.

**D — KB/provider unavailable:** return `not_found_in_curated_kb` or `unable_to_assess` / VirusTotal `unavailable` → continue deterministic analysis → clearly state what wasn't checked → never render as "safe."

---

## 18. The One Sentence to Remember

> Namma Kavacham does not secretly read messages or claim to authenticate a sender. The user deliberately shares a message, reviews it, and receives an explainable risk assessment that combines deterministic checks, VirusTotal URL intelligence, and comparison against a curated set of official government information — reporting evidence, uncertainty, and limitations instead of assuming a message is genuine or fraudulent.

---

## 19. Final Freeze (v2)

**Agents:** 1
**Intake:** Web only (paste / manual / screenshot) — no native Android
**LLM:** Gemini — explanation/translation only, never the verdict
**Threat intel:** VirusTotal only (feature-flagged); others deferred
**Government verification:** Static curated KB (5 categories), explicitly not live search
**Languages:** English + Tamil
**Database:** None required
**Frontend:** React + Vite + Tailwind
**Backend:** FastAPI, single `/v1/analyze` endpoint
**Deployment:** Laptop primary; Render conditional
**Primary security principle:** Deterministic checks decide; AI explains; missing data is never shown as safe.
