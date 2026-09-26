"""Turn KB objects into localised API responses."""
from app.civic.schemes.attributes import ATTRIBUTES
from app.civic.schemes.models import (
    BenefitOut,
    ChannelOut,
    CriterionOut,
    QuestionOut,
    SchemeDetail,
    SchemeSummary,
    SourceOut,
    StatementOut,
)
from app.civic.schemes.schema import Criterion, Scheme, Statement
from app.civic.text import LocText, localize

SEARCH_PORTAL = "https://www.myscheme.gov.in/"

# NEEDS NATIVE REVIEW (hi, ta)
DISCLOSURE = {
    "en": "Information comes from a curated set of official government web pages, retrieved on the dates shown. "
          "It is not live data and not an official decision. Always confirm on the official portal before applying; "
          "the implementing authority decides eligibility.",
    "hi": "यह जानकारी आधिकारिक सरकारी वेबपेजों के चुने हुए संग्रह से ली गई है, जिन्हें दिखाई गई तारीखों पर प्राप्त किया गया था। "
          "यह लाइव डेटा या आधिकारिक निर्णय नहीं है। आवेदन से पहले आधिकारिक पोर्टल पर पुष्टि करें; पात्रता का निर्णय संबंधित प्राधिकरण करता है।",
    "ta": "இந்தத் தகவல் தேர்ந்தெடுக்கப்பட்ட அதிகாரப்பூர்வ அரசு இணையப் பக்கங்களிலிருந்து, காட்டப்பட்ட தேதிகளில் பெறப்பட்டது. "
          "இது நேரடித் தரவோ அதிகாரப்பூர்வ முடிவோ அல்ல. விண்ணப்பிக்கும் முன் அதிகாரப்பூர்வ இணையதளத்தில் உறுதிசெய்யவும்; தகுதியை செயல்படுத்தும் அதிகாரியே முடிவு செய்வார்.",
}
ELIGIBILITY_NOTE = {
    "en": "This compares your answers with the eligibility rules stated on the official pages we hold. "
          "It is guidance, not a decision; the implementing authority makes the final decision.",
    "hi": "यह आपके उत्तरों की तुलना हमारे पास मौजूद आधिकारिक पेजों में बताए गए पात्रता नियमों से करता है। "
          "यह मार्गदर्शन है, निर्णय नहीं; अंतिम निर्णय संबंधित प्राधिकरण करता है।",
    "ta": "இது உங்கள் பதில்களை எங்களிடம் உள்ள அதிகாரப்பூர்வ பக்கங்களில் கூறப்பட்ட தகுதி விதிகளுடன் ஒப்பிடுகிறது. "
          "இது வழிகாட்டுதல் மட்டுமே, முடிவு அல்ல; இறுதி முடிவைச் செயல்படுத்தும் அதிகாரியே எடுப்பார்.",
}


def loc(lt: dict[str, str], lang: str) -> LocText:
    return localize(lt, lang)


def statement(st: Statement, lang: str) -> StatementOut:
    return StatementOut(text=loc(st.text, lang), source_ref=st.source_ref)


def criterion(c: Criterion, lang: str) -> CriterionOut:
    return CriterionOut(id=c.id, attribute=c.attribute, kind=c.kind, statement=statement(c.statement, lang))


def sources(s: Scheme) -> list[SourceOut]:
    return [SourceOut(id=x.id, publisher=x.publisher, title=x.title, url=x.url, retrieved=x.retrieved) for x in s.sources]


def summary(s: Scheme, lang: str) -> SchemeSummary:
    return SchemeSummary(
        id=s.id, name=loc(s.names, lang), abbreviations=s.abbreviations, level=s.level, ministry=s.ministry,
        need_tags=s.need_tags, description=statement(s.description, lang), last_verified=s.last_verified,
        official_domains=s.official_domains,
    )


def detail(s: Scheme, lang: str) -> SchemeDetail:
    return SchemeDetail(
        **summary(s, lang).model_dump(),
        benefits=[BenefitOut(**statement(b, lang).model_dump(), amount_inr=b.amount_inr) for b in s.benefits],
        eligibility=[criterion(c, lang) for c in s.eligibility],
        criteria_complete=s.criteria_complete,
        documents=[statement(d.statement, lang) for d in s.documents],
        application_steps=[statement(a, lang) for a in s.application_steps],
        channels=[ChannelOut(type=c.type, label=loc(c.label, lang), official_url=c.official_url, source_ref=c.source_ref) for c in s.channels],
        helplines=[h.number for h in s.helplines],
        sources=sources(s),
        disclosure=loc(DISCLOSURE, lang),
    )


def question(attr_name: str, lang: str) -> QuestionOut:
    a = ATTRIBUTES[attr_name]
    options = list(a.values) if a.type == "enum" else (["true", "false"] if a.type == "bool" else [])
    return QuestionOut(attribute=a.name, type=a.type, options=options, question=loc(a.question, lang))
