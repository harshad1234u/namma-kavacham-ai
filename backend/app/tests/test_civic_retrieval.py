import httpx
import pytest

from app.civic.nim.provider import NIMError
from app.civic.retrieval.fetch import FetchError, fetch_page, html_to_text
from app.civic.retrieval.index import chunk, tokens
from app.civic.retrieval.service import OfficialSourceRetriever
from app.civic.retrieval.sources import SeedSource, UnofficialUrlError, seed_sources, validate_official_url

STANDUP_HTML = """<html><head><title>Stand Up India Scheme (SUPI)</title><script>var x=1;</script></head><body>
<nav>Home About Contact</nav>
<p>The Stand-up India Scheme was launched on 5th April, 2016 to promote entrepreneurship among the Scheduled Castes/ Scheduled Tribes and Women.</p>
<p>Features: Composite Loan between Rs.10 lakh and Rs.1 crore to entrepreneurs above 18 years of age, through Scheduled Commercial Banks (SCBs); Repayment of the loan in a span of upto seven years including moratorium period of 18 months.</p>
</body></html>"""
KISAN_HTML = """<html><head><title>PM-Kisan</title></head><body><p>PM Kisan is a Central Sector scheme with 100% funding from Government of India.
Under the scheme an income support of 6,000/- per year in three equal installments will be provided to all land holding farmer families.</p>
<p>Definition of family for the scheme is husband, wife and minor children and more words to pass the readable text threshold of the fetcher.</p></body></html>"""

SOURCES = (
    SeedSource("https://financialservices.gov.in/stand-india-scheme-supi", "SUPI", "DFS", None),
    SeedSource("https://pmkisan.gov.in/", "PM-Kisan", "DA&FW", "pm_kisan"),
    SeedSource("https://broken.gov.in/", "Broken", "x", None),
)


def site(req: httpx.Request) -> httpx.Response:
    host = req.url.host
    if host == "financialservices.gov.in":
        return httpx.Response(200, html=STANDUP_HTML)
    if host == "pmkisan.gov.in":
        return httpx.Response(200, html=KISAN_HTML)
    raise httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED]")


class FakeEmbedder:
    """Deterministic bag-of-words vectors, standing in for Nemotron."""

    model = "fake"
    VOCAB = ["stand", "entrepreneurship", "loan", "women", "kisan", "income", "farmer", "6", "000"]

    def __init__(self, fail=False):
        self.fail, self.calls = fail, []

    async def embed(self, texts, input_type):
        self.calls.append(input_type)
        if self.fail:
            raise NIMError("connection_error")
        return [[float(t.lower().count(w)) + 0.01 for w in self.VOCAB] for t in texts]


# ---------- official domain / URL validation ----------
@pytest.mark.parametrize("url", ["https://pmkisan.gov.in/", "https://nrega.nic.in/x", "https://a.b.gov.in/p?q=1"])
def test_official_urls_accepted(url):
    assert validate_official_url(url) == url


@pytest.mark.parametrize("url", [
    "http://pmkisan.gov.in/", "https://pmkisan-gov.in/", "https://pmkisan.gov.in.evil.com/", "https://youtube.com/watch",
    "https://gov.in.example.org", "ftp://x.gov.in", "https://www.standupmitra.in/", "javascript:alert(1)",
])
def test_unofficial_urls_rejected(url):
    with pytest.raises(UnofficialUrlError):
        validate_official_url(url)


def test_registry_is_official_and_includes_kb_sources():
    reg = seed_sources()
    assert all(validate_official_url(s.url) for s in reg)
    assert any(s.scheme_id == "pm_kisan" for s in reg) and any("stand-india" in s.url for s in reg)
    assert len({s.url for s in reg}) == len(reg)


# ---------- fetching ----------
def test_html_to_text_drops_scripts():
    title, text = html_to_text(STANDUP_HTML)
    assert title == "Stand Up India Scheme (SUPI)" and "var x" not in text and "5th April, 2016" in text


async def test_redirect_off_official_domain_is_rejected():
    def handler(req):
        if req.url.host == "scheme.gov.in":
            return httpx.Response(302, headers={"location": "https://scheme-apply.com/"})
        return httpx.Response(200, html=STANDUP_HTML)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        with pytest.raises(FetchError) as e:
            await fetch_page("https://scheme.gov.in/", c)
    assert e.value.reason == "redirected_off_official_domain"


async def test_unofficial_url_is_never_fetched():
    hits = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: hits.append(r) or httpx.Response(200))) as c:
        with pytest.raises(UnofficialUrlError):
            await fetch_page("https://example.com/", c)
    assert hits == []


async def test_javascript_shell_is_not_evidence():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, html="<div id=root></div>"))) as c:
        with pytest.raises(FetchError) as e:
            await fetch_page("https://www.myscheme.gov.in/schemes/x", c)
    assert e.value.reason == "no_readable_text"


# ---------- chunking / evidence ----------
def test_chunks_overlap_and_cover_text():
    text = " ".join(f"Sentence number {i} talks about farmer income support." for i in range(40))
    parts = chunk(text, size=300)
    assert len(parts) > 3 and all(len(p) < 400 for p in parts)
    assert parts[0].split(". ")[-1] in parts[1]  # one sentence of overlap


def test_tokens_are_script_agnostic():
    assert "किसान" in tokens("पीएम किसान योजना") and "விவசாயி" in tokens("நான் ஒரு விவசாயி")


async def test_keyword_retrieval_returns_exact_official_quotes():
    r = OfficialSourceRetriever(SOURCES, transport=httpx.MockTransport(site))
    res = await r.retrieve("Is Stand-Up India a loan scheme for women entrepreneurs?")
    assert res.available and res.sources_checked == 3
    assert res.sources_unavailable == {"https://broken.gov.in/": "tls_error"}
    top = res.evidence[0]
    assert top.domain == "financialservices.gov.in" and top.method == "keyword"
    assert top.quote in STANDUP_HTML.replace("\n", " ") or top.quote in html_to_text(STANDUP_HTML)[1]
    assert top.title == "Stand Up India Scheme (SUPI)" and top.retrieved_at is not None


async def test_embedding_retrieval_uses_query_and_passage_types():
    emb = FakeEmbedder()
    r = OfficialSourceRetriever(SOURCES, transport=httpx.MockTransport(site))
    res = await r.retrieve("farmer income kisan", embedder=emb)
    assert res.evidence[0].method == "embedding" and res.evidence[0].scheme_id == "pm_kisan"
    assert "passage" in emb.calls and emb.calls[-1] == "query"


async def test_embedding_failure_falls_back_to_keywords():
    r = OfficialSourceRetriever(SOURCES, transport=httpx.MockTransport(site))
    res = await r.retrieve("farmer income support", embedder=FakeEmbedder(fail=True))
    assert res.evidence and res.evidence[0].method == "keyword"


async def test_all_sources_down_is_reported_as_unavailable():
    def down(req):
        raise httpx.ConnectError("down")

    r = OfficialSourceRetriever(SOURCES, transport=httpx.MockTransport(down))
    res = await r.retrieve("anything")
    assert not res.available and res.evidence == [] and len(res.sources_unavailable) == 3


async def test_pages_are_cached_between_queries():
    hits = []

    def counting(req):
        hits.append(req.url.host)
        return site(req)

    r = OfficialSourceRetriever(SOURCES, transport=httpx.MockTransport(counting))
    await r.retrieve("loan")
    await r.retrieve("farmer")
    assert len(hits) == 3


def test_numbers_match_with_or_without_grouping():
    assert "6000" in tokens("income support of 6,000/- per year") and "6000" in tokens("₹6000")


def test_long_quotes_are_exact_windows():
    from app.civic.retrieval.index import best_quote

    nav = "Home About Contact " * 40 + "the stand-up india loan is for women entrepreneurs " + "Footer Links " * 40
    q = best_quote(nav, {"stand-up", "women"})
    assert len(q) <= 300 and q in nav and "women" in q
