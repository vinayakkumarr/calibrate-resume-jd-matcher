"""
Outbound Privacy Boundary & Candidate Contact PII Redaction Test Suite.
Verifies that:
1. All supported synthetic direct contact identifiers are scrubbed.
2. Technical evidence, institutions, degrees, and metrics are 100% preserved.
3. The final outbound prompt received by the Gemini SDK boundary contains zero contact PII.
4. Redaction failure triggers a fail-safe exception and blocks outbound transmission.
5. Retries and fallback models receive strictly redacted payloads.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root and engine directory to path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENGINE_DIR = os.path.join(ROOT_DIR, 'engine')
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

from gemini_client import (
    redact_candidate_contact_pii,
    PrivacyRedactionError,
    align_candidate_against_targets,
    _call_gemini_with_fallback
)


class TestContactPIIRedaction(unittest.TestCase):
    def test_unlabeled_header_name_redaction(self):
        resume = """Jane Doe
jane.doe@example.com | (555) 123-4567 | San Francisco, CA
https://linkedin.com/in/janedoe | https://github.com/janedoe

PROFESSIONAL SUMMARY
Senior Backend Engineer with 5 years of experience in Python and PostgreSQL.
"""
        redacted = redact_candidate_contact_pii(resume)
        self.assertNotIn("Jane Doe", redacted)
        self.assertIn("[CANDIDATE_NAME]", redacted)
        self.assertIn("[CANDIDATE_EMAIL]", redacted)
        self.assertIn("[CANDIDATE_PHONE]", redacted)
        self.assertIn("[CANDIDATE_LOCATION]", redacted)
        self.assertIn("[LINKEDIN_PROFILE]", redacted)
        self.assertIn("[GITHUB_PROFILE]", redacted)
        self.assertIn("Senior Backend Engineer", redacted)
        self.assertIn("Python and PostgreSQL", redacted)

    def test_labeled_name_redaction(self):
        resume = """Candidate Name: Alex Johnson
Email: alex.j@domain.co.in
Phone: +91 98765 43210
Address: 123 Tech Park Road, Bengaluru, KA 560001
Portfolio: https://alexjohnson.dev

TECHNICAL SKILLS
Python 3.10, FastAPI, Docker, PostgreSQL 3NF.
"""
        redacted = redact_candidate_contact_pii(resume)
        self.assertNotIn("Alex Johnson", redacted)
        self.assertIn("[CANDIDATE_NAME]", redacted)
        self.assertIn("[CANDIDATE_EMAIL]", redacted)
        self.assertIn("[CANDIDATE_PHONE]", redacted)
        self.assertIn("[CANDIDATE_ADDRESS]", redacted)
        self.assertIn("[PORTFOLIO_URL]", redacted)
        self.assertIn("Python 3.10", redacted)
        self.assertIn("FastAPI", redacted)
        self.assertIn("PostgreSQL 3NF", redacted)

    def test_indian_phone_variations(self):
        cases = [
            "+91 98765 43210",
            "+91-9876543210",
            "+919876543210",
            "+91 9876543210",
        ]
        for phone in cases:
            text = f"John Doe\njohn@example.com\nMobile: {phone}\nBangalore, India\n\nExperience: Built APIs."
            redacted = redact_candidate_contact_pii(text)
            self.assertNotIn(phone, redacted, f"Failed to redact Indian phone: {phone}")
            self.assertIn("[CANDIDATE_PHONE]", redacted)

    def test_standalone_indian_phone_in_header(self):
        text = "Rahul Sharma\n98765 43210\nrahul@example.com\nMumbai, MH\n\nExperience: Developed React components."
        redacted = redact_candidate_contact_pii(text)
        self.assertNotIn("Rahul Sharma", redacted)
        self.assertNotIn("98765 43210", redacted)
        self.assertIn("[CANDIDATE_NAME]", redacted)
        self.assertIn("[CANDIDATE_PHONE]", redacted)

    def test_institution_and_degree_preservation(self):
        resume = """Stanford University
Department of Computer Science
B.Tech in Computer Science & Engineering (2020 - 2024)
IIT Bombay - Research Fellow

PROJECTS
• Architected scalable microservices for Google LLC handling 8M daily requests.
"""
        redacted = redact_candidate_contact_pii(resume)
        self.assertIn("Stanford University", redacted)
        self.assertIn("IIT Bombay", redacted)
        self.assertIn("Google LLC", redacted)
        self.assertIn("B.Tech", redacted)
        self.assertIn("8M daily requests", redacted)
        self.assertNotIn("[CANDIDATE_NAME]", redacted)

    def test_contactless_resume_preservation(self):
        resume = """Algorithmic Visualizer Platform
Full-stack web application designed for data structures education.
• Built interactive graphs with sub-250ms latency using React and Canvas API.
"""
        redacted = redact_candidate_contact_pii(resume)
        self.assertIn("Algorithmic Visualizer Platform", redacted)
        self.assertIn("sub-250ms latency", redacted)
        self.assertNotIn("[CANDIDATE_NAME]", redacted)

    def test_mailto_link_redaction(self):
        resume = """Jane Doe
Contact: mailto:jane.doe@sample.org | Tel: 415-555-0199
Experience: Cloud Infrastructure."""
        redacted = redact_candidate_contact_pii(resume)
        self.assertNotIn("jane.doe@sample.org", redacted)
        self.assertIn("[CANDIDATE_EMAIL]", redacted)
        self.assertNotIn("mailto:", redacted.lower())


class TestOutboundSDKBoundary(unittest.TestCase):
    def test_outbound_prompt_contains_zero_synthetic_identifiers(self):
        synthetic_resume = """Candidate Name: Alice Walker
alice.walker@securetech.io | +1 (415) 555-2671 | San Jose, CA
https://linkedin.com/in/alicewalker | https://github.com/alicewalker

EXPERIENCE
Software Architect at CyberCorp (2021 - Present)
• Built Kubernetes microservices in Go and Python reducing latency by 35%.
• Architected normalized PostgreSQL schemas handling 10M daily transactions.
"""
        synthetic_bullets = [
            "Built Kubernetes microservices in Go and Python reducing latency by 35%.",
            "Contact team at alice.walker@securetech.io for reference architecture."
        ]

        jd_targets = {
            "must_haves": [{"requirement": "Kubernetes and Go microservices", "domain": "Backend"}],
            "bonus_skills": [{"skill": "PostgreSQL", "domain": "Database"}]
        }

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"must_haves": [], "bonus_skills": [], "actionable_rewrites": []}'
        mock_client.models.generate_content.return_value = mock_response

        # Call Stage 2 alignment
        align_candidate_against_targets(
            client=mock_client,
            resume_text=synthetic_resume,
            jd_targets=jd_targets,
            candidate_bullets=synthetic_bullets
        )

        # Assert generate_content was called
        mock_client.models.generate_content.assert_called_once()
        _, kwargs = mock_client.models.generate_content.call_args
        outbound_prompt = kwargs.get('contents', '')

        # 1. Assert synthetic direct identifiers NEVER survive in outbound prompt
        self.assertNotIn("Alice Walker", outbound_prompt)
        self.assertNotIn("alice.walker@securetech.io", outbound_prompt)
        self.assertNotIn("(415) 555-2671", outbound_prompt)
        self.assertNotIn("San Jose, CA", outbound_prompt)
        self.assertNotIn("linkedin.com/in/alicewalker", outbound_prompt)
        self.assertNotIn("github.com/alicewalker", outbound_prompt)

        # 2. Assert placeholders exist
        self.assertIn("[CANDIDATE_NAME]", outbound_prompt)
        self.assertIn("[CANDIDATE_EMAIL]", outbound_prompt)
        self.assertIn("[CANDIDATE_PHONE]", outbound_prompt)

        # 3. Assert technical evidence survives
        self.assertIn("Kubernetes microservices in Go and Python", outbound_prompt)
        self.assertIn("PostgreSQL schemas handling 10M daily transactions", outbound_prompt)

        # 4. Assert candidate bullet anchor was also sanitized
        self.assertIn("Contact team at [CANDIDATE_EMAIL] for reference architecture", outbound_prompt)

    def test_fail_safe_boundary_blocks_transmission_on_redaction_failure(self):
        mock_client = MagicMock()
        # Test empty redaction failure guard
        with unittest.mock.patch('gemini_client.redact_candidate_contact_pii', return_value=""):
            with self.assertRaises(PrivacyRedactionError):
                align_candidate_against_targets(
                    client=mock_client,
                    resume_text="Non-empty resume text with candidate details.",
                    jd_targets={"must_haves": [], "bonus_skills": []}
                )
            # Confirm generate_content was NEVER called
            mock_client.models.generate_content.assert_not_called()

    def test_fail_safe_boundary_blocks_transmission_on_redaction_exception(self):
        mock_client = MagicMock()
        with unittest.mock.patch('gemini_client.redact_candidate_contact_pii', side_effect=ValueError("Regex crash")):
            with self.assertRaises(PrivacyRedactionError):
                align_candidate_against_targets(
                    client=mock_client,
                    resume_text="Valid resume text.",
                    jd_targets={"must_haves": [], "bonus_skills": []}
                )
            mock_client.models.generate_content.assert_not_called()

    def test_retries_and_fallbacks_preserve_redacted_prompt(self):
        captured_prompts = []
        mock_client = MagicMock()

        def mock_generate_content(model, contents, config):
            captured_prompts.append((model, contents))
            if len(captured_prompts) == 1:
                raise RuntimeError("503 Service Unavailable")
            mock_resp = MagicMock()
            mock_resp.text = '{"status": "ok"}'
            return mock_resp

        mock_client.models.generate_content.side_effect = mock_generate_content

        test_prompt = "EVALUATE: <CANDIDATE_RESUME_123>[CANDIDATE_NAME] at [CANDIDATE_EMAIL]</CANDIDATE_RESUME_123>"
        schema = {"type": "OBJECT"}

        with unittest.mock.patch.dict(os.environ, {"GEMINI_MAX_RETRIES": "2"}):
            result, model_used = _call_gemini_with_fallback(mock_client, test_prompt, schema)

        self.assertEqual(len(captured_prompts), 2)
        # Verify both attempts received the exact same redacted prompt
        for model, prompt in captured_prompts:
            self.assertEqual(prompt, test_prompt)
            self.assertIn("[CANDIDATE_NAME]", prompt)
            self.assertIn("[CANDIDATE_EMAIL]", prompt)


if __name__ == '__main__':
    unittest.main()
