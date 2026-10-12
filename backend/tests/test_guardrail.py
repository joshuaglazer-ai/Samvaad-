from app.guardrail import check, extract_claims

TOOLS = [{
    "found": True,
    "records": [{
        "placement_rate": 74.0, "earnings_min": 12000, "earnings_max": 18500, "earnings_median": 15500,
        "sample_size": 186, "reporting_period": "FY 2025-26", "year": 2025,
    }],
    "source": {"title": "SAMVAAD simulated demo dataset", "reporting_period": "FY 2023-24 to FY 2025-26"},
    "costs": {"fee_max": 118000},
}]


def ok(text, tools=TOOLS):
    return check(text, tools).passed


def test_plain_and_formatted_rupees():
    assert ok("Typical earnings are ₹15,500 per month.")
    assert ok("Typical earnings are 15500 rupees.")
    assert ok("Between ₹12,000 and ₹18,500.")
    assert ok("Around Rs. 15500 a month.")


def test_k_and_thousand_formats():
    assert ok("About ₹12k to ₹18.5k a month.")
    assert ok("Around 12 thousand rupees.")
    assert ok("12-18.5 thousand per month.")  # unit applies to both ends of the range
    assert ok("ಸುಮಾರು 15.5 ಸಾವಿರ ರೂಪಾಯಿ.")


def test_lakh_conversions():
    assert ok("Fees can go up to ₹1.18 lakh.")
    assert ok("Fees can go up to ₹1.2 lakh.")  # rounded at the precision used
    assert ok("ಶುಲ್ಕ ₹1.18 ಲಕ್ಷದವರೆಗೆ.")
    assert not ok("Fees can go up to ₹2 lakh.")


def test_kannada_numerals():
    assert ok("ಶೇಕಡಾ ೭೪ ಜನರಿಗೆ ಕೆಲಸ ಸಿಕ್ಕಿದೆ.")
    assert ok("ಸಾಮಾನ್ಯ ಸಂಪಾದನೆ ₹೧೫,೫೦೦.")
    assert not ok("ಸಾಮಾನ್ಯ ಸಂಪಾದನೆ ₹೨೫,೦೦೦.")


def test_percentages():
    assert ok("74% of learners got a job.")
    assert ok("74 percent of learners got a job.")
    assert ok("ಶೇ. 74 ಕಲಿಯುವವರು")
    assert not ok("90% of learners got a job.")


def test_years_from_reporting_period_allowed():
    assert ok("This is for FY 2025-26.")
    assert ok("Data from 2023 to 2025.")
    assert not ok("In 2019 things were different.")


def test_small_integers_and_steps_ignored():
    assert ok("Here are 3 options. Step 2 is an apprenticeship. NSQF level 4.")
    assert ok("The 1st step is a job; the 5th is a degree.")


def test_school_classes_ignored():
    assert ok("After Class 12 you can join a diploma.")
    assert ok("ಅವರು 12ನೇ ತರಗತಿ ಮುಗಿಸಿದ ನಂತರ")
    assert ok("If they finished the 12th, nursing is possible.")


def test_unsupported_number_fails():
    r = check("Electricians earn ₹25,000 per month.", TOOLS)
    assert not r.passed and r.unmatched


def test_number_without_tools_fails():
    assert not check("Placement is 72%.", []).passed
    assert check("That is an important question. Let's look at 2 options.", []).passed


def test_derived_annual_figure_not_allowed():
    # 15,500 × 12 = 1,86,000 is not in the tool output → must not pass
    assert not ok("That is about ₹1,86,000 a year.")


def test_extract_claims_marks_exemptions():
    claims = extract_claims("3 options, ₹4 bonus, 72%")
    assert claims[0].exempt == "small_integer"
    assert claims[1].exempt is None  # rupee amount is never exempt
    assert claims[2].is_percent
