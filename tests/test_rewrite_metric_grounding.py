"""
Unit & Regression Tests: Priority 1 — Resume Rewrite Metric Integrity
Validates that:
1. Unsupported numeric claims are replaced with exactly '[ENTER YOUR VERIFIED METRIC]',
   with zero occurrences of the invented number in the placeholder or replacement text.
2. Authentic source metrics ('8M daily requests', '12 microservices') are preserved intact.
3. Unsupported '99.9% cluster availability' is blocked even when unrelated brackets exist.
4. Unsupported '40% reduction' is blocked even when unrelated CI metrics are mentioned.
5. Numbers elsewhere in the resume cannot ground unrelated quantified claims.
6. Technical identifiers (Python 3, ES6, HTML5, CSS3, 3NF, S3) are not treated as metrics.
7. Truthful nonnumeric rewrites generate cleanly without forced placeholders or invented numbers.
8. Placeholder and verification metadata remain correct across candidate review and edits.
"""

import os
import sys
import unittest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
engine_dir = os.path.join(project_root, 'engine')
if engine_dir not in sys.path:
    sys.path.insert(0, engine_dir)

from gemini_client import clean_and_enforce_metric_lock
from grounding_verifier import validate_and_anchor_rewrites


class TestRewriteMetricGrounding(unittest.TestCase):

    def test_01_unsupported_45ms_produces_exact_neutral_placeholder(self):
        """1. Unsupported 45ms claim produces '[ENTER YOUR VERIFIED METRIC]' with no occurrence of 45ms."""
        orig_bullet = "Designed normalized PostgreSQL schemas and optimized multi-column B-tree indexes reducing query latency."
        raw_rewrite = "Accomplished faster analytical read speeds, as measured by a 45ms reduction in average query latency, by designing 3NF normalized PostgreSQL schemas and strategic multi-column B-tree indexes."
        
        rewrites = [{"target_skill": "PostgreSQL", "original_bullet": orig_bullet, "upgraded_xyz_bullet": raw_rewrite}]
        validated = validate_and_anchor_rewrites(rewrites)
        
        res_bullet = validated[0]["upgraded_xyz_bullet"]
        # Must strictly replace 45ms with exact neutral placeholder
        self.assertNotIn("45ms", res_bullet)
        self.assertIn("[ENTER YOUR VERIFIED METRIC]", res_bullet)
        self.assertNotIn("45ms", validated[0]["upgraded_xyz_bullet"])
        # Technical identifier 3NF preserved
        self.assertIn("3NF normalized PostgreSQL schemas", res_bullet)
        # Metadata must reflect unverified metric
        self.assertFalse(validated[0]["metrics_grounded"])
        self.assertIn("45ms", validated[0]["unverified_metrics"])
        self.assertTrue(validated[0]["requires_candidate_verification"])

    def test_02_authentic_metrics_preserved_intact(self):
        """2. Genuine evidence for 8M daily requests and 12 microservices remains intact."""
        orig_bullet = "Architected 12 high-performance microservices using Python and FastAPI handling 8M daily requests."
        raw_rewrite = "Accomplished robust backend scalability, as measured by successfully processing 8M daily requests with 99.9% uptime, by architecting 12 asynchronous microservices using Python and FastAPI."
        
        rewrites = [{"target_skill": "FastAPI", "original_bullet": orig_bullet, "upgraded_xyz_bullet": raw_rewrite}]
        validated = validate_and_anchor_rewrites(rewrites)
        
        res_bullet = validated[0]["upgraded_xyz_bullet"]
        # Grounded metrics preserved
        self.assertIn("8M daily requests", res_bullet)
        self.assertIn("12 asynchronous microservices", res_bullet)
        # Hallucinated 99.9% replaced with neutral placeholder
        self.assertNotIn("99.9%", res_bullet)
        self.assertIn("[ENTER YOUR VERIFIED METRIC]", res_bullet)
        self.assertIn("99.9%", validated[0]["unverified_metrics"])
        self.assertIn("8M", validated[0]["verified_metrics"])

    def test_03_unsupported_availability_blocked_despite_unrelated_brackets(self):
        """3. Unsupported 99.9% availability is blocked even when unrelated bracketed text exists."""
        orig_bullet = "Administered Kubernetes clusters on AWS EKS for internal developer tools."
        raw_rewrite = "Accomplished 99.9% cluster availability, as measured by [uptime monitoring dashboards], by administering Kubernetes clusters on AWS EKS for internal developer tools."
        
        rewrites = [{"target_skill": "Kubernetes", "original_bullet": orig_bullet, "upgraded_xyz_bullet": raw_rewrite}]
        validated = validate_and_anchor_rewrites(rewrites)
        
        res_bullet = validated[0]["upgraded_xyz_bullet"]
        # Non-metric brackets stripped from unrelated phrase
        self.assertNotIn("[uptime monitoring dashboards]", res_bullet)
        self.assertIn("uptime monitoring dashboards", res_bullet)
        # Fabricated 99.9% replaced with exact neutral placeholder
        self.assertNotIn("99.9%", res_bullet)
        self.assertIn("[ENTER YOUR VERIFIED METRIC]", res_bullet)
        self.assertIn("99.9%", validated[0]["unverified_metrics"])

    def test_04_unsupported_build_time_reduction_blocked(self):
        """4. Unsupported 40% reduction is blocked even when unrelated CI metrics are mentioned."""
        orig_bullet = "Built automated deployment pipelines using GitLab CI for virtual machine imaging."
        raw_rewrite = "Accomplished a 40% reduction in image build times, as measured by [CI execution duration metrics], by building automated deployment pipelines using GitLab CI for virtual machine imaging."
        
        rewrites = [{"target_skill": "GitLab CI", "original_bullet": orig_bullet, "upgraded_xyz_bullet": raw_rewrite}]
        validated = validate_and_anchor_rewrites(rewrites)
        
        res_bullet = validated[0]["upgraded_xyz_bullet"]
        self.assertNotIn("40%", res_bullet)
        self.assertIn("[ENTER YOUR VERIFIED METRIC]", res_bullet)
        self.assertNotIn("[CI execution duration metrics]", res_bullet)
        self.assertIn("40%", validated[0]["unverified_metrics"])

    def test_05_number_elsewhere_in_resume_cannot_ground_unrelated_claim(self):
        """5. A number appearing elsewhere in the resume cannot ground an unrelated quantified claim."""
        # Resume has "Top 20 Rank at GeeksforGeeks" in achievements, but this database bullet has no metric
        database_bullet = "Architected normalized MySQL schema with foreign key constraints and indexed queries."
        raw_rewrite = "Accomplished 20% latency reduction by optimizing normalized MySQL schema with indexed queries."
        
        rewrites = [{"target_skill": "MySQL", "original_bullet": database_bullet, "upgraded_xyz_bullet": raw_rewrite}]
        validated = validate_and_anchor_rewrites(rewrites, resume_text="Achievements: Top 20 Rank at GeeksforGeeks.")
        
        res_bullet = validated[0]["upgraded_xyz_bullet"]
        self.assertNotIn("20%", res_bullet)
        self.assertIn("[ENTER YOUR VERIFIED METRIC]", res_bullet)
        self.assertIn("20%", validated[0]["unverified_metrics"])
        self.assertFalse(validated[0]["metrics_grounded"])

    def test_06_technical_identifiers_not_incorrectly_replaced(self):
        """6. Legitimate technical identifiers (Python 3, ES6, HTML5, CSS3, 3NF, S3) are preserved."""
        orig_bullet = "Built full stack web application with HTML5, CSS3, React (ES6), Python 3.10, and AWS S3 storage."
        raw_rewrite = "Engineered responsive web applications utilizing HTML5, CSS3, React ES6 components, Python 3.10 microservices, and Amazon S3."
        
        rewrites = [{"target_skill": "Full Stack", "original_bullet": orig_bullet, "upgraded_xyz_bullet": raw_rewrite}]
        validated = validate_and_anchor_rewrites(rewrites)
        
        res_bullet = validated[0]["upgraded_xyz_bullet"]
        self.assertIn("HTML5", res_bullet)
        self.assertIn("CSS3", res_bullet)
        self.assertIn("ES6", res_bullet)
        self.assertIn("Python 3.10", res_bullet)
        self.assertIn("S3", res_bullet)
        # Verify none of the tech identifiers were falsely flagged as unverified metrics
        for unv in validated[0]["unverified_metrics"]:
            self.assertNotIn(unv, ["HTML5", "CSS3", "ES6", "Python 3.10", "S3"])

    def test_07_truthful_nonnumeric_rewrite_without_forced_metric(self):
        """7. A nonnumeric rewrite can be generated without inventing a metric or forcing a placeholder."""
        orig_bullet = "Built full-stack platforms using PHP & MySQL with modular MVC architecture."
        truthful_rewrite = "Architected modular full-stack web applications utilizing PHP and MySQL adhering to MVC separation of concerns."
        
        rewrites = [{"target_skill": "PHP MVC", "original_bullet": orig_bullet, "upgraded_xyz_bullet": truthful_rewrite}]
        validated = validate_and_anchor_rewrites(rewrites)
        
        res_bullet = validated[0]["upgraded_xyz_bullet"]
        # Should not force any brackets or invented metrics
        self.assertEqual(res_bullet, truthful_rewrite)
        self.assertNotIn("[", res_bullet)
        self.assertTrue(validated[0]["metrics_grounded"])
        self.assertEqual(len(validated[0]["unverified_metrics"]), 0)
        self.assertFalse(validated[0]["requires_candidate_verification"])

    def test_08_placeholder_and_verification_metadata_after_edit(self):
        """8. Placeholder and verification metadata remain correct across rewrite validation."""
        orig_bullet = "Optimized database queries."
        raw_rewrite = "Optimized database queries reducing latency by 45ms."
        
        rewrites = [{"target_skill": "Database", "original_bullet": orig_bullet, "upgraded_xyz_bullet": raw_rewrite}]
        validated = validate_and_anchor_rewrites(rewrites)
        
        item = validated[0]
        self.assertFalse(item["metrics_grounded"])
        self.assertTrue(item["requires_candidate_verification"])
        self.assertEqual(item["unverified_metrics"], ["45ms"])
        self.assertIn("[ENTER YOUR VERIFIED METRIC]", item["upgraded_xyz_bullet"])

    def test_09_incompatible_units_rejected_despite_matching_numeric_token(self):
        """9. Matching numeric tokens with incompatible units (30 days vs 30 requests, 5 tickets vs 5 microservices) are rejected."""
        # Case A: 30 days vs 30 requests
        orig_days = "Delivered core platform features within 30 days."
        rewrite_requests = "Accomplished high backend throughput, handling 30 requests per second."
        val_a = validate_and_anchor_rewrites([{"target_skill": "API", "original_bullet": orig_days, "upgraded_xyz_bullet": rewrite_requests}])
        self.assertNotIn("30 requests", val_a[0]["upgraded_xyz_bullet"])
        self.assertIn("[ENTER YOUR VERIFIED METRIC]", val_a[0]["upgraded_xyz_bullet"])
        self.assertFalse(val_a[0]["metrics_grounded"])

        # Case B: 5 tickets vs 5 microservices
        orig_tickets = "Resolved 5 urgent customer support tickets per week."
        rewrite_services = "Architected 5 microservices in Python."
        val_b = validate_and_anchor_rewrites([{"target_skill": "Architecture", "original_bullet": orig_tickets, "upgraded_xyz_bullet": rewrite_services}])
        self.assertNotIn("5 microservices", val_b[0]["upgraded_xyz_bullet"])
        self.assertIn("[ENTER YOUR VERIFIED METRIC]", val_b[0]["upgraded_xyz_bullet"])
        self.assertFalse(val_b[0]["metrics_grounded"])

    def test_10_different_unit_or_context_from_other_bullet_cannot_ground(self):
        """10. A number elsewhere in the resume cannot ground a different claim when the unit or metric context differs."""
        orig_team = "Managed a team of 10 engineers."
        rewrite_latency = "Reduced server response latency by 10ms."
        val = validate_and_anchor_rewrites(
            [{"target_skill": "Performance", "original_bullet": orig_team, "upgraded_xyz_bullet": rewrite_latency}],
            resume_text="Managed a team of 10 engineers across multiple regions."
        )
        self.assertNotIn("10ms", val[0]["upgraded_xyz_bullet"])
        self.assertIn("[ENTER YOUR VERIFIED METRIC]", val[0]["upgraded_xyz_bullet"])
        self.assertFalse(val[0]["metrics_grounded"])

    def test_11_fallback_path_cannot_reintroduce_unsupported_quantified_claims(self):
        """11. Fallback paths (original_bullet=None) cannot reintroduce invented numbers or ranges."""
        raw_bullet = "Accomplished 25% efficiency gain by reducing query latency by 45ms."
        fallback_res = clean_and_enforce_metric_lock(raw_bullet, original_bullet=None)
        # Must not contain fabricated ranges like [25% - e.g., 20-30%] or [sub-250ms]
        self.assertNotIn("25%", fallback_res)
        self.assertNotIn("45ms", fallback_res)
        self.assertNotIn("e.g.", fallback_res)
        self.assertIn("[ENTER YOUR VERIFIED METRIC]", fallback_res)

    def test_12_empty_or_malformed_source_evidence_handled_conservatively(self):
        """12. Empty, malformed, or missing source evidence is handled conservatively."""
        raw_rewrite = "Scaled microservices to process 1000 transactions per second."
        # Missing original bullet
        val_empty = validate_and_anchor_rewrites([{"target_skill": "Scale", "original_bullet": "", "upgraded_xyz_bullet": raw_rewrite}])
        self.assertNotIn("1000", val_empty[0]["upgraded_xyz_bullet"])
        self.assertIn("[ENTER YOUR VERIFIED METRIC]", val_empty[0]["upgraded_xyz_bullet"])
        self.assertFalse(val_empty[0]["metrics_grounded"])
        self.assertTrue(val_empty[0]["requires_candidate_verification"])


if __name__ == "__main__":
    unittest.main()
