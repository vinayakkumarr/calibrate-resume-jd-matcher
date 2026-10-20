"""
Focused Regression Test Suite: JD Experience Parsing & Scoring Safeguard Verification
Verifies:
1. Fix for TC-04: 'Minimum 5 years of professional experience' -> 5.0.
2. Fix for TC-08: 'Minimum 4 years of verified professional software engineering experience' -> 4.0.
3. Supported JD formats: 'at least 3 years', 'minimum of 2.5 years', '3+ years experience with Go', '5+ years of software development experience'.
4. Negative and ambiguous cases (ranges, company founding dates, multiple numbers).
5. Scoring safeguard test: 5-year requirement + 1.5-year candidate tenure -> 30.0% experience score.
"""

import os
import sys
import unittest

engine_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'engine'))
if engine_dir not in sys.path:
    sys.path.insert(0, engine_dir)

from parsers.date_parser import extract_required_years_from_jd, extract_candidate_tenure
from scorer import calculate_deterministic_scores


class TestDateParserRegression(unittest.TestCase):

    def test_01_tc04_and_tc08_intervening_descriptors(self):
        """Verifies parsing when descriptive words appear between 'years of' and 'experience'."""
        tc04_jd = "Role: Cloud Infrastructure Architect.\nRequirements:\n- Minimum 5 years of professional experience.\n- AWS Certified."
        tc08_jd = "Role: Senior Software Engineer.\nRequirements:\n- Minimum 4 years of verified professional software engineering experience.\n- Python & MySQL."

        self.assertEqual(extract_required_years_from_jd(tc04_jd), 5.0, "TC-04 must parse 5.0 years.")
        self.assertEqual(extract_required_years_from_jd(tc08_jd), 4.0, "TC-08 must parse 4.0 years.")

    def test_02_standard_supported_formats(self):
        """Verifies all standard experience requirement expressions."""
        cases = [
            ("At least 3 years of hands-on industry experience.", 3.0),
            ("At least 3 years in a production environment.", 3.0),
            ("Minimum of 2.5 years in backend systems.", 2.5),
            ("Minimum 2 years.", 2.0),
            ("3+ years experience with Go.", 3.0),
            ("5+ years of software development experience.", 5.0),
            ("Requires 4+ years in software engineering.", 4.0),
            ("Minimum of 6 years relevant experience.", 6.0)
        ]
        for jd_text, expected in cases:
            actual = extract_required_years_from_jd(jd_text)
            self.assertEqual(actual, expected, f"Failed for '{jd_text}': expected {expected}, got {actual}")

    def test_03_experience_ranges_extract_lower_bound(self):
        """Verifies that experience ranges extract the lower bound."""
        cases = [
            ("3-5 years of experience in Python.", 3.0),
            ("2 to 4 years experience.", 2.0),
            ("5 - 8 years of relevant experience.", 5.0)
        ]
        for jd_text, expected in cases:
            actual = extract_required_years_from_jd(jd_text)
            self.assertEqual(actual, expected, f"Range failed for '{jd_text}': expected {expected}, got {actual}")

    def test_04_negative_and_ambiguous_non_requirements(self):
        """Verifies that non-requirement numbers (company age, growth, graduation) are NOT overmatched."""
        negative_cases = [
            "Company founded 10 years ago.",
            "Over the past 5 years we have grown to 100 employees.",
            "Within 2 years of graduation.",
            "Entry-level role for freshers. 0-1 years.",
            "Looking for an intern. Junior full stack developer.",
            "No experience required."
        ]
        for jd_text in negative_cases:
            actual = extract_required_years_from_jd(jd_text)
            self.assertEqual(actual, 0.0, f"Overmatched on non-requirement '{jd_text}': got {actual}, expected 0.0")

    def test_05_multiple_numbers_in_same_jd(self):
        """Verifies that irrelevant numbers (team size, servers, funding) do not override the requirement."""
        complex_jd = (
            "We are a team of 50 engineers managing 200 microservices across 15 global regions. "
            "Our company was founded 8 years ago. "
            "Requirements: Minimum 3 years of software engineering experience with Python."
        )
        self.assertEqual(extract_required_years_from_jd(complex_jd), 3.0, "Must extract 3.0 years, ignoring 50, 200, 15, and 8.")

    def test_06_scoring_safeguard_tenure_deficit_vs_zero_masking(self):
        """
        Scoring Safeguard Investigation Test:
        Demonstrates that a candidate with 1.5 years experience against a 5.0-year requirement
        correctly receives 30.0% experience score, but would be falsely inflated to 100.0%
        if an extraction failure silently defaults required_years to 0.0.
        """
        # Scenario A: Correctly identified 5.0 year requirement
        correct_report = {
            "must_haves": [{"requirement": "Python", "status": "MATCHED"}],
            "bonus_skills": [],
            "experience_years": {"required_years": 5.0, "candidate_years": 1.5}
        }
        scores_correct = calculate_deterministic_scores(correct_report)
        self.assertEqual(scores_correct["experience_score"], 30.0, "1.5y / 5.0y must yield 30.0% experience score.")
        self.assertEqual(scores_correct["overall_score"], 76.67, "Overall score must reflect 30.0% experience component renormalized across active criteria.")

        # Scenario B: Remediated behavior where required_years is 0.0 (or unspecified)
        # Experience tenure is excluded (experience_score = None) and weights renormalized,
        # preventing unearned 100.0% experience inflation.
        masked_report = {
            "must_haves": [{"requirement": "Python", "status": "MATCHED"}],
            "bonus_skills": [],
            "experience_years": {"required_years": 0.0, "candidate_years": 1.5}
        }
        scores_masked = calculate_deterministic_scores(masked_report)
        self.assertIsNone(scores_masked["experience_score"], "Zero-required-years safely excludes experience score.")
        self.assertTrue(scores_masked.get("experience_excluded"), "experience_excluded must be True.")
        self.assertEqual(scores_masked["overall_score"], 100.0, "Overall score is renormalized across must-haves and bonus.")

    def test_07_cashier_as_cloud_architect_zero_tech_tenure(self):
        """
        Verifies resolution of the 'Cashier as Cloud Architect' experience bug:
        A candidate who worked 5 years as a grocery cashier applying for a Senior Cloud Architect job
        must receive 0.0 years technical experience and 0.0% experience score (not 100.0%).
        """
        cashier_resume = """Alex Taylor - Grocery Cashier
Experience:
Lead Cashier | SuperMart Store (Jan 2018 - Dec 2022)
- Handled point-of-sale customer checkout and cash handling.
- Reconciled drawer balances and assisted store shoppers with grocery items.
- Stocked dairy and dry goods shelves.
"""
        cloud_architect_jd = """Role: Senior Cloud Infrastructure Architect.
Requirements:
- Minimum 5 years of professional cloud engineering experience.
- Kubernetes, Terraform, and AWS solutions.
"""
        req_years = extract_required_years_from_jd(cloud_architect_jd)
        self.assertEqual(req_years, 5.0, "JD requires 5.0 years.")

        tenure = extract_candidate_tenure(cashier_resume)
        self.assertEqual(tenure["candidate_years"], 0.0, "Grocery cashier must have 0.0 technical years.")
        self.assertEqual(tenure["technical_years"], 0.0, "Technical years must be 0.0.")
        self.assertEqual(tenure["general_workforce_years"], 5.0, "General workforce tenure must reflect 5.0 years.")

        report = {
            "must_haves": [{"requirement": "AWS solutions", "status": "MISSING"}],
            "bonus_skills": [],
            "experience_years": {
                "required_years": req_years,
                "candidate_years": tenure["candidate_years"],
                "technical_years": tenure["technical_years"],
                "general_workforce_years": tenure["general_workforce_years"],
                "requirement_status": "SPECIFIED"
            }
        }
        scores = calculate_deterministic_scores(report)
        self.assertEqual(scores["experience_score"], 0.0, "Cashier experience score must be 0.0%, NOT 100.0%!")
        self.assertEqual(scores["overall_score"], 0.0, "Overall score must be 0.0% due to deal-breaker and zero tenure.")

    def test_08_career_changer_dual_tenure(self):
        """
        Verifies dual-tenure handling for legitimate career changers:
        4 years retail cashier + 2 years software developer = 2.0 technical years out of 6.0 total workforce years.
        """
        career_changer_resume = """Jordan Reed - Software Engineer
Experience:
Software Engineer | Acme Tech (Jan 2024 - Dec 2025)
- Developed REST APIs in Python and configured PostgreSQL databases.
- Deployed microservices to AWS ECS.

Grocery Cashier | Metro Market (Jan 2020 - Dec 2023)
- Processed customer transactions at register.
- Assisted retail shoppers and managed inventory stocking.
"""
        tenure = extract_candidate_tenure(career_changer_resume)
        self.assertEqual(tenure["candidate_years"], 2.0, "Career changer must receive exactly 2.0 technical years.")
        self.assertEqual(tenure["technical_years"], 2.0, "Technical years must be 2.0.")
        self.assertEqual(tenure["general_workforce_years"], 6.0, "General workforce years must be 6.0 years.")

        # Against a 4.0 year requirement, 2.0 tech years yields 50.0% experience score
        report = {
            "must_haves": [{"requirement": "Python", "status": "MATCHED"}],
            "bonus_skills": [],
            "experience_years": {
                "required_years": 4.0,
                "candidate_years": tenure["candidate_years"],
                "technical_years": tenure["technical_years"],
                "general_workforce_years": tenure["general_workforce_years"],
                "requirement_status": "SPECIFIED"
            }
        }
        scores = calculate_deterministic_scores(report)
        self.assertEqual(scores["experience_score"], 50.0, "2.0y / 4.0y must yield exactly 50.0% experience score.")

    def test_09_academic_degree_spans_excluded_from_employment_tenure(self):
        """
        Verifies that university degrees are NOT falsely counted as 4 years of employment tenure.
        """
        student_resume = """Taylor Swift - Computer Science Graduate
Education:
B.S. in Computer Science | State University (2020 - 2024)
- GPA 3.8/4.0
"""
        tenure = extract_candidate_tenure(student_resume)
        self.assertEqual(tenure["candidate_years"], 0.0, "Pure college degree span must not count as work experience.")
        self.assertEqual(tenure["general_workforce_years"], 0.0, "Workforce years must be 0.0.")

    def test_10_retail_with_technical_substance_preserved(self):
        """
        Verifies that hybrid roles with technical substance (e.g. POS admin, IT support) are preserved.
        """
        hybrid_resume = """Morgan Kelly - Systems Support
Experience:
Retail Store & POS Systems Admin | Best Buy (Jan 2022 - Dec 2023)
- Maintained point-of-sale computer network, resolved software crashes, and configured MySQL inventory database.
"""
        tenure = extract_candidate_tenure(hybrid_resume)
        self.assertEqual(tenure["technical_years"], 2.0, "Retail role with IT/software/SQL substance must count as technical.")

    def test_11_yoe_extraction_in_jds(self):
        """
        Verifies that 'YOE' (Years of Experience) in modern tech JDs is parsed deterministically.
        """
        cases = [
            ("Candidate must have 6+ YOE in Go and distributed systems.", 6.0),
            ("Requires 5 YOE in backend development.", 5.0),
            ("Minimum 4 YOE with AWS.", 4.0),
            ("3-5 YOE in Kubernetes and cloud networking.", 3.0),
            ("At least 7 YOE.", 7.0)
        ]
        for jd, expected in cases:
            actual = extract_required_years_from_jd(jd)
            self.assertEqual(actual, expected, f"Failed for '{jd}': expected {expected}, got {actual}")

    def test_12_pre_2000_and_long_tenure_parsing(self):
        """
        Verifies that tenures starting in the 1990s and careers spanning >25 years are accurately parsed.
        """
        # Pre-2000 start: Jan 1998 to Dec 2005 (8 years = 96 months)
        pre_2000_resume = """Alex Vance - Principal Architect
Experience:
Senior Software Engineer | Sun Microsystems (Jan 1998 - Dec 2005)
- Architected Java enterprise distributed middleware.
"""
        tenure = extract_candidate_tenure(pre_2000_resume)
        self.assertEqual(tenure["candidate_years"], 8.0, "Pre-2000 tenure (1998-2005) must extract 8.0 years.")

        # Single tenure > 25 years: Jan 1995 to Dec 2023 (29 years = 348 months)
        long_tenure_resume = """David Bowman - Chief Scientist
Experience:
Distinguished Engineer | IBM Research (Jan 1995 - Dec 2023)
- Directed supercomputing architecture and high-performance algorithms.
"""
        tenure_long = extract_candidate_tenure(long_tenure_resume)
        self.assertEqual(tenure_long["candidate_years"], 29.0, "Long tenure (>25y) must not be dropped.")

    def test_13_numeric_slash_and_word_separators(self):
        """
        Verifies that numeric dates (MM/YYYY, MM.YYYY) and word separators ('to', 'until') are parsed.
        """
        # Slash format: 01/2020 - 12/2022 (36 months = 3.0 years)
        slash_resume = """Jordan Cole - Developer
Experience:
Software Engineer | Acme Labs (01/2020 - 12/2022)
- Built microservices in Python.
"""
        tenure_slash = extract_candidate_tenure(slash_resume)
        self.assertEqual(tenure_slash["candidate_years"], 3.0, "Slash format (01/2020 - 12/2022) must yield 3.0 years.")

        # Word separator 'to': Jan 2021 to Dec 2023 (36 months = 3.0 years)
        word_sep_resume = """Chris Evans - Backend Engineer
Experience:
Backend Engineer | CloudCorp (Jan 2021 to Dec 2023)
- Maintained PostgreSQL databases and Golang APIs.
"""
        tenure_word = extract_candidate_tenure(word_sep_resume)
        self.assertEqual(tenure_word["candidate_years"], 3.0, "'to' separator must yield 3.0 years.")


if __name__ == '__main__':
    unittest.main()
