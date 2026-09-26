"""Development-need taxonomy: 12 categories, each with issue types and multilingual keywords.

Adding a category = one entry here. `infra_metric` names the facility count used for the gap
engine; `benchmark_per_10k` is an analytical reference chosen for this demo, NOT an official norm.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class IssueType:
    id: str
    label: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class Category:
    id: str
    labels: dict[str, str]
    keywords: tuple[str, ...]
    issues: tuple[IssueType, ...]
    infra_metric: str | None
    benchmark_per_10k: float | None


def _i(id_: str, label: str, *kw: str) -> IssueType:
    return IssueType(id_, label, kw)


CATEGORIES: dict[str, Category] = {c.id: c for c in (
    Category("water", {"en": "Water", "hi": "पानी", "ta": "குடிநீர்"},
             ("water", "drinking water", "tap", "borewell", "tanker", "paani", "pani", "tanni", "thanni", "पानी", "पेयजल", "नल", "குடிநீர்", "தண்ணீர்", "நீர்"),
             (_i("no_supply", "No or irregular supply", "no water", "not coming", "4 km", "km every day", "irregular", "नहीं आता", "வருவதில்லை", "sari illa", "illa"),
              _i("contamination", "Contaminated water", "dirty", "contaminated", "smell", "गंदा", "அசுத்த"),
              _i("pipeline_leak", "Broken pipeline or leak", "leak", "pipeline", "pipe", "broken tap", "पाइप", "குழாய்")),
             "water_facilities", 2.0),
    Category("roads", {"en": "Roads", "hi": "सड़क", "ta": "சாலை"},
             ("road", "pothole", "street", "sadak", "rasta", "salai", "सड़क", "रास्ता", "சாலை", "ரோடு", "குழி"),
             (_i("damaged_road", "Damaged road / potholes", "pothole", "damaged", "broken", "गड्ढे", "குழி", "damage"),
              _i("waterlogging", "Waterlogging in rain", "rain", "flood", "water logging", "बारिश", "மழை"),
              _i("no_road", "No road access", "no road", "कच्चा", "no access")),
             "road_km", 12.0),
    Category("healthcare", {"en": "Healthcare", "hi": "स्वास्थ्य", "ta": "சுகாதாரம்"},
             ("hospital", "health", "doctor", "clinic", "phc", "medicine", "aspatal", "davakhana", "अस्पताल", "डॉक्टर", "दवा", "மருத்துவமனை", "மருத்துவர்", "மருந்து"),
             (_i("no_facility", "No nearby facility", "no hospital", "far", "km", "दूर", "தூரம்"),
              _i("staff_shortage", "Doctor/staff shortage", "no doctor", "doctor absent", "staff", "डॉक्टर नहीं", "மருத்துவர் இல்லை"),
              _i("medicine_shortage", "Medicine shortage", "medicine", "दवा", "மருந்து")),
             "health_facilities", 0.5),
    Category("education", {"en": "Education", "hi": "शिक्षा", "ta": "கல்வி"},
             ("school", "teacher", "classroom", "education", "college", "padhai", "vidyalaya", "स्कूल", "शिक्षक", "पढ़ाई", "பள்ளி", "ஆசிரியர்"),
             (_i("teacher_shortage", "Teacher shortage", "teacher", "शिक्षक", "ஆசிரியர்"),
              _i("poor_infrastructure", "Poor school building/facilities", "building", "roof", "toilet", "bench", "छत", "கட்டிடம்"),
              _i("no_school", "No school nearby", "no school", "far", "km", "दूर")),
             "schools", 3.0),
    Category("electricity", {"en": "Electricity", "hi": "बिजली", "ta": "மின்சாரம்"},
             ("electricity", "power", "current", "transformer", "streetlight", "bijli", "karant", "minsaram", "बिजली", "மின்சாரம்", "கரண்ட்"),
             (_i("power_cuts", "Frequent power cuts", "power cut", "cut", "hours", "कटौती", "தடை"),
              _i("streetlights", "Streetlights not working", "streetlight", "street light", "dark", "अंधेरा", "தெருவிளக்கு"),
              _i("no_connection", "No connection", "no connection", "कनेक्शन", "இணைப்பு")),
             None, None),
    Category("sanitation", {"en": "Sanitation", "hi": "स्वच्छता", "ta": "சுகாதாரம் (துப்புரவு)"},
             ("garbage", "drainage", "sewage", "toilet", "waste", "kachra", "naali", "कचरा", "नाली", "शौचालय", "குப்பை", "கழிவுநீர்", "சாக்கடை"),
             (_i("garbage", "Garbage not collected", "garbage", "waste", "कचरा", "குப்பை"),
              _i("drainage", "Blocked drains / sewage", "drain", "sewage", "overflow", "नाली", "சாக்கடை"),
              _i("no_toilets", "No public/household toilets", "toilet", "शौचालय", "கழிப்பறை")),
             "sanitation_facilities", 1.0),
    Category("public_transport", {"en": "Public transport", "hi": "सार्वजनिक परिवहन", "ta": "பொது போக்குவரத்து"},
             ("bus", "transport", "bus stop", "train", "auto", "बस", "பேருந்து", "பஸ்"),
             (_i("no_bus", "No bus service", "no bus", "बस नहीं", "பேருந்து இல்லை"),
              _i("poor_frequency", "Infrequent service", "only one", "once", "rarely", "wait", "इंतजार")),
             "transport_points", 1.5),
    Category("digital_connectivity", {"en": "Digital connectivity", "hi": "डिजिटल कनेक्टिविटी", "ta": "இணைய இணைப்பு"},
             ("internet", "network", "signal", "mobile tower", "wifi", "broadband", "नेटवर्क", "इंटरनेट", "இணையம்", "சிக்னல்"),
             (_i("no_network", "No mobile network", "no signal", "no network", "नेटवर्क नहीं", "சிக்னல் இல்லை"),
              _i("slow_internet", "Slow internet", "slow", "धीमा")),
             None, None),
    Category("agriculture", {"en": "Agriculture", "hi": "कृषि", "ta": "விவசாயம்"},
             ("irrigation", "crop", "farm", "canal", "fertiliser", "fertilizer", "kheti", "sinchai", "सिंचाई", "फसल", "खेती", "பாசனம்", "பயிர்", "விவசாய"),
             (_i("irrigation", "Irrigation shortage", "irrigation", "canal", "सिंचाई", "பாசனம்"),
              _i("input_support", "Seeds/fertiliser support", "seed", "fertiliser", "fertilizer", "खाद", "உரம்")),
             None, None),
    Category("housing", {"en": "Housing", "hi": "आवास", "ta": "வீட்டுவசதி"},
             ("house", "housing", "shelter", "hut", "ghar", "makan", "मकान", "घर", "வீடு"),
             (_i("damaged_house", "Damaged house", "damaged", "collapsed", "leaking roof", "टूटा", "சேதம்"),
              _i("no_house", "No pucca house", "no house", "kutcha", "hut", "झोपड़ी", "குடிசை")),
             None, None),
    Category("employment", {"en": "Employment", "hi": "रोजगार", "ta": "வேலைவாய்ப்பு"},
             ("job", "work", "employment", "wages", "mgnrega", "rozgar", "naukri", "velai", "रोजगार", "मजदूरी", "வேலை", "கூலி"),
             (_i("no_work", "No work available", "no work", "no job", "काम नहीं", "வேலை இல்லை"),
              _i("delayed_wages", "Wages delayed", "wages", "payment", "मजदूरी", "கூலி")),
             None, None),
    Category("public_safety", {"en": "Public safety", "hi": "सार्वजनिक सुरक्षा", "ta": "பொது பாதுகாப்பு"},
             ("safety", "unsafe", "theft", "police", "crime", "harassment", "सुरक्षा", "चोरी", "பாதுகாப்பு", "திருட்டு"),
             (_i("unsafe_area", "Unsafe area / poor lighting", "unsafe", "dark", "अंधेरा", "இருட்டு"),
              _i("crime", "Crime / theft", "theft", "crime", "चोरी", "திருட்டு")),
             "police_points", 0.3),
)}

URGENCY_HIGH = ("urgent", "emergency", "danger", "dangerous", "accident", "sick", "death", "died", "children", "every day",
                "days without", "weeks", "immediately", "तुरंत", "खतरा", "बीमार", "हादसा", "அவசரம்", "ஆபத்து", "விபத்து", "தினமும்")
URGENCY_LOW = ("suggest", "suggestion", "would be nice", "request to consider", "सुझाव", "பரிந்துரை")
