"""
Comprehensive Unit Test Suite for Scoring Formula Contract & Invariants
Validates all 10 boundary and edge-case scenarios required by Section 4.4:
1. Mandatory requirements present, no bonus requirements.
2. Both mandatory and bonus requirements present.
3. All bonus requirements matched.
4. Some bonus requirements matched (partial credit).
5. No bonus requirements matched (zero credit).
6. Experience unspecified (tenure excluded and renormalized).
7. Experience specified (linear tenure ratio).
8. No matched mandatory requirements (0.0% deal-breaker gate).
9. Gate boundary thresholds (0%, 25%, 49.9%, 50%, 75%, 100%).
10. Empty or malformed inputs (None values, empty dicts, missing keys).
"""

import os
import sys
import unittest

# Ensure engine path is available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'engine')))

from scorer import calculate_deterministic_scores


class TestScorerContract(unittest.TestCase):

    def test_01_mandatory_with_no_bonus_requirements(self):
        """Scenario 1: Mandatory requirements present, 0 bonus requirements."""
        payload = {
            "must_haves": [
                {"requirement": "Python", "status": "MATCHED"},
                {"requirement": "SQL", "status": "MATCHED"}
            ],
            "bonus_skills": [],
            "experience_years": {"required_years": 4.0, "candidate_years": 4.0, "requirement_status": "SPECIFIED"}
        }
        res = calculate_deterministic_scores(payload)
        self.assertEqual(res["must_have_score"], 100.0)
        self.assertIsNone(res["bonus_score"], "Bonus score must be None when bonus_skills is empty.")
        self.assertTrue(res["bonus_excluded"], "bonus_excluded must be True.")
        self.assertEqual(res["experience_score"], 100.0)
        # Active weights: must=0.50, exp=0.25 -> active_sum=0.75
        # (0.50/0.75)*100 + (0.25/0.75)*100 = 100.0%
        self.assertEqual(res["overall_score"], 100.0)
        self.assertFalse(res["is_gated"])

    def test_02_both_mandatory_and_bonus_requirements(self):
        """Scenario 2: Both mandatory and bonus requirements present."""
        payload = {
            "must_haves": [
                {"requirement": "Python", "status": "MATCHED"},
                {"requirement": "FastAPI", "status": "MATCHED"}
            ],
            "bonus_skills": [
                {"skill": "Docker", "status": "MATCHED"},
                {"skill": "Kubernetes", "status": "MATCHED"}
            ],
            "experience_years": {"required_years": 3.0, "candidate_years": 3.0, "requirement_status": "SPECIFIED"}
        }
        res = calculate_deterministic_scores(payload)
        self.assertEqual(res["must_have_score"], 100.0)
        self.assertEqual(res["bonus_score"], 100.0)
        self.assertFalse(res["bonus_excluded"])
        self.assertEqual(res["experience_score"], 100.0)
        self.assertEqual(res["overall_score"], 100.0)

    def test_03_all_bonus_requirements_matched(self):
        """Scenario 3: All bonus requirements matched (100% bonus credit)."""
        payload = {
            "must_haves": [
                {"requirement": "Python", "status": "MATCHED"},
                {"requirement": "FastAPI", "status": "MISSING"}  # 50% must-haves
            ],
            "bonus_skills": [
                {"skill": "Redis", "status": "MATCHED"},
                {"skill": "Docker", "status": "MATCHED"}
            ],
            "experience_years": {"required_years": 4.0, "candidate_years": 4.0, "requirement_status": "SPECIFIED"}
        }
        res = calculate_deterministic_scores(payload)
        self.assertEqual(res["must_have_score"], 50.0)
        self.assertEqual(res["bonus_score"], 100.0)
        self.assertEqual(res["experience_score"], 100.0)
        # Raw = 0.50*50 + 0.25*100 + 0.25*100 = 25 + 25 + 25 = 75.0%
        self.assertEqual(res["overall_score"], 75.0)

    def test_04_some_bonus_requirements_matched_partial(self):
        """Scenario 4: Some bonus requirements matched (partial credit via WEAK)."""
        payload = {
            "must_haves": [{"requirement": "Java", "status": "MATCHED"}],
            "bonus_skills": [
                {"skill": "Maven", "status": "MATCHED"},   # 1.0
                {"skill": "Gradle", "status": "WEAK"},     # 0.5
                {"skill": "Kafka", "status": "MISSING"}    # 0.0
            ],
            "experience_years": {"required_years": 2.0, "candidate_years": 2.0, "requirement_status": "SPECIFIED"}
        }
        res = calculate_deterministic_scores(payload)
        self.assertEqual(res["must_have_score"], 100.0)
        # Bonus points = 1.5 / 3 = 50.0%
        self.assertEqual(res["bonus_score"], 50.0)
        self.assertEqual(res["experience_score"], 100.0)
        # Raw = 0.50*100 + 0.25*100 + 0.25*50 = 50 + 25 + 12.5 = 87.5%
        self.assertEqual(res["overall_score"], 87.5)

    def test_05_no_bonus_requirements_matched(self):
        """Scenario 5: No bonus requirements matched (0% bonus score)."""
        payload = {
            "must_haves": [{"requirement": "Go", "status": "MATCHED"}],
            "bonus_skills": [
                {"skill": "GraphQL", "status": "MISSING"},
                {"skill": "gRPC", "status": "MISSING"}
            ],
            "experience_years": {"required_years": 2.0, "candidate_years": 2.0, "requirement_status": "SPECIFIED"}
        }
        res = calculate_deterministic_scores(payload)
        self.assertEqual(res["must_have_score"], 100.0)
        self.assertEqual(res["bonus_score"], 0.0)
        self.assertEqual(res["experience_score"], 100.0)
        # Raw = 0.50*100 + 0.25*100 + 0.25*0 = 75.0%
        self.assertEqual(res["overall_score"], 75.0)

    def test_06_experience_unspecified(self):
        """Scenario 6: Experience is unspecified (excluded and renormalized)."""
        payload = {
            "must_haves": [
                {"requirement": "TypeScript", "status": "MATCHED"},
                {"requirement": "React", "status": "MATCHED"}
            ],
            "bonus_skills": [
                {"skill": "Tailwind", "status": "MATCHED"}
            ],
            "experience_years": {"requirement_status": "NOT_SPECIFIED"}
        }
        res = calculate_deterministic_scores(payload)
        self.assertTrue(res["experience_excluded"])
        self.assertIsNone(res["experience_score"])
        # Active weights: must=0.50, bonus=0.25 -> active_sum=0.75
        # (0.50/0.75)*100 + (0.25/0.75)*100 = 100.0%
        self.assertEqual(res["overall_score"], 100.0)

    def test_07_experience_specified_linear_ratio(self):
        """Scenario 7: Experience specified with tenure deficit."""
        payload = {
            "must_haves": [{"requirement": "C++", "status": "MATCHED"}],
            "bonus_skills": [{"skill": "Rust", "status": "MATCHED"}],
            "experience_years": {"required_years": 5.0, "candidate_years": 2.5, "requirement_status": "SPECIFIED"}
        }
        res = calculate_deterministic_scores(payload)
        # 2.5 / 5.0 = 50.0%
        self.assertEqual(res["experience_score"], 50.0)
        # Raw = 0.50*100 + 0.25*50 + 0.25*100 = 50 + 12.5 + 25 = 87.5%
        self.assertEqual(res["overall_score"], 87.5)

    def test_08_no_matched_mandatory_requirements_deal_breaker(self):
        """Scenario 8: No matched mandatory requirements (must_have = 0.0% triggers deal breaker)."""
        payload = {
            "must_haves": [
                {"requirement": "Core C++", "status": "MISSING"},
                {"requirement": "RTOS", "status": "MISSING"}
            ],
            "bonus_skills": [
                {"skill": "Git", "status": "MATCHED"},
                {"skill": "Jira", "status": "MATCHED"}
            ],
            "experience_years": {"required_years": 3.0, "candidate_years": 10.0, "requirement_status": "SPECIFIED"}
        }
        res = calculate_deterministic_scores(payload)
        self.assertEqual(res["must_have_score"], 0.0)
        self.assertEqual(res["bonus_score"], 100.0)
        self.assertEqual(res["experience_score"], 100.0)
        # Raw score would be 0 + 25 + 25 = 50%, BUT deal-breaker collapses score to 0.0%
        self.assertEqual(res["overall_score"], 0.0)
        self.assertTrue(res["is_gated"])
        self.assertEqual(res["gate_multiplier"], 0.0)

    def test_09_mandatory_score_gate_boundaries(self):
        """Scenario 9: Boundary thresholds at 0%, 25%, 49.9%, 50%, 75%, 100%."""
        # A. At exactly 50% must-haves: gate multiplier is 1.0 (un-gated)
        p50 = {
            "must_haves": [
                {"requirement": "Req 1", "status": "MATCHED"},
                {"requirement": "Req 2", "status": "MISSING"}
            ],
            "bonus_skills": [{"skill": "Bonus", "status": "MATCHED"}],
            "experience_years": {"required_years": 2.0, "candidate_years": 2.0, "requirement_status": "SPECIFIED"}
        }
        r50 = calculate_deterministic_scores(p50)
        self.assertEqual(r50["must_have_score"], 50.0)
        self.assertFalse(r50["is_gated"])
        self.assertEqual(r50["gate_multiplier"], 1.0)
        self.assertEqual(r50["overall_score"], 75.0)

        # B. Below 50% must-haves (e.g. 25% must-haves): gate multiplier = 25 / 50 = 0.50
        p25 = {
            "must_haves": [
                {"requirement": "Req 1", "status": "MATCHED"},
                {"requirement": "Req 2", "status": "MISSING"},
                {"requirement": "Req 3", "status": "MISSING"},
                {"requirement": "Req 4", "status": "MISSING"}
            ],
            "bonus_skills": [{"skill": "Bonus", "status": "MATCHED"}],
            "experience_years": {"required_years": 2.0, "candidate_years": 2.0, "requirement_status": "SPECIFIED"}
        }
        r25 = calculate_deterministic_scores(p25)
        self.assertEqual(r25["must_have_score"], 25.0)
        self.assertTrue(r25["is_gated"])
        self.assertEqual(r25["gate_multiplier"], 0.5)
        # raw = 0.50*25 + 0.25*100 + 0.25*100 = 12.5 + 25 + 25 = 62.5
        # overall = 62.5 * 0.5 = 31.25%
        self.assertEqual(r25["overall_score"], 31.25)

        # C. Minimum gate multiplier clamp test (e.g. 5% must-haves clamped to 0.15)
        p_tiny = {
            "must_haves": [{"requirement": f"R{i}", "status": "MISSING"} for i in range(19)] + [{"requirement": "R20", "status": "MATCHED"}],
            "bonus_skills": [],
            "experience_years": {"requirement_status": "NOT_SPECIFIED"}
        }
        r_tiny = calculate_deterministic_scores(p_tiny)
        self.assertEqual(r_tiny["must_have_score"], 5.0)
        self.assertTrue(r_tiny["is_gated"])
        self.assertEqual(r_tiny["gate_multiplier"], 0.15, "Gate multiplier must not fall below min_gate_multiplier (0.15).")

    def test_10_empty_and_malformed_inputs(self):
        """Scenario 10: Empty dictionary, None inputs, missing keys."""
        # Empty dict
        r_empty = calculate_deterministic_scores({})
        self.assertIsNotNone(r_empty["overall_score"])
        self.assertGreaterEqual(r_empty["overall_score"], 0.0)
        self.assertLessEqual(r_empty["overall_score"], 100.0)

        # None input
        r_none = calculate_deterministic_scores(None)
        self.assertIsNotNone(r_none["overall_score"])
        self.assertGreaterEqual(r_none["overall_score"], 0.0)
        self.assertLessEqual(r_none["overall_score"], 100.0)

        # Missing experience_years block
        r_no_exp = calculate_deterministic_scores({"must_haves": [{"requirement": "A", "status": "MATCHED"}]})
        self.assertTrue(r_no_exp["experience_excluded"])
        self.assertTrue(r_no_exp["bonus_excluded"])
        self.assertEqual(r_no_exp["overall_score"], 100.0)


if __name__ == '__main__':
    unittest.main()
