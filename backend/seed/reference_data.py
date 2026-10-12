"""Pilot reference data (trades, ladders, providers). Indicative only — see docs/source_register.md.

NSQF levels and durations are indicative for the demo. Official qualification codes and awarding
bodies are intentionally left out (NULL) until verified on nqr.gov.in.
Kannada strings are AI-written and need native review.
"""

TRADES = [
    {
        "slug": "electrician", "name_en": "Electrician", "name_kn": "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್",
        "sector": "Electrical", "nsqf_level": 4, "duration_months": 24, "icon": "bolt",
        "entry_min_education": "class_10",
        "entry_requirement_en": "Passed Class 10", "entry_requirement_kn": "10ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ",
        "job_roles_en": ["Assistant Electrician", "Maintenance Electrician", "Electrical Contractor (self-employed)"],
        "job_roles_kn": ["ಸಹಾಯಕ ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", "ನಿರ್ವಹಣಾ ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", "ವಿದ್ಯುತ್ ಗುತ್ತಿಗೆದಾರ (ಸ್ವಂತ ಉದ್ಯೋಗ)"],
        "base": {"min": 12000, "median": 15500, "max": 22000, "placement": 72},
    },
    {
        "slug": "wireman", "name_en": "Wireman", "name_kn": "ವೈರ್‌ಮ್ಯಾನ್",
        "sector": "Electrical", "nsqf_level": 3, "duration_months": 24, "icon": "bolt",
        "entry_min_education": "class_8",
        "entry_requirement_en": "Passed Class 8", "entry_requirement_kn": "8ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ",
        "job_roles_en": ["Wireman", "Electrical Helper", "Building Wiring Technician"],
        "job_roles_kn": ["ವೈರ್‌ಮ್ಯಾನ್", "ವಿದ್ಯುತ್ ಸಹಾಯಕ", "ಕಟ್ಟಡ ವೈರಿಂಗ್ ತಂತ್ರಜ್ಞ"],
        "base": {"min": 10000, "median": 13000, "max": 17000, "placement": 66},
    },
    {
        "slug": "solar-pv-installer", "name_en": "Solar PV Installer", "name_kn": "ಸೌರ ಫಲಕ ಅಳವಡಿಕೆ ತಂತ್ರಜ್ಞ",
        "sector": "Green Energy", "nsqf_level": 4, "duration_months": 3, "icon": "sun",
        "entry_min_education": "class_10",
        "entry_requirement_en": "Passed Class 10", "entry_requirement_kn": "10ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ",
        "job_roles_en": ["Solar Panel Installer", "Solar Maintenance Technician", "Rooftop Solar Site Supervisor"],
        "job_roles_kn": ["ಸೌರ ಫಲಕ ಅಳವಡಿಕೆದಾರ", "ಸೌರ ನಿರ್ವಹಣಾ ತಂತ್ರಜ್ಞ", "ಮೇಲ್ಛಾವಣಿ ಸೌರ ಮೇಲ್ವಿಚಾರಕ"],
        "base": {"min": 11000, "median": 14500, "max": 20000, "placement": 68},
    },
    {
        "slug": "two-wheeler-service-technician", "name_en": "Two-Wheeler Service Technician",
        "name_kn": "ದ್ವಿಚಕ್ರ ವಾಹನ ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ",
        "sector": "Automotive", "nsqf_level": 4, "duration_months": 4, "icon": "bike",
        "entry_min_education": "class_10",
        "entry_requirement_en": "Passed Class 10", "entry_requirement_kn": "10ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ",
        "job_roles_en": ["Service Technician at a showroom", "Workshop Mechanic", "Own repair shop"],
        "job_roles_kn": ["ಶೋರೂಂನಲ್ಲಿ ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "ವರ್ಕ್‌ಶಾಪ್ ಮೆಕ್ಯಾನಿಕ್", "ಸ್ವಂತ ರಿಪೇರಿ ಅಂಗಡಿ"],
        "base": {"min": 10000, "median": 13500, "max": 18000, "placement": 70},
    },
    {
        "slug": "automotive-service-technician", "name_en": "Automotive Service Technician",
        "name_kn": "ವಾಹನ ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ",
        "sector": "Automotive", "nsqf_level": 4, "duration_months": 6, "icon": "car",
        "entry_min_education": "class_10",
        "entry_requirement_en": "Passed Class 10", "entry_requirement_kn": "10ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ",
        "job_roles_en": ["Car Service Technician", "Service Advisor (with experience)", "Workshop Supervisor"],
        "job_roles_kn": ["ಕಾರು ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "ಸರ್ವಿಸ್ ಸಲಹೆಗಾರ (ಅನುಭವದ ನಂತರ)", "ವರ್ಕ್‌ಶಾಪ್ ಮೇಲ್ವಿಚಾರಕ"],
        "base": {"min": 12000, "median": 16000, "max": 23000, "placement": 71},
    },
    {
        "slug": "ev-service-technician", "name_en": "EV Service Technician",
        "name_kn": "ವಿದ್ಯುತ್ ವಾಹನ (EV) ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ",
        "sector": "Automotive", "nsqf_level": 4, "duration_months": 4, "icon": "bolt",
        "entry_min_education": "class_10",
        "entry_requirement_en": "Passed Class 10", "entry_requirement_kn": "10ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ",
        "job_roles_en": ["EV Service Technician", "Battery Technician", "EV Charging Station Technician"],
        "job_roles_kn": ["EV ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", "ಬ್ಯಾಟರಿ ತಂತ್ರಜ್ಞ", "EV ಚಾರ್ಜಿಂಗ್ ಕೇಂದ್ರ ತಂತ್ರಜ್ಞ"],
        "base": {"min": 13000, "median": 17000, "max": 24000, "placement": 69},
    },
    {
        "slug": "general-duty-assistant", "name_en": "General Duty Assistant",
        "name_kn": "ಜನರಲ್ ಡ್ಯೂಟಿ ಅಸಿಸ್ಟೆಂಟ್ (ಆಸ್ಪತ್ರೆ ಸಹಾಯಕ)",
        "sector": "Healthcare", "nsqf_level": 4, "duration_months": 6, "icon": "heart",
        "entry_min_education": "class_10",
        "entry_requirement_en": "Passed Class 10", "entry_requirement_kn": "10ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ",
        "job_roles_en": ["Patient Care Assistant in a hospital", "Ward Assistant", "Nursing Home Assistant"],
        "job_roles_kn": ["ಆಸ್ಪತ್ರೆಯಲ್ಲಿ ರೋಗಿ ಆರೈಕೆ ಸಹಾಯಕ", "ವಾರ್ಡ್ ಸಹಾಯಕ", "ನರ್ಸಿಂಗ್ ಹೋಮ್ ಸಹಾಯಕ"],
        "base": {"min": 10000, "median": 13000, "max": 17500, "placement": 74},
    },
    {
        "slug": "home-health-aide", "name_en": "Home Health Aide", "name_kn": "ಮನೆ ಆರೋಗ್ಯ ಸಹಾಯಕ",
        "sector": "Healthcare", "nsqf_level": 4, "duration_months": 4, "icon": "heart",
        "entry_min_education": "class_10",
        "entry_requirement_en": "Passed Class 10", "entry_requirement_kn": "10ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ",
        "job_roles_en": ["Home Care Assistant", "Elder Care Assistant", "Home Nursing Support"],
        "job_roles_kn": ["ಮನೆ ಆರೈಕೆ ಸಹಾಯಕ", "ಹಿರಿಯರ ಆರೈಕೆ ಸಹಾಯಕ", "ಮನೆ ಶುಶ್ರೂಷೆ ನೆರವು"],
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


def _step(order, kind, title_en, title_kn, nsqf, req_en, req_kn, min_edu, months):
    return {
        "step_order": order, "kind": kind, "title_en": title_en, "title_kn": title_kn,
        "nsqf_level": nsqf, "entry_requirement_en": req_en, "entry_requirement_kn": req_kn,
        "entry_min_education": min_edu, "duration_months": months,
    }


AFTER_TRAINING_EN, AFTER_TRAINING_KN = "After completing this training", "ಈ ತರಬೇತಿ ಮುಗಿಸಿದ ನಂತರ"

LADDERS = {
    "electrician": [
        _step(1, "job", "Assistant Electrician", "ಸಹಾಯಕ ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", 4, AFTER_TRAINING_EN, AFTER_TRAINING_KN, "class_10", None),
        _step(2, "apprenticeship", "Paid apprenticeship with an employer", "ಉದ್ಯೋಗದಾತರೊಂದಿಗೆ ಸಂಬಳ ಸಹಿತ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್", 5, "After ITI Electrician", "ಐಟಿಐ ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ನಂತರ", "iti", 12),
        _step(3, "upskill", "Electrical Supervisor licence / advanced course", "ವಿದ್ಯುತ್ ಮೇಲ್ವಿಚಾರಕ ಪರವಾನಗಿ / ಉನ್ನತ ಕೋರ್ಸ್", 5, "With work experience", "ಕೆಲಸದ ಅನುಭವದೊಂದಿಗೆ", "iti", 6),
        _step(4, "diploma", "Diploma in Electrical Engineering (lateral entry)", "ಎಲೆಕ್ಟ್ರಿಕಲ್ ಎಂಜಿನಿಯರಿಂಗ್ ಡಿಪ್ಲೊಮಾ (ನೇರ 2ನೇ ವರ್ಷ ಪ್ರವೇಶ)", 6, "After ITI or Class 12", "ಐಟಿಐ ಅಥವಾ 12ನೇ ತರಗತಿ ನಂತರ", "iti", 24),
        _step(5, "degree", "B.E./B.Tech in Electrical (lateral entry)", "ಎಲೆಕ್ಟ್ರಿಕಲ್ ಬಿ.ಇ./ಬಿ.ಟೆಕ್ (ನೇರ ಪ್ರವೇಶ)", 7, "After Diploma", "ಡಿಪ್ಲೊಮಾ ನಂತರ", "diploma", 36),
    ],
    "wireman": [
        _step(1, "job", "Wireman / Electrical Helper", "ವೈರ್‌ಮ್ಯಾನ್ / ವಿದ್ಯುತ್ ಸಹಾಯಕ", 3, AFTER_TRAINING_EN, AFTER_TRAINING_KN, "class_8", None),
        _step(2, "apprenticeship", "Apprenticeship with an electrical contractor", "ವಿದ್ಯುತ್ ಗುತ್ತಿಗೆದಾರರ ಬಳಿ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್", 4, "After ITI Wireman", "ಐಟಿಐ ವೈರ್‌ಮ್ಯಾನ್ ನಂತರ", "iti", 12),
        _step(3, "upskill", "Electrician course (move up the ladder)", "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ಕೋರ್ಸ್ (ಏಣಿಯಲ್ಲಿ ಮೇಲಕ್ಕೆ)", 4, "Passed Class 10", "10ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ", "class_10", 24),
        _step(4, "diploma", "Diploma in Electrical Engineering", "ಎಲೆಕ್ಟ್ರಿಕಲ್ ಎಂಜಿನಿಯರಿಂಗ್ ಡಿಪ್ಲೊಮಾ", 6, "After ITI or Class 12", "ಐಟಿಐ ಅಥವಾ 12ನೇ ತರಗತಿ ನಂತರ", "iti", 24),
    ],
    "solar-pv-installer": [
        _step(1, "job", "Solar Panel Installer", "ಸೌರ ಫಲಕ ಅಳವಡಿಕೆದಾರ", 4, AFTER_TRAINING_EN, AFTER_TRAINING_KN, "class_10", None),
        _step(2, "upskill", "Solar PV Designer / Site Supervisor course", "ಸೌರ ವಿನ್ಯಾಸಕ / ಸೈಟ್ ಮೇಲ್ವಿಚಾರಕ ಕೋರ್ಸ್", 5, "With installation experience", "ಅಳವಡಿಕೆ ಅನುಭವದೊಂದಿಗೆ", "class_10", 3),
        _step(3, "apprenticeship", "Apprenticeship with a solar company", "ಸೌರ ಕಂಪನಿಯಲ್ಲಿ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್", 5, "After this training", "ಈ ತರಬೇತಿಯ ನಂತರ", "class_10", 12),
        _step(4, "diploma", "Diploma in Electrical / Renewable Energy", "ಎಲೆಕ್ಟ್ರಿಕಲ್ / ನವೀಕರಿಸಬಹುದಾದ ಇಂಧನ ಡಿಪ್ಲೊಮಾ", 6, "After Class 10 or ITI", "10ನೇ ತರಗತಿ ಅಥವಾ ಐಟಿಐ ನಂತರ", "class_10", 36),
        _step(5, "degree", "B.E./B.Tech (Electrical) via lateral entry", "ನೇರ ಪ್ರವೇಶದ ಮೂಲಕ ಬಿ.ಇ./ಬಿ.ಟೆಕ್ (ಎಲೆಕ್ಟ್ರಿಕಲ್)", 7, "After Diploma", "ಡಿಪ್ಲೊಮಾ ನಂತರ", "diploma", 36),
    ],
    "two-wheeler-service-technician": [
        _step(1, "job", "Two-Wheeler Service Technician", "ದ್ವಿಚಕ್ರ ವಾಹನ ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", 4, AFTER_TRAINING_EN, AFTER_TRAINING_KN, "class_10", None),
        _step(2, "upskill", "EV Service Technician course", "EV ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ ಕೋರ್ಸ್", 4, "After this training", "ಈ ತರಬೇತಿಯ ನಂತರ", "class_10", 4),
        _step(3, "apprenticeship", "Apprenticeship at a dealership", "ಡೀಲರ್‌ಶಿಪ್‌ನಲ್ಲಿ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್", 5, "After this training", "ಈ ತರಬೇತಿಯ ನಂತರ", "class_10", 12),
        _step(4, "diploma", "Diploma in Automobile Engineering", "ಆಟೋಮೊಬೈಲ್ ಎಂಜಿನಿಯರಿಂಗ್ ಡಿಪ್ಲೊಮಾ", 6, "After Class 10 or ITI", "10ನೇ ತರಗತಿ ಅಥವಾ ಐಟಿಐ ನಂತರ", "class_10", 36),
    ],
    "automotive-service-technician": [
        _step(1, "job", "Car Service Technician", "ಕಾರು ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", 4, AFTER_TRAINING_EN, AFTER_TRAINING_KN, "class_10", None),
        _step(2, "apprenticeship", "Apprenticeship at a car workshop", "ಕಾರು ವರ್ಕ್‌ಶಾಪ್‌ನಲ್ಲಿ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್", 5, "After this training", "ಈ ತರಬೇತಿಯ ನಂತರ", "class_10", 12),
        _step(3, "upskill", "Senior Technician / Service Advisor course", "ಹಿರಿಯ ತಂತ್ರಜ್ಞ / ಸರ್ವಿಸ್ ಸಲಹೆಗಾರ ಕೋರ್ಸ್", 5, "With work experience", "ಕೆಲಸದ ಅನುಭವದೊಂದಿಗೆ", "class_10", 6),
        _step(4, "diploma", "Diploma in Automobile Engineering", "ಆಟೋಮೊಬೈಲ್ ಎಂಜಿನಿಯರಿಂಗ್ ಡಿಪ್ಲೊಮಾ", 6, "After Class 10 or ITI", "10ನೇ ತರಗತಿ ಅಥವಾ ಐಟಿಐ ನಂತರ", "class_10", 36),
        _step(5, "degree", "B.E./B.Tech (Automobile/Mechanical) via lateral entry", "ನೇರ ಪ್ರವೇಶದ ಮೂಲಕ ಬಿ.ಇ./ಬಿ.ಟೆಕ್ (ಆಟೋಮೊಬೈಲ್/ಮೆಕ್ಯಾನಿಕಲ್)", 7, "After Diploma", "ಡಿಪ್ಲೊಮಾ ನಂತರ", "diploma", 36),
    ],
    "ev-service-technician": [
        _step(1, "job", "EV Service Technician", "EV ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ", 4, AFTER_TRAINING_EN, AFTER_TRAINING_KN, "class_10", None),
        _step(2, "upskill", "Battery Management Systems course", "ಬ್ಯಾಟರಿ ನಿರ್ವಹಣಾ ವ್ಯವಸ್ಥೆ ಕೋರ್ಸ್", 5, "After this training", "ಈ ತರಬೇತಿಯ ನಂತರ", "class_10", 3),
        _step(3, "apprenticeship", "Apprenticeship with an EV maker or dealer", "EV ತಯಾರಕರು ಅಥವಾ ಡೀಲರ್ ಬಳಿ ಅಪ್ರೆಂಟಿಸ್‌ಶಿಪ್", 5, "After this training", "ಈ ತರಬೇತಿಯ ನಂತರ", "class_10", 12),
        _step(4, "diploma", "Diploma in Automobile / Electrical Engineering", "ಆಟೋಮೊಬೈಲ್ / ಎಲೆಕ್ಟ್ರಿಕಲ್ ಎಂಜಿನಿಯರಿಂಗ್ ಡಿಪ್ಲೊಮಾ", 6, "After Class 10 or ITI", "10ನೇ ತರಗತಿ ಅಥವಾ ಐಟಿಐ ನಂತರ", "class_10", 36),
    ],
    "general-duty-assistant": [
        _step(1, "job", "Patient Care Assistant", "ರೋಗಿ ಆರೈಕೆ ಸಹಾಯಕ", 4, AFTER_TRAINING_EN, AFTER_TRAINING_KN, "class_10", None),
        _step(2, "upskill", "Advanced GDA / Critical Care Assistant", "ಉನ್ನತ GDA / ತೀವ್ರ ನಿಗಾ ಸಹಾಯಕ", 5, "With hospital experience", "ಆಸ್ಪತ್ರೆ ಅನುಭವದೊಂದಿಗೆ", "class_10", 6),
        _step(3, "diploma", "Diploma in Nursing (ANM / GNM)", "ನರ್ಸಿಂಗ್ ಡಿಪ್ಲೊಮಾ (ANM / GNM)", 5, "Passed Class 12 (GNM) / Class 10-12 (ANM)", "12ನೇ ತರಗತಿ (GNM) / 10-12ನೇ ತರಗತಿ (ANM)", "class_12", 24),
        _step(4, "degree", "B.Sc Nursing", "ಬಿ.ಎಸ್ಸಿ ನರ್ಸಿಂಗ್", 7, "Passed Class 12 with Science", "ವಿಜ್ಞಾನದೊಂದಿಗೆ 12ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ", "class_12", 48),
    ],
    "home-health-aide": [
        _step(1, "job", "Home Care Assistant", "ಮನೆ ಆರೈಕೆ ಸಹಾಯಕ", 4, AFTER_TRAINING_EN, AFTER_TRAINING_KN, "class_10", None),
        _step(2, "upskill", "General Duty Assistant course", "ಜನರಲ್ ಡ್ಯೂಟಿ ಅಸಿಸ್ಟೆಂಟ್ ಕೋರ್ಸ್", 4, "After this training", "ಈ ತರಬೇತಿಯ ನಂತರ", "class_10", 6),
        _step(3, "diploma", "Diploma in Nursing (ANM)", "ನರ್ಸಿಂಗ್ ಡಿಪ್ಲೊಮಾ (ANM)", 5, "Passed Class 12", "12ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ", "class_12", 24),
        _step(4, "degree", "B.Sc Nursing", "ಬಿ.ಎಸ್ಸಿ ನರ್ಸಿಂಗ್", 7, "Passed Class 12 with Science", "ವಿಜ್ಞಾನದೊಂದಿಗೆ 12ನೇ ತರಗತಿ ಉತ್ತೀರ್ಣ", "class_12", 48),
    ],
}

# Fictional providers. Names say "Demo" so they can never be mistaken for real institutions.
PROVIDER_TEMPLATES = [
    ("Demo Government ITI, {d}", "government_iti", ["electrician", "wireman", "automotive-service-technician"]),
    ("Demo Skill Centre, {d}", "skill_centre", ["solar-pv-installer", "two-wheeler-service-technician", "ev-service-technician"]),
    ("Demo Health Skills Academy, {d}", "private_training_partner", ["general-duty-assistant", "home-health-aide"]),
]
# Provider gap: no EV training centre in Kalaburagi.
PROVIDER_GAPS = {("ev-service-technician", "Kalaburagi")}

DISTRICT_KN = {"Bengaluru Urban": "ಬೆಂಗಳೂರು ನಗರ", "Mysuru": "ಮೈಸೂರು", "Kalaburagi": "ಕಲಬುರಗಿ", "Dharwad": "ಧಾರವಾಡ"}

DISTRICT_COORDS = {
    "Bengaluru Urban": (12.9716, 77.5946),
    "Mysuru": (12.2958, 76.6394),
    "Kalaburagi": (17.3297, 76.8343),
    "Dharwad": (15.4589, 75.0078),
}

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
