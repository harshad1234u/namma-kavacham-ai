"""Generate the Development Intelligence demonstration dataset (deterministic, seed 26).

Everything produced here except the State/UT names is SYNTHETIC and labelled source.type = "demo".
The State/UT names were read from the official DBT Bharat home page (https://dbtbharat.gov.in/)
on 2026-09-26. District names are real places used for geography only; localities are fictional
("Demo Area A"), and population, facility, project and request figures are invented for demonstration.

Usage: python scripts/generate_dev_demo_data.py
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "app" / "data" / "civic" / "development"
TODAY = date(2026, 9, 26)
DEMO = {"type": "demo", "name": "CivicInsight demonstration dataset (synthetic)", "last_updated": TODAY.isoformat(),
        "scope": "4 districts, 12 fictional localities",
        "note": "Synthetic figures for demonstration only. Not census, government or official statistics."}

STATES = [  # from https://dbtbharat.gov.in/ (retrieved 2026-09-26)
    "ANDAMAN AND NICOBAR ISLANDS", "ANDHRA PRADESH", "ARUNACHAL PRADESH", "ASSAM", "BIHAR", "CHANDIGARH", "CHHATTISGARH",
    "DELHI", "GOA", "GUJARAT", "HARYANA", "HIMACHAL PRADESH", "JAMMU AND KASHMIR", "JHARKHAND", "KARNATAKA", "KERALA",
    "LADAKH", "LAKSHADWEEP", "MADHYA PRADESH", "MAHARASHTRA", "MANIPUR", "MEGHALAYA", "MIZORAM", "NAGALAND", "ODISHA",
    "PUDUCHERRY", "PUNJAB", "RAJASTHAN", "SIKKIM", "TAMIL NADU", "TELANGANA", "THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "TRIPURA", "UTTAR PRADESH", "UTTARAKHAND", "WEST BENGAL",
]
# district -> (state, approximate district-centre lat/lng for map placement only)
DISTRICTS = {
    "Tiruchirappalli": ("TAMIL NADU", 10.79, 78.70),
    "Madurai": ("TAMIL NADU", 9.93, 78.12),
    "Pune": ("MAHARASHTRA", 18.52, 73.86),
    "Gaya": ("BIHAR", 24.79, 85.00),
}
OFFSETS = {"A": (0.05, -0.04), "B": (-0.05, 0.05), "C": (0.03, 0.07)}

# (district, area) -> scenario weights per category; the first one is the headline demo hotspot.
SCENARIO = {
    ("Tiruchirappalli", "A"): {"water": 132, "roads": 14, "healthcare": 6},
    ("Tiruchirappalli", "B"): {"roads": 38, "sanitation": 12},
    ("Tiruchirappalli", "C"): {"education": 9, "electricity": 7},
    ("Madurai", "A"): {"healthcare": 46, "water": 10},
    ("Madurai", "B"): {"sanitation": 21, "public_transport": 8},
    ("Madurai", "C"): {"digital_connectivity": 11},
    ("Pune", "A"): {"roads": 52, "public_transport": 18},
    ("Pune", "B"): {"water": 16, "public_safety": 9},
    ("Pune", "C"): {"housing": 7, "employment": 6},
    ("Gaya", "A"): {"electricity": 34, "agriculture": 15},
    ("Gaya", "B"): {"education": 28, "healthcare": 9},
    ("Gaya", "C"): {"employment": 22, "housing": 5},
}

TEMPLATES = {
    "water": [("en", "Our area does not have proper drinking water. We walk 4 km every day for water."),
              ("ta", "எங்கள் பகுதியில் குடிநீர் வசதி சரியாக இல்லை. தினமும் 4 கிலோமீட்டர் செல்ல வேண்டியுள்ளது."),
              ("romanised_indic", "Enga area la water facility sari illa, tanker um varala."),
              ("hi", "हमारे मोहल्ले में पीने का पानी नहीं आता, नल सूखे हैं।"),
              ("en", "Tap water is dirty and has a bad smell, children are falling sick."),
              ("en", "The water pipeline near the temple is broken and leaking for weeks.")],
    "roads": [("en", "Road near our government school is completely damaged and buses cannot enter during rain."),
              ("en", "The road is full of potholes, two accidents happened this month."),
              ("hi", "सड़क में बड़े गड्ढे हैं, बारिश में पानी भर जाता है।"),
              ("ta", "பள்ளி அருகே உள்ள சாலை முழுவதும் குழிகளாக உள்ளது.")],
    "healthcare": [("en", "No doctor at the primary health centre most days."),
                   ("hi", "अस्पताल बहुत दूर है और दवा नहीं मिलती।"),
                   ("ta", "ஆரம்ப சுகாதார நிலையத்தில் மருத்துவர் இல்லை, மருந்தும் இல்லை.")],
    "education": [("en", "The school has only one teacher for five classes."),
                  ("hi", "स्कूल की छत टूटी है, बच्चे बाहर बैठते हैं।")],
    "electricity": [("en", "Power cuts for 8 hours every day in our village."),
                    ("hi", "गांव में बिजली की कटौती रोज़ होती है, ट्रांसफार्मर खराब है।"),
                    ("en", "Streetlights have not worked for months and the road is dark.")],
    "sanitation": [("en", "Garbage is not collected and drains are overflowing."),
                   ("ta", "குப்பை அள்ளப்படவில்லை, சாக்கடை நிரம்பி வழிகிறது.")],
    "public_transport": [("en", "Only one bus a day comes to our village."), ("hi", "गांव में बस नहीं आती।")],
    "digital_connectivity": [("en", "There is no mobile network signal in our area."), ("ta", "எங்கள் ஊரில் சிக்னல் இல்லை.")],
    "agriculture": [("en", "The irrigation canal is dry and crops are failing."), ("hi", "सिंचाई के लिए पानी नहीं है, फसल सूख रही है।")],
    "housing": [("en", "Many families live in kutcha huts with leaking roofs."), ("hi", "बारिश में हमारा घर टूट गया।")],
    "employment": [("en", "No work available under the job scheme for months."), ("hi", "मजदूरी का भुगतान कई महीनों से नहीं हुआ।")],
    "public_safety": [("en", "The market road is unsafe at night because it is dark."), ("en", "Theft cases have increased near the bus stand.")],
}


def main() -> None:
    rnd = random.Random(26)
    OUT.mkdir(parents=True, exist_ok=True)
    areas, demo, infra = [], [], []
    for d, (state, lat, lng) in DISTRICTS.items():
        for a, (dy, dx) in OFFSETS.items():
            aid = f"{d.lower()}-{a.lower()}"
            areas.append({"area_id": aid, "state": state, "district": d, "area": f"Demo Area {a}",
                          "lat": round(lat + dy, 4), "lng": round(lng + dx, 4)})
            if aid != "madurai-c":  # deliberately missing: shows "population impact cannot be assessed"
                pop = 185000 if aid == "tiruchirappalli-a" else rnd.randrange(38000, 160000, 1000)
                demo.append({"area_id": aid, "population": pop, "households": pop // 4,
                             "children_percent": round(rnd.uniform(16, 26), 1), "elderly_percent": round(rnd.uniform(6, 12), 1),
                             "literacy_rate": round(rnd.uniform(68, 90), 1)})
            if aid not in ("gaya-c", "pune-c"):  # deliberately missing: shows "infrastructure data unavailable"
                row = {"area_id": aid, "water_facilities": 14 if aid == "tiruchirappalli-a" else rnd.randint(10, 40),
                       "road_km": rnd.randint(60, 240), "health_facilities": rnd.randint(1, 8), "schools": rnd.randint(8, 40),
                       "sanitation_facilities": rnd.randint(4, 25), "transport_points": rnd.randint(3, 25),
                       "police_points": rnd.randint(1, 6)}
                if aid == "madurai-a":
                    row["health_facilities"] = 2
                infra.append(row)
    projects = [
        ("P001", "Demo: Road resurfacing programme", "tiruchirappalli-b", "roads", 42_000_000, "ongoing"),
        ("P002", "Demo: Ring road widening", "pune-a", "roads", 180_000_000, "planned"),
        ("P003", "Demo: Urban bus route extension", "pune-a", "public_transport", 25_000_000, "proposed"),
        ("P004", "Demo: Primary health centre upgrade", "madurai-a", "healthcare", 30_000_000, "delayed"),
        ("P005", "Demo: Feeder line and transformer replacement", "gaya-a", "electricity", 55_000_000, "approved"),
        ("P006", "Demo: School building repairs", "gaya-b", "education", 12_000_000, "completed"),
        ("P007", "Demo: Canal desilting", "gaya-a", "agriculture", 9_000_000, "planned"),
        ("P008", "Demo: Underground drainage phase 1", "madurai-b", "sanitation", 60_000_000, "ongoing"),
        ("P009", "Demo: Water treatment plant expansion", "pune-b", "water", 75_000_000, "ongoing"),
        ("P010", "Demo: Street lighting upgrade", "pune-b", "public_safety", 6_000_000, "completed"),
        ("P011", "Demo: Solid waste collection vehicles", "tiruchirappalli-b", "sanitation", 8_000_000, "approved"),
        ("P012", "Demo: Mobile tower connectivity", "madurai-c", "digital_connectivity", 15_000_000, "proposed"),
        ("P013", "Demo: Anganwadi and school toilets", "tiruchirappalli-c", "education", 4_000_000, "planned"),
        ("P014", "Demo: Rural employment works shelf", "gaya-c", "employment", 20_000_000, "ongoing"),
    ]
    invest = [{"project_id": p, "name": n, "area_id": a, "category": c, "budget_inr": b, "status": s,
               "start_date": (TODAY - timedelta(days=rnd.randint(30, 400))).isoformat(),
               "expected_completion": (TODAY + timedelta(days=rnd.randint(60, 700))).isoformat()} for p, n, a, c, b, s in projects]
    reqs, n = [], 0
    for (d, a), cats in SCENARIO.items():
        aid = f"{d.lower()}-{a.lower()}"
        for cat, count in cats.items():
            for _ in range(count):
                n += 1
                lang, text = rnd.choice(TEMPLATES[cat])
                days = int(rnd.triangular(0, 90, 10))
                urgency = rnd.choices(["high", "medium", "low"], [5, 4, 1] if aid == "tiruchirappalli-a" else [2, 5, 3])[0]
                reqs.append({"id": f"DEMO-{n:04d}", "text": text, "language": lang, "category": cat, "area_id": aid,
                             "urgency": urgency, "source": rnd.choice(["text", "text", "voice"]),
                             "created_at": (TODAY - timedelta(days=days)).isoformat()})
    files = {"areas.json": {"states_and_uts": {"source": {"type": "official", "name": "DBT Bharat (dbtbharat.gov.in) State/UT list",
                                                           "url": "https://dbtbharat.gov.in/", "last_updated": TODAY.isoformat()},
                                                "names": STATES},
                            "source": DEMO, "areas": areas},
             "demographics.json": {"source": DEMO, "profiles": demo},
             "infrastructure.json": {"source": DEMO, "profiles": infra},
             "investments.json": {"source": DEMO, "projects": invest},
             "requests_seed.json": {"source": DEMO, "requests": reqs}}
    for name, data in files.items():
        (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(areas)} areas, {len(demo)} demographic, {len(infra)} infrastructure, {len(invest)} projects, {len(reqs)} requests")


if __name__ == "__main__":
    main()
