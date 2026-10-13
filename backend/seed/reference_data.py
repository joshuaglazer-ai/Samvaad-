"""Pilot reference data (trades, ladders, providers). Indicative only — see docs/source_register.md.

NSQF levels and durations are indicative for the demo. Official qualification codes and awarding
bodies are intentionally left out (NULL) until verified on nqr.gov.in.
Text is stored per language as {"en": …, "kn": …, "hi": …, "te": …}. Kannada, Hindi and Telugu strings are
AI-written and need native review (everyday spoken forms, not word-for-word translation).
"""


def L(en, kn, hi, te):  # noqa: E743 — tiny helper for a translated string
    return {"en": en, "kn": kn, "hi": hi, "te": te}


CLASS_10 = L("Passed Class 10", "10ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ", "10वीं पास", "10వ తరగతి పాస్")
CLASS_8 = L("Passed Class 8", "8ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ", "8वीं पास", "8వ తరగతి పాస్")
CLASS_12 = L("Passed Class 12", "12ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ", "12वीं पास", "12వ తరగతి పాస్")
AFTER_TRAINING = L("After completing this training", "ಈ ತರಬೇತಿ ಮುಗಿಸಿದ ನಂತರ", "यह ट्रेनिंग पूरी करने के बाद", "ఈ శిక్షణ పూర్తయ్యాక")
AFTER_THIS = L("After this training", "ಈ ತರಬೇತಿಯ ನಂತರ", "इस ट्रेनिंग के बाद", "ఈ శిక్షణ తర్వాత")
WORK_EXP = L("With work experience", "ಕೆಲಸದ ಅನುಭವದೊಂದಿಗೆ", "काम के अनुभव के साथ", "పని అనుభవంతో")
ITI_OR_12 = L("After ITI or Class 12", "ಐಟಿಐ ಅಥವಾ 12ನೇ ತರಗತಿ ನಂತರ", "आईटीआई या 12वीं के बाद", "ఐటీఐ లేదా 12వ తరగతి తర్వాత")
TEN_OR_ITI = L("After Class 10 or ITI", "10ನೇ ತರಗತಿ ಅಥವಾ ಐಟಿಐ ನಂತರ", "10वीं या आईटीआई के बाद", "10వ తరగతి లేదా ఐటీఐ తర్వాత")
AFTER_DIPLOMA = L("After Diploma", "ಡಿಪ್ಲೊಮಾ ನಂತರ", "डिप्लोमा के बाद", "డిప్లొమా తర్వాత")
SCIENCE_12 = L("Passed Class 12 with Science", "ವಿಜ್ಞಾನದೊಂದಿಗೆ 12ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ", "साइंस के साथ 12वीं पास", "సైన్స్‌తో 12వ తరగతి పాస్")
DIPLOMA_AUTO = L("Diploma in Automobile Engineering", "ಆಟೋಮೊಬೈಲ್ ಎಂಜಿನಿಯರಿಂಗ್ ಡಿಪ್ಲೊಮಾ", "ऑटोमोबाइल इंजीनियरिंग डिप्लोमा", "ఆటోమొబైల్ ఇంజనీరింగ్ డిప్లొమా")
DIPLOMA_ELEC = L("Diploma in Electrical Engineering", "ಎಲೆಕ್ಟ್ರಿಕಲ್ ಎಂಜಿನಿಯರಿಂಗ್ ಡಿಪ್ಲೊಮಾ", "इलेक्ट्रिकल इंजीनियरिंग डिप्लोमा", "ఎలక్ట్రికల్ ఇంజనీరింగ్ డిప్లొమా")
BSC_NURSING = L("B.Sc Nursing", "ಬಿ.ಎಸ್ಸಿ ನರ್ಸಿಂಗ್", "बी.एससी नर्सिंग", "బి.ఎస్సీ నర్సింగ్")

TRADES = [
    {
        "slug": "electrician", "sector": "Electrical", "nsqf_level": 4, "duration_months": 24, "icon": "bolt",
        "names": L("Electrician", "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", "इलेक्ट्रीशियन", "ఎలక్ట్రీషియన్"),
        "entry_min_education": "class_10", "entry_requirement": CLASS_10,
        "job_roles": {
            "en": ["Assistant Electrician", "Maintenance Electrician", "Electrical Contractor (self-employed)"],
            "kn": ["ಸಹಾಯಕ ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", "ನಿರ್ವಹಣಾ ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", "ವಿದ್ಯುತ್ ಗುತ್ತಿಗೆದಾರ (ಸ್ವಂತ ಉದ್ಯೋಗ)"],
            "hi": ["सहायक इलेक्ट्रीशियन", "मेंटेनेंस इलेक्ट्रीशियन", "बिजली ठेकेदार (अपना काम)"],
            "te": ["అసిస్టెంట్ ఎలక్ట్రీషియన్", "మెయింటెనెన్స్ ఎలక్ట్రీషియన్", "ఎలక్ట్రికల్ కాంట్రాక్టర్ (సొంత పని)"],
        },
        "base": {"min": 12000, "median": 15500, "max": 22000, "placement": 72},
    },
    {
        "slug": "wireman", "sector": "Electrical", "nsqf_level": 3, "duration_months": 24, "icon": "bolt",
        "names": L("Wireman", "ವೈರ್‌ಮ್ಯಾನ್", "वायरमैन", "వైర్‌మ్యాన్"),
        "entry_min_education": "class_8", "entry_requirement": CLASS_8,
        "job_roles": {
            "en": ["Wireman", "Electrical Helper", "Building Wiring Technician"],
            "kn": ["ವೈರ್‌ಮ್ಯಾನ್", "ವಿದ್ಯುತ್ ಸಹಾಯಕ", "ಕಟ್ಟಡ ವೈರಿಂಗ್ ತಂತ್ರಜ್ಞ"],
            "hi": ["वायरमैन", "बिजली सहायक", "बिल्डिंग वायरिंग टेक्नीशियन"],
            "te": ["వైర్‌మ్యాన్", "ఎలక్ట్రికల్ హెల్పర్", "భవనాల వైరింగ్ టెక్నీషియన్"],
        },
        "base": {"min": 10000, "median": 13000, "max": 17000, "placement": 66},
    },
    {
        "slug": "solar-pv-installer", "sector": "Green Energy", "nsqf_level": 4, "duration_months": 3, "icon": "sun",
        "names": L("Solar PV Installer", "ಸೌರ ಫಲಕ ಅಳವಡಿಕೆ ತಂತ್ರಜ್ಞ", "सोलर पैनल इंस्टॉलर", "సోలార్ ప్యానెల్ ఇన్‌స్టాలర్"),
        "entry_min_education": "class_10", "entry_requirement": CLASS_10,
        "job_roles": {
            "en": ["Solar Panel Installer", "Solar Maintenance Technician", "Rooftop Solar Site Supervisor"],
            "kn": ["ಸೌರ ಫಲಕ ಅಳವಡಿಕೆದಾರ", "ಸೌರ ನಿರ್ವಹಣಾ ತಂತ್ರಜ್ಞ", "ಮೇಲ್ಛಾವಣಿ ಸೌರ ಮೇಲ್ವಿಚಾರಕ"],
            "hi": ["सोलर पैनल इंस्टॉलर", "सोलर मेंटेनेंस टेक्नीशियन", "रूफटॉप सोलर साइट सुपरवाइज़र"],
            "te": ["సోలార్ ప్యానెల్ ఇన్‌స్టాలర్", "సోలార్ మెయింటెనెన్స్ టెక్నీషియన్", "రూఫ్‌టాప్ సోలార్ సైట్ సూపర్‌వైజర్"],
        },
        "base": {"min": 11000, "median": 14500, "max": 20000, "placement": 68},
    },
    {
        "slug": "two-wheeler-service-technician", "sector": "Automotive", "nsqf_level": 4, "duration_months": 4, "icon": "bike",
        "names": L("Two-Wheeler Service Technician", "ದ್ವಿಚಕ್ರ ವಾಹನ ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "टू-व्हीलर सर्विस टेक्नीशियन",
                   "టూ-వీలర్ సర్వీస్ టెక్నీషియన్"),
        "entry_min_education": "class_10", "entry_requirement": CLASS_10,
        "job_roles": {
            "en": ["Service Technician at a showroom", "Workshop Mechanic", "Own repair shop"],
            "kn": ["ಶೋರೂಂನಲ್ಲಿ ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "ವರ್ಕ್‌ಶಾಪ್ ಮೆಕ್ಯಾನಿಕ್", "ಸ್ವಂತ ರಿಪೇರಿ ಅಂಗಡಿ"],
            "hi": ["शोरूम में सर्विस टेक्नीशियन", "वर्कशॉप मैकेनिक", "अपनी रिपेयर दुकान"],
            "te": ["షోరూమ్‌లో సర్వీస్ టెక్నీషియన్", "వర్క్‌షాప్ మెకానిక్", "సొంత రిపేర్ షాప్"],
        },
        "base": {"min": 10000, "median": 13500, "max": 18000, "placement": 70},
    },
    {
        "slug": "automotive-service-technician", "sector": "Automotive", "nsqf_level": 4, "duration_months": 6, "icon": "car",
        "names": L("Automotive Service Technician", "ವಾಹನ ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "गाड़ी सर्विस टेक्नीशियन (ऑटोमोटिव)",
                   "వాహన సర్వీస్ టెక్నీషియన్"),
        "entry_min_education": "class_10", "entry_requirement": CLASS_10,
        "job_roles": {
            "en": ["Car Service Technician", "Service Advisor (with experience)", "Workshop Supervisor"],
            "kn": ["ಕಾರು ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "ಸರ್ವಿಸ್ ಸಲಹೆಗಾರ (ಅನುಭವದ ನಂತರ)", "ವರ್ಕ್‌ಶಾಪ್ ಮೇಲ್ವಿಚಾರಕ"],
            "hi": ["कार सर्विस टेक्नीशियन", "सर्विस एडवाइज़र (अनुभव के बाद)", "वर्कशॉप सुपरवाइज़र"],
            "te": ["కార్ సర్వీస్ టెక్నీషియన్", "సర్వీస్ అడ్వైజర్ (అనుభవం తర్వాత)", "వర్క్‌షాప్ సూపర్‌వైజర్"],
        },
        "base": {"min": 12000, "median": 16000, "max": 23000, "placement": 71},
    },
    {
        "slug": "ev-service-technician", "sector": "Automotive", "nsqf_level": 4, "duration_months": 4, "icon": "bolt",
        "names": L("EV Service Technician", "ವಿದ್ಯುತ್ ವಾಹನ (EV) ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "ईवी (इलेक्ट्रिक गाड़ी) सर्विस टेक्नीशियन",
                   "ఈవీ (ఎలక్ట్రిక్ వాహనం) సర్వీస్ టెక్నీషియన్"),
        "entry_min_education": "class_10", "entry_requirement": CLASS_10,
        "job_roles": {
            "en": ["EV Service Technician", "Battery Technician", "EV Charging Station Technician"],
            "kn": ["EV ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "ಬ್ಯಾಟರಿ ತಂತ್ರಜ್ಞ", "EV ಚಾರ್ಜಿಂಗ್ ಕೇಂದ್ರ ತಂತ್ರಜ್ಞ"],
            "hi": ["ईवी सर्विस टेक्नीशियन", "बैटरी टेक्नीशियन", "ईवी चार्जिंग स्टेशन टेक्नीशियन"],
            "te": ["ఈవీ సర్వీస్ టెక్నీషియన్", "బ్యాటరీ టెక్నీషియన్", "ఈవీ చార్జింగ్ స్టేషన్ టెక్నీషియన్"],
        },
        "base": {"min": 13000, "median": 17000, "max": 24000, "placement": 69},
    },
    {
        "slug": "general-duty-assistant", "sector": "Healthcare", "nsqf_level": 4, "duration_months": 6, "icon": "heart",
        "names": L("General Duty Assistant", "ಜನರಲ್ ಡ್ಯೂಟಿ ಅಸಿಸ್ಟೆಂಟ್ (ಆಸ್ಪತ್ರೆ ಸಹಾಯಕ)", "जनरल ड्यूटी असिस्टेंट (अस्पताल सहायक)",
                   "జనరల్ డ్యూటీ అసిస్టెంట్ (ఆసుపత్రి సహాయకుడు)"),
        "entry_min_education": "class_10", "entry_requirement": CLASS_10,
        "job_roles": {
            "en": ["Patient Care Assistant in a hospital", "Ward Assistant", "Nursing Home Assistant"],
            "kn": ["ಆಸ್ಪತ್ರೆಯಲ್ಲಿ ರೋಗಿ ಆರೈಕೆ ಸಹಾಯಕ", "ವಾರ್ಡ್ ಸಹಾಯಕ", "ನರ್ಸಿಂಗ್ ಹೋಮ್ ಸಹಾಯಕ"],
            "hi": ["अस्पताल में मरीज़ देखभाल सहायक", "वार्ड सहायक", "नर्सिंग होम सहायक"],
            "te": ["ఆసుపత్రిలో రోగి సంరక్షణ సహాయకుడు", "వార్డ్ అసిస్టెంట్", "నర్సింగ్ హోమ్ అసిస్టెంట్"],
        },
        "base": {"min": 10000, "median": 13000, "max": 17500, "placement": 74},
    },
    {
        "slug": "home-health-aide", "sector": "Healthcare", "nsqf_level": 4, "duration_months": 4, "icon": "heart",
        "names": L("Home Health Aide", "ಮನೆ ಆರೋಗ್ಯ ಸಹಾಯಕ", "होम हेल्थ एड (घर पर देखभाल सहायक)",
                   "హోమ్ హెల్త్ ఎయిడ్ (ఇంటి వద్ద సంరక్షణ సహాయకుడు)"),
        "entry_min_education": "class_10", "entry_requirement": CLASS_10,
        "job_roles": {
            "en": ["Home Care Assistant", "Elder Care Assistant", "Home Nursing Support"],
            "kn": ["ಮನೆ ಆರೈಕೆ ಸಹಾಯಕ", "ಹಿರಿಯರ ಆರೈಕೆ ಸಹಾಯಕ", "ಮನೆ ಶುಶ್ರೂಷೆ ನೆರವು"],
            "hi": ["घर पर देखभाल सहायक", "बुज़ुर्गों की देखभाल सहायक", "घर पर नर्सिंग सहायता"],
            "te": ["ఇంటి సంరక్షణ సహాయకుడు", "వృద్ధుల సంరక్షణ సహాయకుడు", "ఇంటి వద్ద నర్సింగ్ సహాయం"],
        },
        "base": {"min": 9000, "median": 12000, "max": 16000, "placement": 65},
    },
]

# District multipliers on earnings and placement offsets (demo only).
DISTRICT_FACTORS = {
    "Bengaluru Urban": {"earn": 1.22, "place": 6},
    "Mysuru": {"earn": 1.00, "place": 1},
    "Dharwad": {"earn": 0.96, "place": -2},
    "Kalaburagi": {"earn": 0.88, "place": -7},
}

YEARS = {2023: "FY 2023-24", 2024: "FY 2024-25", 2025: "FY 2025-26"}

# Intentional gaps so honest fallbacks and the Evidence Gap Radar can be demonstrated:
#  - EV Service Technician: no Kalaburagi district rows  → state fallback
#  - Home Health Aide: no Kalaburagi/Dharwad district rows and no state rows → national fallback
#  - Solar PV Installer: no FY 2025-26 rows for Dharwad (older year shown)
MISSING_DISTRICT = {
    ("ev-service-technician", "Kalaburagi"),
    ("home-health-aide", "Kalaburagi"),
    ("home-health-aide", "Dharwad"),
}
MISSING_STATE = {"home-health-aide"}
NATIONAL_ROWS = {"home-health-aide", "ev-service-technician"}
MISSING_YEAR = {("solar-pv-installer", "Dharwad", 2025)}


def _step(order, kind, title, nsqf, req, min_edu, months):
    return {"step_order": order, "kind": kind, "titles": title, "nsqf_level": nsqf, "entry_requirement": req,
            "entry_min_education": min_edu, "duration_months": months}


LADDERS = {
    "electrician": [
        _step(1, "job", L("Assistant Electrician", "ಸಹಾಯಕ ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", "सहायक इलेक्ट्रीशियन", "అసిస్టెంట్ ఎలక్ట్రీషియన్"),
              4, AFTER_TRAINING, "class_10", None),
        _step(2, "apprenticeship", L("Paid apprenticeship with an employer", "ಉದ್ಯೋಗದಾತರೊಂದಿಗೆ ಸಂಬಳ ಸಹಿತ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್",
                                     "किसी कंपनी में वेतन वाली अप्रेंटिसशिप", "సంస్థలో జీతంతో కూడిన అప్రెంటిస్‌షిప్"),
              5, L("After ITI Electrician", "ಐಟಿಐ ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ನಂತರ", "आईटीआई इलेक्ट्रीशियन के बाद", "ఐటీఐ ఎలక్ట్రీషియన్ తర్వాత"),
              "iti", 12),
        _step(3, "upskill", L("Electrical Supervisor licence / advanced course", "ವಿದ್ಯುತ್ ಮೇಲ್ವಿಚಾರಕ ಪರವಾನಗಿ / ಉನ್ನತ ಕೋರ್ಸ್",
                              "इलेक्ट्रिकल सुपरवाइज़र लाइसेंस / एडवांस कोर्स", "ఎలక్ట్రికల్ సూపర్‌వైజర్ లైసెన్స్ / అడ్వాన్స్‌డ్ కోర్సు"),
              5, WORK_EXP, "iti", 6),
        _step(4, "diploma", L("Diploma in Electrical Engineering (lateral entry)", "ಎಲೆಕ್ಟ್ರಿಕಲ್ ಎಂಜಿನಿಯರಿಂಗ್ ಡಿಪ್ಲೊಮಾ (ನೇರ 2ನೇ ವರ್ಷ ಪ್ರವೇಶ)",
                              "इलेक्ट्रिकल इंजीनियरिंग डिप्लोमा (सीधे दूसरे साल में)", "ఎలక్ట్రికల్ ఇంజనీరింగ్ డిప్లొమా (నేరుగా రెండో సంవత్సరంలో)"),
              6, ITI_OR_12, "iti", 24),
        _step(5, "degree", L("B.E./B.Tech in Electrical (lateral entry)", "ಎಲೆಕ್ಟ್ರಿಕಲ್ ಬಿ.ಇ./ಬಿ.ಟೆಕ್ (ನೇರ ಪ್ರವೇಶ)",
                             "इलेक्ट्रिकल में बी.ई./बी.टेक (लेटरल एंट्री)", "ఎలక్ట్రికల్‌లో బి.ఇ./బి.టెక్ (లేటరల్ ఎంట్రీ)"),
              7, AFTER_DIPLOMA, "diploma", 36),
    ],
    "wireman": [
        _step(1, "job", L("Wireman / Electrical Helper", "ವೈರ್‌ಮ್ಯಾನ್ / ವಿದ್ಯುತ್ ಸಹಾಯಕ", "वायरमैन / बिजली सहायक", "వైర్‌మ్యాన్ / ఎలక్ట్రికల్ హెల్పర్"),
              3, AFTER_TRAINING, "class_8", None),
        _step(2, "apprenticeship", L("Apprenticeship with an electrical contractor", "ವಿದ್ಯುತ್ ಗುತ್ತಿಗೆದಾರರ ಬಳಿ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್",
                                     "बिजली ठेकेदार के साथ अप्रेंटिसशिप", "ఎలక్ట్రికల్ కాంట్రాక్టర్ వద్ద అప్రెంటిస్‌షిప్"),
              4, L("After ITI Wireman", "ಐಟಿಐ ವೈರ್‌ಮ್ಯಾನ್ ನಂತರ", "आईटीआई वायरमैन के बाद", "ఐటీఐ వైర్‌మ్యాన్ తర్వాత"), "iti", 12),
        _step(3, "upskill", L("Electrician course (move up the ladder)", "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ಕೋರ್ಸ್ (ಏಣಿಯಲ್ಲಿ ಮೇಲಕ್ಕೆ)",
                              "इलेक्ट्रीशियन कोर्स (सीढ़ी में ऊपर)", "ఎలక్ట్రీషియన్ కోర్సు (నిచ్చెనలో పైకి)"),
              4, CLASS_10, "class_10", 24),
        _step(4, "diploma", DIPLOMA_ELEC, 6, ITI_OR_12, "iti", 24),
    ],
    "solar-pv-installer": [
        _step(1, "job", L("Solar Panel Installer", "ಸೌರ ಫಲಕ ಅಳವಡಿಕೆದಾರ", "सोलर पैनल इंस्टॉलर", "సోలార్ ప్యానెల్ ఇన్‌స్టాలర్"),
              4, AFTER_TRAINING, "class_10", None),
        _step(2, "upskill", L("Solar PV Designer / Site Supervisor course", "ಸೌರ ವಿನ್ಯಾಸಕ / ಸೈಟ್ ಮೇಲ್ವಿಚಾರಕ ಕೋರ್ಸ್",
                              "सोलर डिज़ाइनर / साइट सुपरवाइज़र कोर्स", "సోలార్ డిజైనర్ / సైట్ సూపర్‌వైజర్ కోర్సు"),
              5, L("With installation experience", "ಅಳವಡಿಕೆ ಅನುಭವದೊಂದಿಗೆ", "इंस्टॉलेशन के अनुभव के साथ", "ఇన్‌స్టలేషన్ అనుభవంతో"),
              "class_10", 3),
        _step(3, "apprenticeship", L("Apprenticeship with a solar company", "ಸೌರ ಕಂಪನಿಯಲ್ಲಿ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್",
                                     "सोलर कंपनी में अप्रेंटिसशिप", "సోలార్ కంపెనీలో అప్రెంటిస్‌షిప్"),
              5, AFTER_THIS, "class_10", 12),
        _step(4, "diploma", L("Diploma in Electrical / Renewable Energy", "ಎಲೆಕ್ಟ್ರಿಕಲ್ / ನವೀಕರಿಸಬಹುದಾದ ಇಂಧನ ಡಿಪ್ಲೊಮಾ",
                              "इलेक्ट्रिकल / रिन्यूएबल एनर्जी डिप्लोमा", "ఎలక్ట్రికల్ / పునరుత్పాదక ఇంధన డిప్లొమా"),
              6, TEN_OR_ITI, "class_10", 36),
        _step(5, "degree", L("B.E./B.Tech (Electrical) via lateral entry", "ನೇರ ಪ್ರವೇಶದ ಮೂಲಕ ಬಿ.ಇ./ಬಿ.ಟೆಕ್ (ಎಲೆಕ್ಟ್ರಿಕಲ್)",
                             "लेटरल एंट्री से बी.ई./बी.टेक (इलेक्ट्रिकल)", "లేటరల్ ఎంట్రీ ద్వారా బి.ఇ./బి.టెక్ (ఎలక్ట్రికల్)"),
              7, AFTER_DIPLOMA, "diploma", 36),
    ],
    "two-wheeler-service-technician": [
        _step(1, "job", L("Two-Wheeler Service Technician", "ದ್ವಿಚಕ್ರ ವಾಹನ ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "टू-व्हीलर सर्विस टेक्नीशियन",
                          "టూ-వీలర్ సర్వీస్ టెక్నీషియన్"), 4, AFTER_TRAINING, "class_10", None),
        _step(2, "upskill", L("EV Service Technician course", "EV ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ ಕೋರ್ಸ್", "ईवी सर्विस टेक्नीशियन कोर्स",
                              "ఈవీ సర్వీస్ టెక్నీషియన్ కోర్సు"), 4, AFTER_THIS, "class_10", 4),
        _step(3, "apprenticeship", L("Apprenticeship at a dealership", "ಡೀಲರ್‌ಶಿಪ್‌ನಲ್ಲಿ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್", "डीलरशिप में अप्रेंटिसशिप",
                                     "డీలర్‌షిప్‌లో అప్రెంటిస్‌షిప్"), 5, AFTER_THIS, "class_10", 12),
        _step(4, "diploma", DIPLOMA_AUTO, 6, TEN_OR_ITI, "class_10", 36),
    ],
    "automotive-service-technician": [
        _step(1, "job", L("Car Service Technician", "ಕಾರು ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "कार सर्विस टेक्नीशियन", "కార్ సర్వీస్ టెక్నీషియన్"),
              4, AFTER_TRAINING, "class_10", None),
        _step(2, "apprenticeship", L("Apprenticeship at a car workshop", "ಕಾರು ವರ್ಕ್‌ಶಾಪ್‌ನಲ್ಲಿ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್",
                                     "कार वर्कशॉप में अप्रेंटिसशिप", "కార్ వర్క్‌షాప్‌లో అప్రెంటిస్‌షిప్"), 5, AFTER_THIS, "class_10", 12),
        _step(3, "upskill", L("Senior Technician / Service Advisor course", "ಹಿರಿಯ ತಂತ್ರಜ್ಞ / ಸರ್ವಿಸ್ ಸಲಹೆಗಾರ ಕೋರ್ಸ್",
                              "सीनियर टेक्नीशियन / सर्विस एडवाइज़र कोर्स", "సీనియర్ టెక్నీషియన్ / సర్వీస్ అడ్వైజర్ కోర్సు"),
              5, WORK_EXP, "class_10", 6),
        _step(4, "diploma", DIPLOMA_AUTO, 6, TEN_OR_ITI, "class_10", 36),
        _step(5, "degree", L("B.E./B.Tech (Automobile/Mechanical) via lateral entry", "ನೇರ ಪ್ರವೇಶದ ಮೂಲಕ ಬಿ.ಇ./ಬಿ.ಟೆಕ್ (ಆಟೋಮೊಬೈಲ್/ಮೆಕ್ಯಾನಿಕಲ್)",
                             "लेटरल एंट्री से बी.ई./बी.टेक (ऑटोमोबाइल/मैकेनिकल)", "లేటరల్ ఎంట్రీ ద్వారా బి.ఇ./బి.టెక్ (ఆటోమొబైల్/మెకానికల్)"),
              7, AFTER_DIPLOMA, "diploma", 36),
    ],
    "ev-service-technician": [
        _step(1, "job", L("EV Service Technician", "EV ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "ईवी सर्विस टेक्नीशियन", "ఈవీ సర్వీస్ టెక్నీషియన్"),
              4, AFTER_TRAINING, "class_10", None),
        _step(2, "upskill", L("Battery Management Systems course", "ಬ್ಯಾಟರಿ ನಿರ್ವಹಣಾ ವ್ಯವಸ್ಥೆ ಕೋರ್ಸ್", "बैटरी मैनेजमेंट सिस्टम कोर्स",
                              "బ్యాటరీ మేనేజ్‌మెంట్ సిస్టమ్స్ కోర్సు"), 5, AFTER_THIS, "class_10", 3),
        _step(3, "apprenticeship", L("Apprenticeship with an EV maker or dealer", "EV ತಯಾರಕರು ಅಥವಾ ಡೀಲರ್ ಬಳಿ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್",
                                     "ईवी कंपनी या डीलर के साथ अप्रेंटिसशिप", "ఈవీ తయారీదారు లేదా డీలర్ వద్ద అప్రెంటిస్‌షిప్"),
              5, AFTER_THIS, "class_10", 12),
        _step(4, "diploma", L("Diploma in Automobile / Electrical Engineering", "ಆಟೋಮೊಬೈಲ್ / ಎಲೆಕ್ಟ್ರಿಕಲ್ ಎಂಜಿನಿಯರಿಂಗ್ ಡಿಪ್ಲೊಮಾ",
                              "ऑटोमोबाइल / इलेक्ट्रिकल इंजीनियरिंग डिप्लोमा", "ఆటోమొబైల్ / ఎలక్ట్రికల్ ఇంజనీరింగ్ డిప్లొమా"),
              6, TEN_OR_ITI, "class_10", 36),
    ],
    "general-duty-assistant": [
        _step(1, "job", L("Patient Care Assistant", "ರೋಗಿ ಆರೈಕೆ ಸಹಾಯಕ", "मरीज़ देखभाल सहायक", "రోగి సంరక్షణ సహాయకుడు"),
              4, AFTER_TRAINING, "class_10", None),
        _step(2, "upskill", L("Advanced GDA / Critical Care Assistant", "ಉನ್ನತ GDA / ತೀವ್ರ ನಿಗಾ ಸಹಾಯಕ", "एडवांस GDA / क्रिटिकल केयर सहायक",
                              "అడ్వాన్స్‌డ్ GDA / క్రిటికల్ కేర్ అసిస్టెంట్"),
              5, L("With hospital experience", "ಆಸ್ಪತ್ರೆ ಅನುಭವದೊಂದಿಗೆ", "अस्पताल के अनुभव के साथ", "ఆసుపత్రి అనుభవంతో"), "class_10", 6),
        _step(3, "diploma", L("Diploma in Nursing (ANM / GNM)", "ನರ್ಸಿಂಗ್ ಡಿಪ್ಲೊಮಾ (ANM / GNM)", "नर्सिंग डिप्लोमा (ANM / GNM)",
                              "నర్సింగ్ డిప్లొమా (ANM / GNM)"),
              5, L("Passed Class 12 (GNM) / Class 10-12 (ANM)", "12ನೇ ತರಗತಿ (GNM) / 10-12ನೇ ತರಗತಿ (ANM)",
                   "12वीं पास (GNM) / 10वीं-12वीं (ANM)", "12వ తరగతి పాస్ (GNM) / 10-12వ తరగతి (ANM)"), "class_12", 24),
        _step(4, "degree", BSC_NURSING, 7, SCIENCE_12, "class_12", 48),
    ],
    "home-health-aide": [
        _step(1, "job", L("Home Care Assistant", "ಮನೆ ಆರೈಕೆ ಸಹಾಯಕ", "घर पर देखभाल सहायक", "ఇంటి సంరక్షణ సహాయకుడు"),
              4, AFTER_TRAINING, "class_10", None),
        _step(2, "upskill", L("General Duty Assistant course", "ಜನರಲ್ ಡ್ಯೂಟಿ ಅಸಿಸ್ಟೆಂಟ್ ಕೋರ್ಸ್", "जनरल ड्यूटी असिस्टेंट कोर्स",
                              "జనరల్ డ్యూటీ అసిస్టెంట్ కోర్సు"), 4, AFTER_THIS, "class_10", 6),
        _step(3, "diploma", L("Diploma in Nursing (ANM)", "ನರ್ಸಿಂಗ್ ಡಿಪ್ಲೊಮಾ (ANM)", "नर्सिंग डिप्लोमा (ANM)", "నర్సింగ్ డిప్లొమా (ANM)"),
              5, CLASS_12, "class_12", 24),
        _step(4, "degree", BSC_NURSING, 7, SCIENCE_12, "class_12", 48),
    ],
}

# Cost / support descriptions (demo text — scheme names to verify).
COST_TEXT = {
    "fee": L("Course fee range across demo training centres. Government-run courses are often free.",
             "ಡೆಮೊ ತರಬೇತಿ ಕೇಂದ್ರಗಳ ಕೋರ್ಸ್ ಶುಲ್ಕದ ವ್ಯಾಪ್ತಿ. ಸರ್ಕಾರಿ ಕೋರ್ಸ್‌ಗಳು ಹಲವು ಬಾರಿ ಉಚಿತ.",
             "डेमो ट्रेनिंग केंद्रों में कोर्स फ़ीस की रेंज। सरकारी कोर्स अक्सर मुफ़्त होते हैं।",
             "డెమో శిక్షణ కేంద్రాలలో కోర్సు ఫీజు పరిధి. ప్రభుత్వ కోర్సులు చాలాసార్లు ఉచితం."),
    "scheme": L("Free training under a government skill scheme for eligible families (demo entry — verify the scheme name).",
                "ಅರ್ಹ ಕುಟುಂಬಗಳಿಗೆ ಸರ್ಕಾರಿ ಕೌಶಲ ಯೋಜನೆಯಡಿ ಉಚಿತ ತರಬೇತಿ (ಡೆಮೊ ಮಾಹಿತಿ — ಯೋಜನೆಯ ಹೆಸರು ಪರಿಶೀಲಿಸಬೇಕು).",
                "पात्र परिवारों के लिए सरकारी स्किल योजना में मुफ़्त ट्रेनिंग (डेमो जानकारी — योजना का नाम जाँचना है)।",
                "అర్హత ఉన్న కుటుంబాలకు ప్రభుత్వ నైపుణ్య పథకంలో ఉచిత శిక్షణ (డెమో సమాచారం — పథకం పేరు నిర్ధారించాలి)."),
    "stipend": L("Apprentices receive a monthly stipend from the employer during apprenticeship (demo entry).",
                 "ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್ ಸಮಯದಲ್ಲಿ ಉದ್ಯೋಗದಾತರಿಂದ ಮಾಸಿಕ ಸ್ಟೈಪೆಂಡ್ ಸಿಗುತ್ತದೆ (ಡೆಮೊ ಮಾಹಿತಿ).",
                 "अप्रेंटिसशिप के दौरान कंपनी से हर महीने स्टाइपेंड मिलता है (डेमो जानकारी)।",
                 "అప్రెంటిస్‌షిప్ సమయంలో సంస్థ నుండి నెలవారీ స్టైపెండ్ వస్తుంది (డెమో సమాచారం)."),
    "blr_fee": L("Course fee range in Bengaluru Urban demo centres.", "ಬೆಂಗಳೂರು ನಗರದ ಡೆಮೊ ಕೇಂದ್ರಗಳಲ್ಲಿ ಕೋರ್ಸ್ ಶುಲ್ಕದ ವ್ಯಾಪ್ತಿ.",
                 "बेंगलुरु शहरी के डेमो केंद्रों में कोर्स फ़ीस की रेंज।", "బెంగళూరు అర్బన్ డెమో కేంద్రాలలో కోర్సు ఫీజు పరిధి."),
}

# Fictional providers. Names say "Demo" so they can never be mistaken for real institutions.
PROVIDER_TEMPLATES = [
    ("Demo Government ITI, {d}", "government_iti", ["electrician", "wireman", "automotive-service-technician"]),
    ("Demo Skill Centre, {d}", "skill_centre", ["solar-pv-installer", "two-wheeler-service-technician", "ev-service-technician"]),
    ("Demo Health Skills Academy, {d}", "private_training_partner", ["general-duty-assistant", "home-health-aide"]),
]
# Provider gap: no EV training centre in Kalaburagi.
PROVIDER_GAPS = {("ev-service-technician", "Kalaburagi")}

DISTRICT_NAMES = {
    "Bengaluru Urban": L("Bengaluru Urban", "ಬೆಂಗಳೂರು ನಗರ", "बेंगलुरु शहरी", "బెంగళూరు అర్బన్"),
    "Mysuru": L("Mysuru", "ಮೈಸೂರು", "मैसूरु", "మైసూరు"),
    "Kalaburagi": L("Kalaburagi", "ಕಲಬುರಗಿ", "कलबुर्गी", "కలబురగి"),
    "Dharwad": L("Dharwad", "ಧಾರವಾಡ", "धारवाड़", "ధార్వాడ్"),
}
DISTRICT_KN = {d: v["kn"] for d, v in DISTRICT_NAMES.items()}  # kept for older imports

from app.config import DISTRICT_COORDS  # noqa: E402,F401  (kept here for older imports)

# Costs: (fee_min, fee_max) per trade at state level. Wireman intentionally has no cost data (gap).
FEES = {
    "electrician": (0, 12000),
    "solar-pv-installer": (0, 8000),
    "two-wheeler-service-technician": (0, 9000),
    "automotive-service-technician": (0, 15000),
    "ev-service-technician": (0, 14000),
    "general-duty-assistant": (0, 18000),
    "home-health-aide": (0, 10000),
}
