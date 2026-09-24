"""URL extraction, normalization, and deterministic domain heuristics.

No network access happens here. A non-government domain is never, by itself,
treated as a scam indicator; checks look for specific deceptive patterns.
"""

import ipaddress
import re
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

Confidence = Literal["low", "medium", "high"]

MAX_URLS = 10

_COMMON_TLDS = (
    "in|com|net|org|info|co|io|app|online|site|xyz|top|cc|tk|ml|ga|cf|gq|work|click|link|"
    "live|shop|store|biz|me|us|uk|club|icu|buzz|vip|win|rest|cyou|sbs|pw|ws|ly|gl|to|gov|edu"
)
_URL_RE = re.compile(
    r"""(?ix)
    (?:
        \b(?:https?://|hxxps?://)[^\s<>"'`]+          # explicit scheme (incl. defanged hxxp)
      | \bwww\.[^\s<>"'`]+                             # www. prefix
      | (?<![@\w.-])                                   # bare domain, not part of an email
        (?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+
        (?:""" + _COMMON_TLDS + r""")
        (?![a-z0-9-])
        (?::\d{2,5})?
        (?:/[^\s<>"'`]*)?
    )
    """
)
_TRAILING_PUNCT = ".,;:!?)]}'\"”’>"

# Registrable-domain suffixes with two labels. Only what we need for Indian and common hosts.
_MULTI_LABEL_SUFFIXES = frozenset(
    {
        "gov.in", "nic.in", "co.in", "org.in", "net.in", "ac.in", "edu.in", "res.in",
        "gen.in", "firm.in", "ind.in", "mil.in", "co.uk", "org.uk", "gov.uk", "com.au",
    }
)
GOVERNMENT_SUFFIXES = ("gov.in", "nic.in")

SUSPICIOUS_TLDS = frozenset({"tk", "ml", "ga", "cf", "gq", "xyz", "top", "cc", "work", "click",
                             "icu", "buzz", "cyou", "sbs", "rest", "pw", "win", "vip"})
URL_SHORTENERS = frozenset({"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly",
                            "rb.gy", "shorturl.at", "tiny.cc", "ow.ly", "rebrand.ly", "t.ly"})
GOVERNMENT_KEYWORDS = ("uidai", "aadhaar", "aadhar", "incometax", "income-tax", "epfo",
                       "passport", "tneb", "tangedco", "pmkisan", "pm-kisan", "cybercrime",
                       "myscheme", "gov", "govt", "sarkari")
# Reference domains for typosquat comparison. Official portals only; not an allowlist of "safe".
REFERENCE_DOMAINS = ("uidai.gov.in", "myaadhaar.uidai.gov.in", "incometax.gov.in",
                     "passportindia.gov.in", "cybercrime.gov.in", "myscheme.gov.in",
                     "pmkisan.gov.in", "india.gov.in", "epfindia.gov.in")
EXECUTABLE_EXTENSIONS = (".apk", ".exe", ".msi", ".bat", ".scr", ".xapk", ".apks")
SENSITIVE_PATH_WORDS = ("login", "signin", "verify", "kyc", "update", "otp", "refund", "bank",
                        "secure", "account", "pay", "payment", "wallet", "unblock", "reactivate")


@dataclass(frozen=True)
class NormalizedUrl:
    raw: str
    normalized: str
    scheme: str
    hostname: str
    registrable_domain: str
    subdomain_labels: list[str]
    tld: str
    path: str
    query: str
    is_ip_host: bool
    has_userinfo: bool
    is_idn: bool


@dataclass
class DomainCheckHit:
    signal: str
    confidence: Confidence
    detail_en: str
    detail_ta: str
    kind: Literal["risk", "info"] = "risk"
    rule_id: str = field(default="")


def extract_urls(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _URL_RE.finditer(text or ""):
        candidate = match.group(0).rstrip(_TRAILING_PUNCT)
        if not candidate or "." not in candidate:
            continue
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            found.append(candidate)
        if len(found) >= MAX_URLS:
            break
    return found


def _registrable(host_labels: list[str]) -> tuple[str, list[str]]:
    if len(host_labels) >= 3 and ".".join(host_labels[-2:]) in _MULTI_LABEL_SUFFIXES:
        return ".".join(host_labels[-3:]), host_labels[:-3]
    if len(host_labels) >= 2:
        return ".".join(host_labels[-2:]), host_labels[:-2]
    return ".".join(host_labels), []


def normalize_url(raw_url: str) -> NormalizedUrl:
    raw = raw_url.strip()
    candidate = re.sub(r"^hxxp", "http", raw, flags=re.IGNORECASE)
    if "://" not in candidate:
        candidate = "http://" + candidate
    parts = urlsplit(candidate)
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError("unsupported URL scheme")

    host = (parts.hostname or "").rstrip(".")
    if not host:
        raise ValueError("URL has no hostname")

    is_idn = any(ord(c) > 127 for c in host) or any(lbl.startswith("xn--") for lbl in host.split("."))
    try:
        ascii_host = host.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("invalid internationalized hostname") from exc

    is_ip = False
    try:
        ipaddress.ip_address(ascii_host.strip("[]"))
        is_ip = True
    except ValueError:
        pass

    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError("invalid port") from exc
    netloc = ascii_host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{ascii_host}:{port}"

    path = parts.path or "/"
    normalized = urlunsplit((scheme, netloc, path, parts.query, ""))

    labels = ascii_host.split(".")
    if is_ip:
        registrable, subdomains, tld = ascii_host, [], ""
    else:
        registrable, subdomains = _registrable(labels)
        tld = labels[-1]

    return NormalizedUrl(
        raw=raw,
        normalized=normalized,
        scheme=scheme,
        hostname=ascii_host,
        registrable_domain=registrable,
        subdomain_labels=subdomains,
        tld=tld,
        path=path,
        query=parts.query,
        is_ip_host=is_ip,
        has_userinfo=bool(parts.username or parts.password),
        is_idn=is_idn,
    )


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def is_government_namespace(n: NormalizedUrl) -> bool:
    return any(n.hostname == s or n.hostname.endswith("." + s) for s in GOVERNMENT_SUFFIXES)


def run_domain_checks(n: NormalizedUrl) -> list[DomainCheckHit]:
    hits: list[DomainCheckHit] = []
    gov_namespace = is_government_namespace(n)

    if n.has_userinfo:
        hits.append(DomainCheckHit(
            "userinfo_in_url", "high",
            "The link hides its real destination using an '@' trick; the browser would open "
            f"'{n.hostname}', not the name shown before the '@'.",
            f"'@' உத்தியைப் பயன்படுத்தி இணைப்பு உண்மையான முகவரியை மறைக்கிறது; உலாவி '{n.hostname}' ஐத் திறக்கும்.",
            rule_id="URL-USERINFO-01"))

    if n.is_idn:
        hits.append(DomainCheckHit(
            "internationalized_lookalike_host", "high",
            "The web address uses non-English characters that can imitate familiar letters "
            "(a common lookalike technique).",
            "இணைய முகவரி பழக்கமான எழுத்துகளைப் போலத் தோன்றும் பிற எழுத்துகளைப் பயன்படுத்துகிறது.",
            rule_id="URL-IDN-01"))

    if n.is_ip_host:
        hits.append(DomainCheckHit(
            "raw_ip_host", "medium",
            "The link points to a raw IP address instead of a named website. Official services "
            "normally use named domains.",
            "இணைப்பு பெயருள்ள இணையதளத்திற்குப் பதிலாக நேரடி IP முகவரியைக் காட்டுகிறது.",
            rule_id="URL-IP-01"))

    if not n.is_ip_host and n.tld in SUSPICIOUS_TLDS:
        hits.append(DomainCheckHit(
            "suspicious_tld", "medium",
            f"The domain ends in '.{n.tld}', a low-cost ending frequently seen in phishing links. "
            "This alone does not prove the site is malicious.",
            f"டொமைன் '.{n.tld}' என முடிகிறது — மோசடி இணைப்புகளில் அடிக்கடி காணப்படும் முடிவு. இது மட்டும் மோசடிக்கு ஆதாரம் அல்ல.",
            rule_id="URL-TLD-01"))

    if n.registrable_domain in URL_SHORTENERS:
        hits.append(DomainCheckHit(
            "url_shortener", "medium",
            "The link uses a URL shortener, which hides the real destination.",
            "இணைப்பு சுருக்கப்பட்ட URL சேவையைப் பயன்படுத்தி உண்மையான முகவரியை மறைக்கிறது.",
            rule_id="URL-SHORT-01"))

    if not gov_namespace and not n.is_ip_host:
        host_text = n.hostname.replace(".", "-")
        keyword = next((k for k in GOVERNMENT_KEYWORDS if re.search(rf"(^|-){re.escape(k)}($|-|\d)", host_text)
                        or (len(k) > 4 and k in host_text)), None)
        if keyword:
            hits.append(DomainCheckHit(
                "government_lookalike_domain", "high",
                f"The address uses a government-style name ('{keyword}') but is registered under "
                f"'{n.registrable_domain}', which is not an official .gov.in or .nic.in domain.",
                f"முகவரி அரசு போன்ற பெயரை ('{keyword}') பயன்படுத்துகிறது, ஆனால் '{n.registrable_domain}' "
                "என்ற அதிகாரப்பூர்வமற்ற டொமைனில் பதிவு செய்யப்பட்டுள்ளது (.gov.in / .nic.in அல்ல).",
                rule_id="URL-GOVLOOK-01"))

    if not gov_namespace and not n.is_ip_host:
        leading_label = n.registrable_domain.split(".")[0]
        for reference in REFERENCE_DOMAINS:
            ref_label = reference.removesuffix(".gov.in").split(".")[-1]
            distance = levenshtein(n.registrable_domain, reference)
            if not 0 < distance <= 2 and len(ref_label) >= 5:
                distance = levenshtein(leading_label, ref_label)
            if 0 < distance <= 2:
                hits.append(DomainCheckHit(
                    "lookalike_domain_typosquat", "high",
                    f"'{n.registrable_domain}' differs from the official '{reference}' by only "
                    f"{distance} character(s) — a typical lookalike pattern.",
                    f"'{n.registrable_domain}' அதிகாரப்பூர்வ '{reference}' இலிருந்து {distance} எழுத்து(கள்) மட்டுமே "
                    "வேறுபடுகிறது — இது போலி முகவரி உத்தி.",
                    rule_id="URL-TYPO-01"))
                break

    if len(n.subdomain_labels) > 3 or n.hostname.count("-") >= 3:
        hits.append(DomainCheckHit(
            "excessive_subdomain_or_hyphenation", "low",
            "The address has an unusually long chain of sub-names or hyphens, often used to "
            "make a link look official.",
            "முகவரியில் அசாதாரணமான நீண்ட துணைப் பெயர்கள் அல்லது இணைப்புக் கோடுகள் உள்ளன.",
            rule_id="URL-STRUCT-01"))

    lowered_path = n.path.lower()
    if lowered_path.endswith(EXECUTABLE_EXTENSIONS):
        hits.append(DomainCheckHit(
            "executable_download_link", "high",
            "The link downloads an app/installer file (for example .apk). Installing apps from "
            "message links can give attackers control of your phone.",
            "இணைப்பு ஒரு செயலி/நிறுவல் கோப்பை (.apk போன்றவை) பதிவிறக்குகிறது. இது உங்கள் தொலைபேசியைக் கட்டுப்படுத்த அனுமதிக்கலாம்.",
            rule_id="URL-EXEC-01"))

    path_and_query = f"{lowered_path}?{n.query.lower()}"
    sensitive = [w for w in SENSITIVE_PATH_WORDS if w in path_and_query]
    if sensitive and not gov_namespace:
        hits.append(DomainCheckHit(
            "credential_or_payment_path", "low",
            "The link path refers to login, verification, or payment ("
            + ", ".join(sensitive[:3]) + ").",
            "இணைப்புப் பாதை உள்நுழைவு, சரிபார்ப்பு அல்லது கட்டணத்தைக் குறிப்பிடுகிறது.",
            rule_id="URL-PATH-01"))

    if n.scheme == "http" and not n.is_ip_host:
        hits.append(DomainCheckHit(
            "no_https", "low",
            "The link does not use a secure (https) connection.",
            "இணைப்பு பாதுகாப்பான (https) இணைப்பைப் பயன்படுத்தவில்லை.",
            rule_id="URL-HTTP-01"))

    if gov_namespace:
        hits.append(DomainCheckHit(
            "government_namespace_domain", "low",
            f"'{n.hostname}' is in the government-reserved .gov.in/.nic.in namespace. This does not "
            "confirm that the message's instructions are legitimate.",
            f"'{n.hostname}' அரசுக்கு ஒதுக்கப்பட்ட .gov.in/.nic.in பெயர்வெளியில் உள்ளது. இது செய்தியின் "
            "வழிமுறைகள் உண்மையானவை என்பதை உறுதிப்படுத்தாது.",
            kind="info",
            rule_id="URL-GOVNS-00"))

    return hits
