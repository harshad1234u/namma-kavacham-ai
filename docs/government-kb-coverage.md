# Government knowledge base — coverage and maintenance

The curated knowledge base (`backend/app/data/government_kb.json`) is a small, static reference. It is **not**
a directory of Indian government services and **not** live verification. A service being listed does not
prove that any message about it is genuine; a service being absent does not make a message fraudulent.

## Covered services (7 entries, last reviewed 2026-09-25)

| Entry id | Service | Official domains | Evidence used |
|---|---|---|---|
| `uidai_aadhaar` | Aadhaar (UIDAI) | uidai.gov.in | PIB (UIDAI) release, 2022-12-30 |
| `pm_kisan` | PM-KISAN | pmkisan.gov.in | pmkisan.gov.in home page |
| `income_tax` | Income Tax Department | incometax.gov.in, incometaxindia.gov.in | CBDT anti-phishing press release, 2016-02-05 (incometax.gov.in) |
| `passport_seva` | Passport Seva | passportindia.gov.in | PIB (MEA) releases, 2026-06-02 and 2014-07-09 |
| `cybercrime_reporting` | National Cyber Crime Reporting Portal & 1930 | cybercrime.gov.in | PIB (MHA) release, cybercrime.gov.in |
| `ab_pmjay` *(Phase 5)* | Ayushman Bharat PM-JAY | pmjay.gov.in, nha.gov.in | PIB releases [2040860](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2040860) (2024-08-02), [1831575](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1831575) (2022-06-06), [2185049](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2185049) (2025-11-01) |
| `national_scholarship_portal` *(Phase 5)* | National Scholarship Portal (NSP) | scholarships.gov.in | [scholarships.gov.in](https://scholarships.gov.in/) home page |

### Phase 5 evidence notes

- **PM-JAY.** `pmjay.gov.in` is confirmed as the official website by PIB release 1831575 ("Ayushman Bharat
  PM-JAY official website (https://pmjay.gov.in)"). `nha.gov.in/PM-JAY` is linked by PIB release 2185049.
  `pmjay.gov.in` itself did not respond from the development machine on 2026-09-25, and `nha.gov.in/PM-JAY`
  is a JavaScript-only page, so no facts are quoted from either site; all facts come from PIB. The facts are
  `not_covered` findings (the sources describe the cashless cover and the Ayushman card routes, and say
  nothing about fees paid through message links or applications through WhatsApp/Telegram). **No helpline is
  listed**, because none was confirmed from a fetched official page.
- **NSP.** The home page states that NSP services are available at Common Service Centres (CSCs) and that the
  total CSC charge per candidate "is fixed at Rs 30.00". Because a genuine charge exists, a fee request
  mentioning NSP is reported as `not_covered` with that context, **not** as `contradicted`.
- Every quote in both entries was checked word for word (whitespace-normalised) against the fetched page text
  on 2026-09-25.

## Not covered

Naming one of these in a message gives the status `not_found_in_curated_kb`. The detector knows the name
(`_UNCOVERED_SERVICES` in `backend/app/services/government/claim_detector.py`) but has no curated facts to
compare against.

| Service | Why it is not in the KB |
|---|---|
| Kalaignar Magalir Urimai Thogai (Tamil Nadu) | Investigated in Phase 5. The scheme site `kmut.tn.gov.in` served an **expired TLS certificate** on 2026-09-25, so its content could not be fetched with a validated connection. The State Planning Commission page ([spc.tn.gov.in](https://spc.tn.gov.in/kalaignar-magalir-urimai-thittam/)) confirms the scheme exists ("The scheme benefits about 1.15 crore women") but gives no official domain, amount, fee or application route to compare against, and its linked PDF report could not be parsed. Re-check when the certificate is renewed. |
| Electricity board (TNEB / TANGEDCO) | Not yet sourced. |
| EPFO / Provident Fund | Not yet sourced. |
| Ration card / PDS | Not yet sourced. |
| Voter ID / Election Commission | Not yet sourced. |
| Driving licence / vehicle (Parivahan) | Not yet sourced. |
| Telecom / SIM (DoT, TRAI) | Not yet sourced. |
| LPG / gas subsidy | Not yet sourced. |
| Law enforcement (CBI / police / customs) | Not a benefit scheme; covered by the generic "digital arrest" and threat rules. |

Any other scheme or department is either unrecognised (no government claim) or, if named only generically
("PM scheme", "government subsidy"), reported as `unable_to_assess` without guessing a scheme.

## Adding or updating an entry

1. **Find an official source.** Use the scheme's own `.gov.in` / `.nic.in` site, a ministry site, PIB, or
   india.gov.in / myscheme.gov.in. Do not use blogs, news sites, social media or third-party "guide" pages.
   The connection must validate (no certificate errors).
2. **Quote, don't paraphrase.** Put the exact sentences in the source's `quotes`. Every `statement_en/ta` in
   a fact must be supported by a quote from the source it cites.
3. **Record the domain only if a source names it.** `official_domains` must end in `.gov.in` or `.nic.in`
   (the loader rejects anything else). `official_urls` must be `https` on one of those domains.
4. **Choose the effect carefully.** `contradicts` only when a source says the opposite of the message (for
   example "do not share your OTP"). If the source is simply silent, use `not_covered`. `compare_amount`
   is only for instalment amounts stated by the source.
5. **Check aliases.** An ASCII alias of 5 or more characters is also used to spot lookalike domains, so a
   genuine official domain containing the alias must be listed in `official_domains`, or it will be flagged
   as a lookalike. Keep aliases specific; avoid words common in ordinary chat.
6. **Update the metadata.** Set `retrieved` on each source, `last_reviewed` on the KB, and add the source
   host to `OFFICIAL_SOURCE_HOSTS` in `backend/app/tests/test_government_kb.py`.
7. **Add Tamil text** and a row to `docs/tamil-review.md` (status "pending native review").
8. **Run the tests** (`python -m pytest -q` in `backend/`). The loader validates schema, source references
   and domains at start-up; a malformed KB fails fast.
