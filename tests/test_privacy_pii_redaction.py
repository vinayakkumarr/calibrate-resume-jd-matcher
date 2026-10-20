"""
Unit & Regression Tests: REM-04 — Candidate Contact PII Redaction
Validates that:
1. Candidate direct personal identifiers (name, email, phone, street address, social links)
   are redacted before prompt construction.
2. Technical skills, frameworks, languages, and architecture terms are 100% preserved.
3. Numeric metrics, latencies, percentages, and quantities are 100% preserved.
4. Educational institutions, degrees, and graduation date spans are 100% preserved.
5. Employer names and experience locations in the body are preserved.
6. align_candidate_against_targets() passes redacted text inside <CANDIDATE_RESUME_{nonce}>
   while maintaining authentic unredacted text for local metric verification and evidence ledger counting.
Strict safety: Zero live AI inference calls; zero network requests; zero DB mutations.
"""

import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
engine_dir = os.path.join(project_root, 'engine')
if engine_dir not in sys.path:
    sys.path.insert(0, engine_dir)

import gemini_client
from gemini_client import redact_candidate_contact_pii, align_candidate_against_targets


class TestPrivacyPiiRedaction(unittest.TestCase):

    def setUp(self):
        self.mock_client = MagicMock()
        self.sample_jd_targets = {
            "job_title_detected": "Senior Full Stack Engineer",
            "must_haves": [
                {"requirement": "PHP backend development", "domain": "Languages & Frameworks"},
                {"requirement": "React client architecture", "domain": "Languages & Frameworks"},
                {"requirement": "PostgreSQL schema design", "domain": "Database & Systems Architecture"}
            ],
            "bonus_skills": [
                {"skill": "Docker containerization", "domain": "DevOps, Cloud & Modern Stack"},
                {"skill": "Redis caching", "domain": "Database & Systems Architecture"}
            ]
        }

    def test_01_direct_contact_identifiers_scrubbed(self):
        """Verifies name, email, phone, street address, and profile links are redacted."""
        raw_resume = """Jane Doe
123 Main Street, Apt 4B, New York, NY 10001
jane.doe@example.com | (555) 123-4567 | linkedin.com/in/janedoe | github.com/janedoe

EDUCATION
Stanford University - Bachelor of Science in Computer Science (2020 - 2024)

EXPERIENCE
Software Engineer - Acme Corp, San Francisco, CA
- Built REST APIs in PHP and React handling 8M daily requests with 99.9% uptime.
"""
        redacted = redact_candidate_contact_pii(raw_resume)

        # Direct identifiers must be redacted
        self.assertNotIn("Jane Doe", redacted)
        self.assertIn("[CANDIDATE_NAME]", redacted)
        self.assertNotIn("jane.doe@example.com", redacted)
        self.assertIn("[CANDIDATE_EMAIL]", redacted)
        self.assertNotIn("(555) 123-4567", redacted)
        self.assertIn("[CANDIDATE_PHONE]", redacted)
        self.assertNotIn("123 Main Street", redacted)
        self.assertIn("[CANDIDATE_ADDRESS]", redacted)
        self.assertNotIn("linkedin.com/in/janedoe", redacted)
        self.assertIn("[LINKEDIN_PROFILE]", redacted)
        self.assertNotIn("github.com/janedoe", redacted)
        self.assertIn("[GITHUB_PROFILE]", redacted)

    def test_02_technical_skills_and_metrics_strictly_preserved(self):
        """Guarantees technical keywords, languages, and numeric claims are untouched."""
        raw_resume = """Alex Smith
alex@example.com
Full Stack Engineer
SKILLS: Python 3.10, PHP, JavaScript (ES6), HTML5, CSS3, PostgreSQL, Docker, AWS (S3, EC2), Redis
EXPERIENCE
- Optimized 3NF database queries reducing latency by 45% (sub-25ms response time).
- Orchestrated 12 microservices with Docker and Kubernetes handling 100k requests/minute.
"""
        redacted = redact_candidate_contact_pii(raw_resume)

        self.assertIn("Python 3.10", redacted)
        self.assertIn("PHP", redacted)
        self.assertIn("JavaScript (ES6)", redacted)
        self.assertIn("HTML5", redacted)
        self.assertIn("CSS3", redacted)
        self.assertIn("PostgreSQL", redacted)
        self.assertIn("Docker", redacted)
        self.assertIn("AWS (S3, EC2)", redacted)
        self.assertIn("Redis", redacted)
        self.assertIn("3NF database queries", redacted)
        self.assertIn("45%", redacted)
        self.assertIn("sub-25ms", redacted)
        self.assertIn("12 microservices", redacted)
        self.assertIn("100k requests/minute", redacted)

    def test_03_education_dates_and_institution_preserved_for_temporal_guard(self):
        """Ensures degree programs and date horizons remain intact for Temporal Horizon Guard."""
        raw_resume = """Candidate Name
candidate@email.com
EDUCATION
Bachelor of Computer Applications
NSHM College of Management and Technology, Durgapur
2023–2027 (pursuing)
"""
        redacted = redact_candidate_contact_pii(raw_resume)

        self.assertIn("Bachelor of Computer Applications", redacted)
        self.assertIn("NSHM College of Management and Technology", redacted)
        self.assertIn("2023–2027", redacted)
        self.assertIn("pursuing", redacted)

    def test_04_job_titles_in_header_not_mistaken_for_candidate_name(self):
        """Technical titles like 'Senior Software Engineer' must never be scrubbed as a name."""
        raw_resume = """Senior Software Engineer
Alex Johnson
alex@domain.org | +1 555-555-5555
Summary of technical experience...
"""
        redacted = redact_candidate_contact_pii(raw_resume)

        self.assertIn("Senior Software Engineer", redacted)
        self.assertNotIn("Alex Johnson", redacted)
        self.assertIn("[CANDIDATE_NAME]", redacted)

    def test_05_international_phone_formats_redacted(self):
        """Verifies various international phone formats are masked."""
        phones = [
            "+91 98765 43210",
            "+91-98765-43210",
            "+44 20 7946 0919",
            "+1-555-123-4567",
            "555.123.4567"
        ]
        for p in phones:
            sample = f"Candidate\n{p}\nSoftware Engineer"
            redacted = redact_candidate_contact_pii(sample)
            self.assertNotIn(p, redacted, f"Failed to redact phone: {p}")
            self.assertIn("[CANDIDATE_PHONE]", redacted)

    @patch('gemini_client._call_gemini_with_fallback')
    def test_06_align_candidate_against_targets_uses_redacted_prompt(self, mock_call):
        """Verifies prompt envelope receives redacted text while evidence ledger uses authentic length."""
        mock_call.return_value = ({
            "must_haves": [
                {"requirement": "PHP backend development", "domain": "Languages & Frameworks", "status": "MATCHED",
                 "evidence_quote": "Built REST APIs in PHP.", "defense_tip": "Discuss PHP architecture."}
            ],
            "bonus_skills": [],
            "actionable_rewrites": [
                {"target_skill": "PHP", "original_bullet": "Built REST APIs in PHP.",
                 "upgraded_xyz_bullet": "Accomplished scalable REST API delivery, as measured by sub-45ms latency, by building modular PHP endpoints.",
                 "interview_defense_tip": "Highlight latency tuning."}
            ]
        }, "mock-model")

        raw_resume = """John Doe
john.doe@example.com | (555) 987-6543 | 123 Elm Street, Austin, TX 78701
SUMMARY
Backend engineer specializing in PHP and relational database design.
EXPERIENCE
• Built REST APIs in PHP.
"""
        result = align_candidate_against_targets(
            client=self.mock_client,
            resume_text=raw_resume,
            jd_targets=self.sample_jd_targets,
            candidate_bullets=["Built REST APIs in PHP."]
        )

        self.assertTrue(mock_call.called)
        prompt = mock_call.call_args[0][1]

        # Verify prompt received REDACTED text inside <CANDIDATE_RESUME_...>
        self.assertNotIn("John Doe", prompt)
        self.assertNotIn("john.doe@example.com", prompt)
        self.assertNotIn("(555) 987-6543", prompt)
        self.assertNotIn("123 Elm Street", prompt)
        self.assertIn("[CANDIDATE_NAME]", prompt)
        self.assertIn("[CANDIDATE_EMAIL]", prompt)
        self.assertIn("[CANDIDATE_PHONE]", prompt)
        self.assertIn("[CANDIDATE_ADDRESS]", prompt)

        # Verify evidence ledger records original unredacted character count
        ledger = result.get("evidence_ledger", {})
        scoring_ev = ledger.get("scoring_evidence", {})
        self.assertEqual(scoring_ev.get("character_count"), len(raw_resume))

    def test_07_institution_and_org_names_not_mistaken_for_candidate_name(self):
        """Educational institutions and companies in header must never become [CANDIDATE_NAME]."""
        institutions = [
            "Stanford University\njane@example.com\nComputer Science",
            "IIT Bombay\njane@example.com\nComputer Science",
            "Harvard University\njane@example.com\nComputer Science",
            "Google LLC\njane@example.com\nEngineering",
            "Acme Corporation\njane@example.com\nSoftware"
        ]
        for inst in institutions:
            redacted = redact_candidate_contact_pii(inst)
            first_line = inst.splitlines()[0]
            self.assertIn(first_line, redacted, f"Institution/Company '{first_line}' was incorrectly scrubbed as candidate name!")

    def test_08_header_without_contact_indicators_not_scrubbed(self):
        """If document lacks contact details, first line is not blindly converted to [CANDIDATE_NAME]."""
        raw_text = """Algorithmic Visualizer Project
Built an interactive web platform animating graph algorithms in React and CSS3.
Implemented custom state transitions and responsive canvas rendering.
"""
        redacted = redact_candidate_contact_pii(raw_text)
        self.assertIn("Algorithmic Visualizer Project", redacted)
        self.assertNotIn("[CANDIDATE_NAME]", redacted)

    def test_09_indian_phone_formats_and_labeled_contacts(self):
        """Verifies diverse Indian phone formats and labeled contact prefixes are redacted."""
        indian_cases = [
            "Contact: +91 98765 43210\nSoftware Engineer",
            "Mobile: 9876543210\nSoftware Engineer",
            "Call: 09876543210\nSoftware Engineer",
            "Phone: +91-9876543210\nSoftware Engineer",
            "+919876543210\nDeveloper",
            "+91 9876543210\nDeveloper"
        ]
        for c in indian_cases:
            redacted = redact_candidate_contact_pii(c)
            self.assertIn("[CANDIDATE_PHONE]", redacted, f"Failed to redact Indian phone in case: {c}")


if __name__ == '__main__':
    unittest.main()

