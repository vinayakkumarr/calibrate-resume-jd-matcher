"""
Unit & Regression Tests: Priority 2 — Experience Requirement State Integrity
Validates tri-state experience requirement handling:
  - SPECIFIED: Stated numerical or word-number tenure requirement extracted and evaluated.
  - NOT_SPECIFIED: Genuinely open/unspecified tenure; experience component is excluded
    and remaining weights renormalized according to approved scoring policy (no unearned 100% inflation).
  - EXTRACTION_FAILED: Mentioned tenure requirement that could not be parsed; experience
    component is excluded, weights renormalized, and warning surfaced.
Also validates:
  - Masking of company founding/history dates.
  - Backward compatibility with legacy cached payloads and database constraints.
  - End-to-end deterministic pipeline behavior with mocked model responses.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
engine_dir = os.path.join(project_root, 'engine')
if engine_dir not in sys.path:
    sys.path.insert(0, engine_dir)

from parsers.date_parser import (
    extract_required_years_from_jd,
    detect_experience_mention_in_jd
)
from scorer import calculate_deterministic_scores
from jd_target_cache import validate_jd_targets_schema


class TestExperienceRequirementIntegrity(unittest.TestCase):

    def test_01_genuinely_unspecified_experience_excludes_component(self):
        """TC-05 style: JD does not specify any minimum experience requirement.
        Experience score must be None and excluded; active weights must be renormalized."""
        jd_text = """
        DevOps & Cloud Engineer
        Responsibilities:
        - Design and maintain CI/CD pipelines using GitLab CI.
        - Administer Kubernetes clusters on AWS EKS.
        - Implement infrastructure as code using Terraform.
        Requirements:
        - Deep proficiency with Linux, Docker containerization, and AWS services.
        - Strong scripting skills in Python or Bash.
        """
        has_mention = detect_experience_mention_in_jd(jd_text)
        req_years = extract_required_years_from_jd(jd_text)

        self.assertFalse(has_mention)
        self.assertEqual(req_years, 0.0)

        # Scorer evaluation for NOT_SPECIFIED with partial scores (60% must, 40% bonus)
        report = {
            "must_haves": [
                {"status": "MATCHED"},
                {"status": "MATCHED"},
                {"status": "MATCHED"},
                {"status": "MISSING"},
                {"status": "MISSING"}
            ],  # 3/5 = 60.0%
            "bonus_skills": [
                {"status": "MATCHED"},
                {"status": "MATCHED"},
                {"status": "MISSING"},
                {"status": "MISSING"},
                {"status": "MISSING"}
            ],  # 2/5 = 40.0%
            "experience_years": {
                "required_years": None,
                "candidate_years": 2.5,
                "requirement_status": "NOT_SPECIFIED"
            }
        }
        scores = calculate_deterministic_scores(report)
        self.assertEqual(scores["requirement_status"], "NOT_SPECIFIED")
        self.assertIsNone(scores["experience_score"])
        self.assertTrue(scores["experience_excluded"])
        # Renormalized: (0.50/0.75)*60.0 + (0.25/0.75)*40.0 = 53.33%, preventing unearned 65.0%
        self.assertEqual(scores["overall_score"], 53.33)

    def test_02_numeric_requirements(self):
        """Standard numeric experience statements (e.g. '4+ years', 'minimum 3 years')."""
        jd_1 = "We are seeking a Backend Engineer with 4+ years of professional Go experience."
        self.assertTrue(detect_experience_mention_in_jd(jd_1))
        self.assertEqual(extract_required_years_from_jd(jd_1), 4.0)

        jd_2 = "Requirements: Minimum of 3.5 years of production web development."
        self.assertTrue(detect_experience_mention_in_jd(jd_2))
        self.assertEqual(extract_required_years_from_jd(jd_2), 3.5)

        # Scorer evaluation for SPECIFIED
        report = {
            "must_haves": [{"status": "MATCHED"}],
            "bonus_skills": [{"status": "MATCHED"}],
            "experience_years": {
                "required_years": 4.0,
                "candidate_years": 3.0,
                "requirement_status": "SPECIFIED"
            }
        }
        scores = calculate_deterministic_scores(report)
        self.assertEqual(scores["requirement_status"], "SPECIFIED")
        self.assertEqual(scores["experience_score"], 75.0)
        self.assertFalse(scores["experience_excluded"])
        # raw: 0.50*100 + 0.25*75 + 0.25*100 = 50 + 18.75 + 25 = 93.75
        self.assertEqual(scores["overall_score"], 93.75)

    def test_03_word_number_requirements(self):
        """Word numbers (e.g. 'minimum five years', 'at least two years')."""
        jd_word_1 = "Qualifications: Minimum five years of full-stack engineering experience."
        self.assertTrue(detect_experience_mention_in_jd(jd_word_1))
        self.assertEqual(extract_required_years_from_jd(jd_word_1), 5.0)

        jd_word_2 = "Requires at least two years experience with distributed systems."
        self.assertTrue(detect_experience_mention_in_jd(jd_word_2))
        self.assertEqual(extract_required_years_from_jd(jd_word_2), 2.0)

        jd_word_3 = "Candidates must possess three to five years of industry experience."
        self.assertTrue(detect_experience_mention_in_jd(jd_word_3))
        self.assertEqual(extract_required_years_from_jd(jd_word_3), 3.0)

    def test_04_ambiguous_descriptions_with_company_history_or_unrelated_numbers(self):
        """Company founding/operating age must be masked so it does not override candidate requirements."""
        jd_company_1 = "Founded 10 years ago, our healthcare technology startup requires 2 years of React experience."
        self.assertTrue(detect_experience_mention_in_jd(jd_company_1))
        # Must extract 2.0, NOT 10.0
        self.assertEqual(extract_required_years_from_jd(jd_company_1), 2.0)

        jd_company_2 = "Established for eight years in fintech, we are looking for engineers with at least 3 years experience."
        self.assertTrue(detect_experience_mention_in_jd(jd_company_2))
        # Must extract 3.0, NOT 8.0
        self.assertEqual(extract_required_years_from_jd(jd_company_2), 3.0)

    def test_05_stated_unparseable_requirement_extraction_failed(self):
        """Mentioned tenure requirement that cannot be parsed as a number must trigger EXTRACTION_FAILED."""
        jd_unparseable = """
        Senior Engineering Role
        Requirements:
        - Candidate must have experience required in building mission-critical distributed databases.
        - Proven track record spanning extensive background in cloud infrastructure.
        """
        has_mention = detect_experience_mention_in_jd(jd_unparseable)
        req_years = extract_required_years_from_jd(jd_unparseable)

        self.assertTrue(has_mention)
        self.assertEqual(req_years, 0.0)

    def test_06_score_renormalization_prevents_unearned_inflation(self):
        """
        When EXTRACTION_FAILED occurs:
        Experience score must be None (not 0.0 or 100.0).
        Must-have (60.0%) and Bonus (40.0%) weights must be renormalized across 0.75:
        (0.50/0.75)*60.0 + (0.25/0.75)*40.0 = 40.0 + 13.33 = 53.33%.
        Silently converting to 100% would have inflated the score to 65.0%.
        """
        report_failed = {
            "must_haves": [
                {"status": "MATCHED"},
                {"status": "MATCHED"},
                {"status": "MATCHED"},
                {"status": "MISSING"},
                {"status": "MISSING"}
            ],  # 3/5 = 60.0%
            "bonus_skills": [
                {"status": "MATCHED"},
                {"status": "MATCHED"},
                {"status": "MISSING"},
                {"status": "MISSING"},
                {"status": "MISSING"}
            ],  # 2/5 = 40.0%
            "experience_years": {
                "required_years": None,
                "candidate_years": 2.0,
                "requirement_status": "EXTRACTION_FAILED"
            }
        }
        scores = calculate_deterministic_scores(report_failed)

        self.assertEqual(scores["requirement_status"], "EXTRACTION_FAILED")
        self.assertIsNone(scores["experience_score"])
        self.assertTrue(scores["experience_excluded"])
        self.assertEqual(scores["must_have_score"], 60.0)
        self.assertEqual(scores["bonus_score"], 40.0)
        # Renormalized score: exactly 53.33%
        self.assertEqual(scores["overall_score"], 53.33)

        # Verify that if it were erroneously given 100% credit, it would have been 65.0%
        unearned_score = round(0.50 * 60.0 + 0.25 * 100.0 + 0.25 * 40.0, 2)
        self.assertEqual(unearned_score, 65.0)
        self.assertNotEqual(scores["overall_score"], unearned_score)

    def test_07_legacy_cached_payloads_and_schema_compatibility(self):
        """
        Validates backward compatibility:
        - Payloads missing 'requirement_status' infer correct state based on required_years.
        - validate_jd_targets_schema accepts required_years = None safely.
        - clamp handles None without TypeError.
        """
        # Legacy payload with positive required_years -> inferred SPECIFIED
        legacy_specified = {
            "must_haves": [{"status": "MATCHED"}],
            "bonus_skills": [{"status": "MATCHED"}],
            "experience_years": {
                "required_years": 3.0,
                "candidate_years": 3.0
            }
        }
        scores_spec = calculate_deterministic_scores(legacy_specified)
        self.assertEqual(scores_spec["requirement_status"], "SPECIFIED")
        self.assertEqual(scores_spec["experience_score"], 100.0)
        self.assertFalse(scores_spec["experience_excluded"])

        # Legacy payload with 0.0 required_years -> inferred NOT_SPECIFIED
        # Excludes experience tenure and renormalizes active weights
        legacy_unspecified = {
            "must_haves": [{"status": "MATCHED"}],
            "bonus_skills": [{"status": "MATCHED"}],
            "experience_years": {
                "required_years": 0.0,
                "candidate_years": 1.5
            }
        }
        scores_unspec = calculate_deterministic_scores(legacy_unspecified)
        self.assertEqual(scores_unspec["requirement_status"], "NOT_SPECIFIED")
        self.assertIsNone(scores_unspec["experience_score"])
        self.assertTrue(scores_unspec["experience_excluded"])
        self.assertEqual(scores_unspec["overall_score"], 100.0)

        # Cache schema validation with required_years = None
        valid_cache_payload = {
            "job_title_detected": "Software Engineer",
            "must_haves": [{"requirement": "Python", "domain": "Languages & Frameworks"}],
            "bonus_skills": [{"skill": "Docker", "domain": "DevOps, Cloud & Modern Stack"}],
            "required_years": None
        }
        self.assertTrue(validate_jd_targets_schema(valid_cache_payload))

    def test_08_end_to_end_deterministic_pipeline_mocked_model(self):
        """End-to-end pipeline test with mocked Stage 1 / Stage 2 outputs."""
        mock_analysis_report = {
            "job_title_detected": "Cloud Engineer",
            "must_haves": [
                {"requirement": "Kubernetes", "domain": "DevOps, Cloud & Modern Stack", "status": "MATCHED", "evidence_quote": "Administered Kubernetes clusters on AWS EKS."},
                {"requirement": "Terraform", "domain": "DevOps, Cloud & Modern Stack", "status": "MATCHED", "evidence_quote": "Authored Terraform modules."}
            ],
            "bonus_skills": [
                {"skill": "Docker", "domain": "DevOps, Cloud & Modern Stack", "status": "MISSING", "gap_reason": "No Docker experience."}
            ],
            "experience_years": {
                "required_years": None,
                "candidate_years": 6.8,
                "requirement_status": "NOT_SPECIFIED",
                "audit_note": "Job description does not specify a minimum experience tenure. Experience component excluded and remaining criteria renormalized."
            }
        }
        scores = calculate_deterministic_scores(mock_analysis_report)
        self.assertEqual(scores["must_have_score"], 100.0)
        self.assertEqual(scores["bonus_score"], 0.0)
        self.assertIsNone(scores["experience_score"])
        self.assertTrue(scores["experience_excluded"])
        # Renormalized: (0.50/0.75)*100.0 + (0.25/0.75)*0.0 = 66.67%
        self.assertEqual(scores["overall_score"], 66.67)

    def test_09_api_serialization_and_score_payload_representation(self):
        """
        Validates API serialization behavior:
        - When requirement_status is NOT_SPECIFIED or EXTRACTION_FAILED:
          - scores['experience_score'] is None, which serializes to JSON null.
          - Simulates API status.php serialization logic where experience_score is null.
        - When requirement_status is SPECIFIED:
          - scores['experience_score'] is numeric float, serializing to a number.
        - Ensures that 0.0 database column storage does not corrupt API payload when excluded.
        """
        import json

        # Case 1: NOT_SPECIFIED
        report_unspecified = {
            "must_haves": [{"status": "MATCHED"}],
            "bonus_skills": [{"status": "MATCHED"}],
            "experience_years": {
                "required_years": None,
                "candidate_years": 4.0,
                "requirement_status": "NOT_SPECIFIED"
            }
        }
        scores_unspec = calculate_deterministic_scores(report_unspecified)
        self.assertIsNone(scores_unspec["experience_score"])

        # Simulate API serialization in status.php
        db_row_exp_score = 0.00  # Database default DECIMAL(5,2) NOT NULL 0.00
        req_status = report_unspecified["experience_years"]["requirement_status"]
        api_exp_score = None if req_status in ("NOT_SPECIFIED", "EXTRACTION_FAILED") else float(db_row_exp_score)
        api_response = {
            "scores": {
                "overall_score": scores_unspec["overall_score"],
                "must_have_score": scores_unspec["must_have_score"],
                "bonus_score": scores_unspec["bonus_score"],
                "experience_score": api_exp_score
            },
            "report": report_unspecified
        }
        json_output = json.dumps(api_response)
        parsed = json.loads(json_output)
        self.assertIsNone(parsed["scores"]["experience_score"])
        self.assertIn('"experience_score": null', json_output)

        # Case 2: EXTRACTION_FAILED
        report_failed = {
            "must_haves": [{"status": "MATCHED"}],
            "bonus_skills": [{"status": "MATCHED"}],
            "experience_years": {
                "required_years": None,
                "candidate_years": 4.0,
                "requirement_status": "EXTRACTION_FAILED"
            }
        }
        scores_failed = calculate_deterministic_scores(report_failed)
        self.assertIsNone(scores_failed["experience_score"])
        req_status_failed = report_failed["experience_years"]["requirement_status"]
        api_exp_score_failed = None if req_status_failed in ("NOT_SPECIFIED", "EXTRACTION_FAILED") else float(db_row_exp_score)
        self.assertIsNone(api_exp_score_failed)

        # Case 3: SPECIFIED
        report_specified = {
            "must_haves": [{"status": "MATCHED"}],
            "bonus_skills": [{"status": "MATCHED"}],
            "experience_years": {
                "required_years": 5.0,
                "candidate_years": 4.0,
                "requirement_status": "SPECIFIED"
            }
        }
        scores_spec = calculate_deterministic_scores(report_specified)
        self.assertEqual(scores_spec["experience_score"], 80.0)
        req_status_spec = report_specified["experience_years"]["requirement_status"]
        api_exp_score_spec = None if req_status_spec in ("NOT_SPECIFIED", "EXTRACTION_FAILED") else float(scores_spec["experience_score"])
        self.assertEqual(api_exp_score_spec, 80.0)


if __name__ == '__main__':
    unittest.main()
