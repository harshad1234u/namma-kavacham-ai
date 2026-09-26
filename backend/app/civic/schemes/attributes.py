"""Closed vocabularies shared by scheme criteria, citizen profiles and eligibility questions.

Attributes are what a citizen can state about themselves. A scheme requirement that is not listed
here is recorded with attribute "other" (not machine-checkable), so the engine reports "not enough
information" for it instead of guessing.
"""
from dataclasses import dataclass, field
from typing import Literal

AttrType = Literal["int", "enum", "bool"]


@dataclass(frozen=True)
class Attribute:
    name: str
    type: AttrType
    values: tuple[str, ...] = ()
    question: dict[str, str] = field(default_factory=dict)  # lang -> question; English fallback


ATTRIBUTES: dict[str, Attribute] = {
    a.name: a
    for a in (
        Attribute("age", "int", question={
            "en": "How old are you (in years)?",
            "hi": "आपकी आयु कितनी है (वर्षों में)?",
            "ta": "உங்கள் வயது என்ன (ஆண்டுகளில்)?"}),
        Attribute("gender", "enum", ("female", "male", "other"), {
            "en": "What is your gender?",
            "hi": "आपका लिंग क्या है?",
            "ta": "உங்கள் பாலினம் என்ன?"}),
        Attribute("occupation", "enum", (
            "farmer", "agricultural_worker", "student", "self_employed", "salaried",
            "unorganised_worker", "street_vendor", "artisan", "unemployed", "homemaker", "other"), {
            "en": "What best describes your work?",
            "hi": "आपका काम किस श्रेणी में आता है?",
            "ta": "உங்கள் வேலையை எது சிறப்பாக விவரிக்கிறது?"}),
        Attribute("owns_agricultural_land", "bool", question={
            "en": "Does your family own cultivable agricultural land?",
            "hi": "क्या आपके परिवार के पास खेती योग्य कृषि भूमि है?",
            "ta": "உங்கள் குடும்பத்துக்கு சாகுபடி செய்யக்கூடிய விவசாய நிலம் சொந்தமாக உள்ளதா?"}),
        Attribute("residence_type", "enum", ("rural", "urban"), {
            "en": "Do you live in a rural or an urban area?",
            "hi": "आप ग्रामीण क्षेत्र में रहते हैं या शहरी क्षेत्र में?",
            "ta": "நீங்கள் கிராமப்புறத்தில் வசிக்கிறீர்களா, நகர்ப்புறத்திலா?"}),
        Attribute("annual_household_income_inr", "int", question={
            "en": "What is your household's annual income in rupees?",
            "hi": "आपके परिवार की वार्षिक आय कितने रुपये है?",
            "ta": "உங்கள் குடும்பத்தின் ஆண்டு வருமானம் எத்தனை ரூபாய்?"}),
        Attribute("social_category", "enum", ("sc", "st", "obc", "general"), {
            "en": "Which social category do you belong to?",
            "hi": "आप किस सामाजिक वर्ग से हैं?",
            "ta": "நீங்கள் எந்த சமூகப் பிரிவைச் சேர்ந்தவர்?"}),
        Attribute("is_indian_citizen", "bool", question={
            "en": "Are you a citizen of India?",
            "hi": "क्या आप भारत के नागरिक हैं?",
            "ta": "நீங்கள் இந்தியக் குடிமகனா?"}),
        Attribute("has_bank_account", "bool", question={
            "en": "Do you have a bank account in your name?",
            "hi": "क्या आपके नाम पर बैंक खाता है?",
            "ta": "உங்கள் பெயரில் வங்கிக் கணக்கு உள்ளதா?"}),
        Attribute("is_income_tax_payer", "bool", question={
            "en": "Are you (or is anyone in your family) an income-tax payer?",
            "hi": "क्या आप (या आपके परिवार में कोई) आयकर दाता हैं?",
            "ta": "நீங்கள் (அல்லது உங்கள் குடும்பத்தில் யாராவது) வருமான வரி செலுத்துபவரா?"}),
        Attribute("family_in_government_service", "bool", question={
            "en": "Are you or a member of your family in government service?",
            "hi": "क्या आप या आपके परिवार का कोई सदस्य सरकारी सेवा में है?",
            "ta": "நீங்கள் அல்லது உங்கள் குடும்ப உறுப்பினர் அரசுப் பணியில் உள்ளீர்களா?"}),
        Attribute("is_pregnant_or_lactating", "bool", question={
            "en": "Are you pregnant or breastfeeding?",
            "hi": "क्या आप गर्भवती हैं या स्तनपान करा रही हैं?",
            "ta": "நீங்கள் கர்ப்பமாக உள்ளீர்களா அல்லது பாலூட்டுகிறீர்களா?"}),
        Attribute("household_has_lpg_connection", "bool", question={
            "en": "Does anyone in your household already have an LPG connection?",
            "hi": "क्या आपके परिवार में किसी के पास पहले से एलपीजी कनेक्शन है?",
            "ta": "உங்கள் குடும்பத்தில் யாருக்காவது ஏற்கனவே எல்பிஜி இணைப்பு உள்ளதா?"}),
        Attribute("owns_pucca_house", "bool", question={
            "en": "Does your family own a pucca (permanent) house anywhere in India?",
            "hi": "क्या आपके परिवार के पास भारत में कहीं पक्का मकान है?",
            "ta": "உங்கள் குடும்பத்துக்கு இந்தியாவில் எங்காவது நிரந்தர (பக்கா) வீடு உள்ளதா?"}),
    )
}

# Need tags for discovery. Closed vocabulary: extraction may only choose from these.
NEED_TAGS: tuple[str, ...] = (
    "farming_income_support", "crop_insurance", "health_insurance", "housing", "cooking_fuel",
    "employment", "education_scholarship", "pension_old_age", "insurance_life_accident",
    "small_business_loan", "street_vendor_credit", "artisan_support", "banking_access",
    "drinking_water", "maternity_support", "girl_child_savings", "skill_training",
)

OPERATORS = ("eq", "in", "not_in", "gte", "lte", "between", "is_true", "is_false")
