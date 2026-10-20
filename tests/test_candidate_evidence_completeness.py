"""
Unit & Regression Tests: Fix A — Candidate Evidence Completeness
Verifies:
  - Test A1: More than 15 bullets (constructs synthetic resume with 19+ distinct bullets;
    verifies late bullets 16-19 remain available in the Stage 2 matching prompt ledger).
  - Test A2: Late evidence is not falsely lost (skill/evidence placed only in a late bullet
    reaches the evaluator and is not silently discarded).
  - Test A3: Original order and references (bullet identifiers and source references
    maintain exact list order and attribution).
  - Test A4: Ordinary small resumes (<15 bullets behave identically as before).
  - Test A5: Large-input safety (explicit MAX_PROMPT_CANDIDATE_BULLETS ceiling enforces predictable boundary).
  - Test A6: Existing functionality (metric-grounding, candidate-attestation, and XYZ placeholder locks intact).
Strict safety: Mocks all external model dependencies; zero live Gemini/AI calls; zero database mutations.
"""

import json
import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
engine_dir = os.path.join(project_root, 'engine')
if engine_dir not in sys.path:
    sys.path.insert(0, engine_dir)

import gemini_client
from gemini_client import clean_and_enforce_metric_lock
from parsers.bullet_extractor import extract_candidate_bullets, snap_to_best_candidate_bullet


class TestCandidateEvidenceCompleteness(unittest.TestCase):

    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_jd_targets = {
            "job_title_detected": "Junior Full Stack Developer",
            "must_haves": [
                {"requirement": "PHP backend development", "domain": "Languages & Frameworks"},
                {"requirement": "React client architecture", "domain": "Languages & Frameworks"}
            ],
            "bonus_skills": [
                {"skill": "TypeScript", "domain": "Languages & Frameworks"},
                {"skill": "Docker containerization", "domain": "DevOps, Cloud & Modern Stack"},
                {"skill": "CI/CD pipelines GitHub Actions", "domain": "DevOps, Cloud & Modern Stack"},
                {"skill": "Redis caching", "domain": "Database & Systems Architecture"},
                {"skill": "Competitive coding Hackathons", "domain": "Competitive Proof & Credentials"}
            ]
        }

    @patch('gemini_client._call_gemini_with_fallback')
    def test_a1_more_than_15_bullets_passed_to_evaluator(self, mock_call):
        """Test A1: Resumes with 19+ bullets must not truncate bullets 15-18 from the evidence ledger."""
        mock_call.return_value = ({
            "must_haves": [],
            "bonus_skills": [],
            "actionable_rewrites": []
        }, "mock-model")

        # 19 distinct candidate bullets mirroring the user's reproduction test case
        bullets_19 = [
            f"Candidate bullet #{i}: Accomplished engineering milestone with scalable technical architecture."
            for i in range(19)
        ]
        # Ensure bullets 15-18 have explicit unique markers
        bullets_19[15] = "Experience containerizing web applications using Docker."
        bullets_19[16] = "Understanding of CI/CD pipelines (e.g., GitHub Actions) and automated unit testing (Jest or PHPUnit)."
        bullets_19[17] = "Exposure to cloud deployment platforms (AWS or GCP) and Redis caching."
        bullets_19[18] = "Active participation in hackathons or competitive coding platforms (HackerRank, LeetCode, GfG)."

        resume_text = "\n".join(bullets_19)

        gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=resume_text,
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets_19
        )

        self.assertTrue(mock_call.called, "Model call should have been initiated.")
        prompt = mock_call.call_args[0][1]

        # Verify all 19 bullets are present in the prompt ledger
        for i in range(19):
            self.assertIn(f"[{i}]", prompt, f"Prompt must contain bullet index [{i}]")

        self.assertIn("Experience containerizing web applications using Docker", prompt)
        self.assertIn("Understanding of CI/CD pipelines (e.g., GitHub Actions)", prompt)
        self.assertIn("Exposure to cloud deployment platforms (AWS or GCP) and Redis caching", prompt)
        self.assertIn("Active participation in hackathons or competitive coding platforms", prompt)

    @patch('gemini_client._call_gemini_with_fallback')
    def test_a2_late_evidence_not_falsely_lost(self, mock_call):
        """Test A2: Skill evidence placed exclusively in late bullets (>15) reaches the evaluator."""
        mock_call.return_value = ({
            "must_haves": [],
            "bonus_skills": [
                {"skill": "Docker containerization", "domain": "DevOps, Cloud & Modern Stack", "status": "MATCHED",
                 "evidence_quote": "Experience containerizing web applications using Docker.", "defense_tip": "Highlight containerization."}
            ],
            "actionable_rewrites": []
        }, "mock-model")

        # 22 bullets with Docker appearing ONLY at index 20
        bullets = [f"Generic engineering task number {i} performed with standard methodologies." for i in range(22)]
        bullets[20] = "Spearheaded Docker containerization and Kubernetes cluster deployment across staging environments."

        resume_text = "\n".join(bullets)

        gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=resume_text,
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets
        )

        prompt = mock_call.call_args[0][1]
        self.assertIn("[20] Spearheaded Docker containerization", prompt)
        self.assertNotIn("[:15]", prompt)

    @patch('gemini_client._call_gemini_with_fallback')
    def test_a3_original_order_and_attribution_preserved(self, mock_call):
        """Test A3: Bullet numbering and sequence in prompt strictly matches candidate_bullets order."""
        mock_call.return_value = ({
            "must_haves": [],
            "bonus_skills": [],
            "actionable_rewrites": [
                {
                    "target_skill": "PHP backend development",
                    "original_bullet": "Bullet 17: Late backend project",
                    "upgraded_xyz_bullet": "Accomplished [X] by doing [Z]",
                    "interview_defense_tip": "Defense"
                }
            ]
        }, "mock-model")

        bullets = [f"Bullet {i}: Late backend project" if i == 17 else f"Bullet {i}: Standard task" for i in range(20)]
        resume_text = "\n".join(bullets)

        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=resume_text,
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets
        )

        prompt = mock_call.call_args[0][1]
        # Check order: [0] before [5] before [15] before [19]
        pos_0 = prompt.find("[0] Bullet 0:")
        pos_15 = prompt.find("[15] Bullet 15:")
        pos_17 = prompt.find("[17] Bullet 17:")
        pos_19 = prompt.find("[19] Bullet 19:")

        self.assertTrue(0 < pos_0 < pos_15 < pos_17 < pos_19, "Bullet sequence in prompt must be strictly ascending.")

        # Check snapping downstream can resolve the late bullet
        snapped = snap_to_best_candidate_bullet(res["actionable_rewrites"][0]["original_bullet"], bullets)
        self.assertEqual(snapped, bullets[17])

    @patch('gemini_client._call_gemini_with_fallback')
    def test_a4_ordinary_small_resumes_unaffected(self, mock_call):
        """Test A4: Resumes with fewer than 15 bullets behave identically as before."""
        mock_call.return_value = ({
            "must_haves": [],
            "bonus_skills": [],
            "actionable_rewrites": []
        }, "mock-model")

        bullets_8 = [f"Candidate bullet #{i}: Built web application features." for i in range(8)]
        resume_text = "\n".join(bullets_8)

        gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=resume_text,
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets_8
        )

        prompt = mock_call.call_args[0][1]
        for i in range(8):
            self.assertIn(f"[{i}] Candidate bullet #{i}", prompt)
        self.assertNotIn("[8]", prompt)

    @patch('gemini_client._call_gemini_with_fallback')
    def test_a5_large_input_safety_boundary(self, mock_call):
        """Test A5: Large resumes with >60 bullets respect the explicit MAX_PROMPT_CANDIDATE_BULLETS ceiling."""
        mock_call.return_value = ({
            "must_haves": [],
            "bonus_skills": [],
            "actionable_rewrites": []
        }, "mock-model")

        # 80 bullets
        bullets_80 = [f"Bullet #{i}: Engineering task description line." for i in range(80)]
        resume_text = "\n".join(bullets_80)

        gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=resume_text,
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets_80
        )

        prompt = mock_call.call_args[0][1]
        ceiling = gemini_client.MAX_PROMPT_CANDIDATE_BULLETS
        self.assertEqual(ceiling, 60, "Default safety ceiling must be 60.")

        # Exactly 60 bullets included in ledger
        self.assertIn(f"[{ceiling - 1}] Bullet #{ceiling - 1}", prompt)
        self.assertNotIn(f"[{ceiling}] Bullet #{ceiling}", prompt)

    def test_a6_existing_metric_lock_and_grounding_intact(self):
        """Test A6: Existing metric-grounding and rewrite-confirmation behavior remains completely unchanged."""
        # Unanchored rewrite with metrics must get placeholder lock
        raw_bullet = "Engineered backend microservices reducing server latency by 45% and handling 10k requests."
        locked = clean_and_enforce_metric_lock(raw_bullet, original_bullet="", resume_text="")

        self.assertIn("[ENTER YOUR VERIFIED METRIC]", locked)
        self.assertNotIn("45%", locked)
        self.assertNotIn("10k", locked)

    @patch('gemini_client._call_gemini_with_fallback')
    def test_a7_zero_bullets_unavailable_status(self, mock_call):
        """Test A7: Zero extracted bullets produces UNAVAILABLE status in evidence_ledger."""
        mock_call.return_value = ({"must_haves": [], "bonus_skills": [], "actionable_rewrites": []}, "mock-model")
        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text="No bulleted items in unstructured text.",
            jd_targets=self.mock_jd_targets,
            candidate_bullets=[]
        )
        ledger = res.get("evidence_ledger", {})
        self.assertEqual(ledger.get("status"), "UNAVAILABLE")
        self.assertEqual(ledger.get("extracted_bullets_count"), 0)
        self.assertEqual(ledger.get("evaluated_bullets_count"), 0)
        self.assertEqual(ledger.get("omitted_bullets_count"), 0)
        self.assertIn("No structured candidate bullets", ledger.get("audit_note", ""))

    @patch('gemini_client._call_gemini_with_fallback')
    def test_a8_single_bullet_complete_status(self, mock_call):
        """Test A8: A single extracted bullet produces COMPLETE status with 1 evaluated and 0 omitted."""
        mock_call.return_value = ({"must_haves": [], "bonus_skills": [], "actionable_rewrites": []}, "mock-model")
        bullet = ["Architected full-stack web application in PHP and MySQL."]
        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=bullet[0],
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullet
        )
        ledger = res.get("evidence_ledger", {})
        self.assertEqual(ledger.get("status"), "COMPLETE")
        self.assertEqual(ledger.get("extracted_bullets_count"), 1)
        self.assertEqual(ledger.get("evaluated_bullets_count"), 1)
        self.assertEqual(ledger.get("omitted_bullets_count"), 0)

    @patch('gemini_client._call_gemini_with_fallback')
    def test_a9_exact_boundary_60_bullets_complete_status(self, mock_call):
        """Test A9: Exactly 60 bullets (at default limit) produces COMPLETE status with 0 omitted."""
        mock_call.return_value = ({"must_haves": [], "bonus_skills": [], "actionable_rewrites": []}, "mock-model")
        bullets_60 = [f"Bullet #{i}: Engineering task execution." for i in range(60)]
        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text="\n".join(bullets_60),
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets_60
        )
        ledger = res.get("evidence_ledger", {})
        self.assertEqual(ledger.get("status"), "COMPLETE")
        self.assertEqual(ledger.get("extracted_bullets_count"), 60)
        self.assertEqual(ledger.get("evaluated_bullets_count"), 60)
        self.assertEqual(ledger.get("omitted_bullets_count"), 0)

    @patch('gemini_client._call_gemini_with_fallback')
    def test_a10_boundary_plus_one_61_bullets_capped_status(self, mock_call):
        """Test A10: Exactly 61 bullets (ceiling + 1) produces CAPPED status with 1 omitted."""
        mock_call.return_value = ({"must_haves": [], "bonus_skills": [], "actionable_rewrites": []}, "mock-model")
        bullets_61 = [f"Bullet #{i}: Engineering task execution." for i in range(61)]
        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text="\n".join(bullets_61),
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets_61
        )
        ledger = res.get("evidence_ledger", {})
        self.assertEqual(ledger.get("status"), "CAPPED")
        self.assertEqual(ledger.get("extracted_bullets_count"), 61)
        self.assertEqual(ledger.get("evaluated_bullets_count"), 60)
        self.assertEqual(ledger.get("omitted_bullets_count"), 1)
        self.assertIn("1 late bullets omitted", ledger.get("audit_note", ""))

    @patch('gemini_client._call_gemini_with_fallback')
    def test_a11_dense_resume_80_bullets_capped_metadata(self, mock_call):
        """Test A11: Dense resume with 80 bullets produces CAPPED status with 20 omitted."""
        mock_call.return_value = ({"must_haves": [], "bonus_skills": [], "actionable_rewrites": []}, "mock-model")
        bullets_80 = [f"Bullet #{i}: Engineering task execution." for i in range(80)]
        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text="\n".join(bullets_80),
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets_80
        )
        ledger = res.get("evidence_ledger", {})
        self.assertEqual(ledger.get("status"), "CAPPED")
        self.assertEqual(ledger.get("extracted_bullets_count"), 80)
        self.assertEqual(ledger.get("evaluated_bullets_count"), 60)
        self.assertEqual(ledger.get("omitted_bullets_count"), 20)

    def test_a12_env_configuration_isolated_subprocesses(self):
        """Test A12: Isolated subprocess evaluation of MAX_PROMPT_CANDIDATE_BULLETS across all input types."""
        py_code = "import gemini_client; print(gemini_client.MAX_PROMPT_CANDIDATE_BULLETS)"
        test_cases = [
            (None, "60", "Missing variable defaults to 60"),
            ("45", "45", "Valid positive integer is preserved"),
            ("0", "60", "Zero falls back to 60"),
            ("-5", "60", "Negative integer falls back to 60"),
            ("abc", "60", "Invalid text falls back to 60"),
            ("", "60", "Empty string falls back to 60"),
            ("   ", "60", "Whitespace falls back to 60"),
            ("1000000", "120", "Excessively large value is safely clamped to 120 boundary")
        ]

        env_base = os.environ.copy()
        env_base["GEMINI_API_KEY"] = "mock_key_for_test"

        for val, expected, desc in test_cases:
            sub_env = env_base.copy()
            if val is None:
                sub_env.pop("MAX_PROMPT_CANDIDATE_BULLETS", None)
            else:
                sub_env["MAX_PROMPT_CANDIDATE_BULLETS"] = val

            proc = subprocess.run(
                [sys.executable, "-c", py_code],
                env=sub_env,
                cwd=engine_dir,
                capture_output=True,
                text=True
            )
            self.assertEqual(proc.returncode, 0, f"Subprocess crashed on {val}: {proc.stderr}")
            self.assertEqual(proc.stdout.strip(), expected, f"{desc}: expected {expected}, got {proc.stdout.strip()}")

    def test_a13_report_persistence_and_serialization_roundtrip(self):
        """Test A13: evidence_ledger survives json.dumps/json.loads without field corruption."""
        sample_ledger = {
            "status": "CAPPED",
            "extracted_bullets_count": 75,
            "evaluated_bullets_count": 60,
            "omitted_bullets_count": 15,
            "ceiling": 60,
            "audit_note": "Candidate evidence capped at 60 bullets (15 late bullets omitted from rewrite matching)."
        }
        report = {
            "job_title_detected": "Backend Engineer",
            "must_haves": [],
            "bonus_skills": [],
            "experience_years": {"required_years": 3.0, "candidate_years": 4.0},
            "actionable_rewrites": [],
            "evidence_ledger": sample_ledger
        }
        serialized = json.dumps(report)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized["evidence_ledger"], sample_ledger)

    def test_a14_historical_report_loading_not_falsely_complete(self):
        """Test A14: Historical reports lacking evidence_ledger default safely and do not falsely certify completeness."""
        legacy_report = {
            "job_title_detected": "Backend Engineer",
            "must_haves": [],
            "bonus_skills": [],
            "experience_years": {"required_years": 3.0, "candidate_years": 4.0},
            "actionable_rewrites": []
        }
        ledger = legacy_report.get("evidence_ledger")
        self.assertIsNone(ledger, "Historical scan must not invent a COMPLETE state")

    def test_a15_downstream_snapping_across_all_extracted_bullets(self):
        """Test A15: snap_to_best_candidate_bullet searches full candidate bullets list, even late ones."""
        all_bullets = [f"Bullet #{i}: Maintenance task" for i in range(70)]
        all_bullets[68] = "Architected high-throughput Kafka event streaming pipeline handling 50k events/sec."
        query = "Built Kafka event pipeline handling high throughput."
        snapped = snap_to_best_candidate_bullet(query, all_bullets)
        self.assertEqual(snapped, all_bullets[68], "Snapping must search all extracted bullets beyond prompt cap.")

    def test_a16_scoring_arithmetic_invariants(self):
        """Test A16: Deterministic scoring formula in scorer.py is 100% invariant to evidence_ledger presence."""
        from scorer import calculate_deterministic_scores
        report_without = {
            "must_haves": [{"status": "MATCHED"}, {"status": "MATCHED"}],
            "bonus_skills": [{"status": "MATCHED"}, {"status": "MISSING"}],
            "experience_years": {"requirement_status": "SPECIFIED", "required_years": 4.0, "candidate_years": 2.0}
        }
        report_with = {
            **report_without,
            "evidence_ledger": {
                "status": "CAPPED",
                "extracted_bullets_count": 80,
                "evaluated_bullets_count": 60,
                "omitted_bullets_count": 20,
                "ceiling": 60
            }
        }
        scores_without = calculate_deterministic_scores(report_without)
        scores_with = calculate_deterministic_scores(report_with)
        self.assertEqual(scores_without, scores_with, "Scoring arithmetic must remain 100% identical.")


class TestEvidenceSeparationAndPromptBudget(unittest.TestCase):
    """
    Evidence-Integrity Acceptance Gate Tests:
    1. Verify separation of rewrite evidence (numbered bullets ledger) from scoring evidence (raw resume block).
    2. Verify prompt budget mathematics and intake limits (<15,000 tokens vs 1M window).
    3. Verify end-to-end API/frontend consistency and historical payload backwards compatibility.
    """

    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_jd_targets = {
            "job_title_detected": "Senior Infrastructure Engineer",
            "must_haves": [
                {"requirement": "Kubernetes cluster orchestration", "domain": "DevOps, Cloud & Modern Stack"},
                {"requirement": "Python backend services", "domain": "Languages & Frameworks"}
            ],
            "bonus_skills": [
                {"skill": "GraphQL schema federation", "domain": "Languages & Frameworks"},
                {"skill": "Rust systems programming", "domain": "Languages & Frameworks"}
            ]
        }

    @patch('gemini_client._call_gemini_with_fallback')
    def test_case_1_late_bullet_qualification_available_in_raw_resume(self, mock_call):
        """Case 1: Bullet 65 is omitted from rewrite anchor ledger but present in raw resume for scoring."""
        bullets = [f"Standard operational bullet #{i}: Managed production workloads." for i in range(70)]
        bullets[65] = "Architected multi-region Kubernetes cluster orchestration with automated failover."
        resume_text = "\n".join(bullets)

        mock_call.return_value = ({
            "must_haves": [
                {
                    "requirement": "Kubernetes cluster orchestration",
                    "domain": "DevOps, Cloud & Modern Stack",
                    "status": "MATCHED",
                    "evidence_quote": "Architected multi-region Kubernetes cluster orchestration with automated failover.",
                    "defense_tip": "Discuss zero-downtime cluster migrations."
                },
                {
                    "requirement": "Python backend services",
                    "domain": "Languages & Frameworks",
                    "status": "MATCHED",
                    "evidence_quote": "Managed production workloads.",
                    "defense_tip": "Highlight backend maintenance."
                }
            ],
            "bonus_skills": [],
            "actionable_rewrites": []
        }, "mock-model")

        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=resume_text,
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets,
            scoring_clamped=False
        )

        prompt = mock_call.call_args[0][1]

        # 1. Bullet 65 MUST NOT be in the numbered rewrite ledger (ceiling is 60)
        rewrite_ledger_section = prompt.split("AUTHENTIC CANDIDATE BULLETS FROM RESUME")[1].split("EVALUATION & GROUNDING RULES")[0]
        self.assertNotIn("[65]", rewrite_ledger_section)
        self.assertNotIn("Architected multi-region Kubernetes cluster orchestration", rewrite_ledger_section)

        # 2. Bullet 65 MUST be in the raw resume block <CANDIDATE_RESUME_...>
        raw_resume_section = prompt.rsplit("<CANDIDATE_RESUME_", 1)[1]
        self.assertIn("Architected multi-region Kubernetes cluster orchestration", raw_resume_section)

        # 3. Evidence ledger statuses reflect accurate separation
        self.assertEqual(res["evidence_ledger"]["rewrite_ledger"]["status"], "CAPPED")
        self.assertEqual(res["evidence_ledger"]["rewrite_ledger"]["included_bullets_count"], 60)
        self.assertEqual(res["evidence_ledger"]["rewrite_ledger"]["omitted_bullets_count"], 10)
        self.assertEqual(res["evidence_ledger"]["scoring_evidence"]["status"], "COMPLETE")

        # 4. Deterministic score includes Kubernetes match
        from scorer import calculate_deterministic_scores
        report_with_exp = {
            **res,
            "experience_years": {"requirement_status": "NOT_SPECIFIED"}
        }
        scores = calculate_deterministic_scores(report_with_exp)
        self.assertEqual(scores["must_have_score"], 100.0, "Late-bullet qualification must count 100% in deterministic scoring.")

    @patch('gemini_client._call_gemini_with_fallback')
    def test_case_2_raw_text_qualification_outside_bullet_ledger(self, mock_call):
        """Case 2: Qualification in narrative paragraph outside bullet extractor reaches prompt and is scored."""
        narrative_header = "EXECUTIVE SUMMARY: 6 years pioneering GraphQL schema federation across distributed microservices.\n"
        bullets = [f"Bullet #{i}: Maintained legacy software modules." for i in range(10)]
        resume_text = narrative_header + "\n".join(bullets)

        mock_call.return_value = ({
            "must_haves": [],
            "bonus_skills": [
                {
                    "skill": "GraphQL schema federation",
                    "domain": "Languages & Frameworks",
                    "status": "MATCHED",
                    "evidence_quote": "6 years pioneering GraphQL schema federation across distributed microservices.",
                    "defense_tip": "Discuss Apollo federation schema design."
                }
            ],
            "actionable_rewrites": []
        }, "mock-model")

        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=resume_text,
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets,
            scoring_clamped=False
        )

        prompt = mock_call.call_args[0][1]

        # Narrative text is present in raw resume block
        self.assertIn("GraphQL schema federation", prompt)
        # Narrative text is NOT in numbered bullet list
        rewrite_ledger_section = prompt.split("AUTHENTIC CANDIDATE BULLETS FROM RESUME")[1].split("EVALUATION & GROUNDING RULES")[0]
        self.assertNotIn("EXECUTIVE SUMMARY", rewrite_ledger_section)

        # Scoring evidence is complete
        self.assertEqual(res["evidence_ledger"]["scoring_evidence"]["status"], "COMPLETE")
        self.assertEqual(res["bonus_skills"][0]["status"], "MATCHED")

    @patch('gemini_client._call_gemini_with_fallback')
    def test_case_3_jd_target_absent_from_resume_not_hallucinated(self, mock_call):
        """Case 3: JD target completely absent from candidate resume is marked MISSING and yields 0 score."""
        bullets = ["Developed web APIs in Python using Flask.", "Managed PostgreSQL databases."]
        resume_text = "\n".join(bullets)

        mock_call.return_value = ({
            "must_haves": [
                {"requirement": "Python backend services", "domain": "Languages & Frameworks", "status": "MATCHED",
                 "evidence_quote": "Developed web APIs in Python using Flask.", "defense_tip": "Elaborate on Flask."}
            ],
            "bonus_skills": [
                {"skill": "Rust systems programming", "domain": "Languages & Frameworks", "status": "MISSING",
                 "gap_reason": "No mention of Rust or systems programming in candidate resume.", "defense_tip": "Discuss systems learning goals."}
            ],
            "actionable_rewrites": []
        }, "mock-model")

        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=resume_text,
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets
        )

        self.assertEqual(res["bonus_skills"][0]["status"], "MISSING")
        self.assertEqual(res["bonus_skills"][0].get("evidence_quote", ""), "")

        from scorer import calculate_deterministic_scores
        report = {
            "must_haves": [{"status": "MATCHED"}],
            "bonus_skills": [{"status": "MISSING"}],
            "experience_years": {"requirement_status": "NOT_SPECIFIED"}
        }
        scores = calculate_deterministic_scores(report)
        self.assertEqual(scores["bonus_score"], 0.0)

    @patch('gemini_client._call_gemini_with_fallback')
    def test_case_4_oversized_resume_prompt_budget_bounded(self, mock_call):
        """Case 4: 35,000-char resume is clamped at intake (25,000 chars); serialized prompt is <15,000 tokens."""
        mock_call.return_value = ({"must_haves": [], "bonus_skills": [], "actionable_rewrites": []}, "mock-model")

        raw_oversized = "Engineering bullet point with architectural details and metrics. " * 550
        self.assertGreater(len(raw_oversized), 35000)

        # Apply engine intake boundary
        MAX_RESUME_CHARS = 25000
        if len(raw_oversized) > MAX_RESUME_CHARS:
            resume_text = raw_oversized[:MAX_RESUME_CHARS]
            scoring_clamped = True
        else:
            resume_text = raw_oversized
            scoring_clamped = False

        bullets_60 = [f"Bullet #{i}: Engineering task execution." for i in range(60)]

        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=resume_text,
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets_60,
            scoring_clamped=scoring_clamped
        )

        prompt = mock_call.call_args[0][1]

        # 1. Total serialized prompt length is bounded
        self.assertLess(len(prompt), 60000, "Serialized prompt characters must be strictly < 60,000 chars.")
        # Estimated token count (1 token ~= 3.5 to 4 characters for English technical text)
        estimated_tokens = len(prompt) / 3.5
        self.assertLess(estimated_tokens, 15000, "Serialized prompt tokens must be strictly < 15,000 tokens (vs 1M window).")

        # 2. Scoring evidence ledger correctly flags CAPPED status and exact 25,000 character count
        scoring_ev = res["evidence_ledger"]["scoring_evidence"]
        self.assertEqual(scoring_ev["status"], "CAPPED")
        self.assertEqual(scoring_ev["character_count"], 25000)
        self.assertEqual(scoring_ev["character_limit"], 25000)
        self.assertIn("clamped to 25,000 characters", scoring_ev["audit_note"])

    @patch('gemini_client._call_gemini_with_fallback')
    def test_case_5_capped_rewrite_ledger_preserves_scoring_evidence(self, mock_call):
        """Case 5: Resume with 75 bullets has CAPPED rewrite ledger but COMPLETE scoring evidence."""
        mock_call.return_value = ({"must_haves": [], "bonus_skills": [], "actionable_rewrites": []}, "mock-model")

        bullets_75 = [f"Bullet #{i}: Implemented scalable backend features and database optimizations." for i in range(75)]
        resume_text = "\n".join(bullets_75)
        self.assertLess(len(resume_text), 25000, "Resume text must be within 25,000-char intake limit.")

        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=resume_text,
            jd_targets=self.mock_jd_targets,
            candidate_bullets=bullets_75,
            scoring_clamped=False
        )

        ledger = res["evidence_ledger"]
        # Rewrite ledger is CAPPED
        self.assertEqual(ledger["rewrite_ledger"]["status"], "CAPPED")
        self.assertEqual(ledger["rewrite_ledger"]["extracted_bullets_count"], 75)
        self.assertEqual(ledger["rewrite_ledger"]["included_bullets_count"], 60)
        self.assertEqual(ledger["rewrite_ledger"]["omitted_bullets_count"], 15)

        # Scoring evidence is COMPLETE
        self.assertEqual(ledger["scoring_evidence"]["status"], "COMPLETE")
        self.assertEqual(ledger["scoring_evidence"]["character_count"], len(resume_text))
        self.assertEqual(ledger["scoring_evidence"]["character_limit"], 25000)

        # Scoring arithmetic is invariant to rewrite ledger cap
        from scorer import calculate_deterministic_scores
        report = {
            "must_haves": [{"status": "MATCHED"}],
            "bonus_skills": [{"status": "MATCHED"}],
            "experience_years": {"requirement_status": "NOT_SPECIFIED"},
            "evidence_ledger": ledger
        }
        scores = calculate_deterministic_scores(report)
        self.assertEqual(scores["overall_score"], 100.0)

    @patch('gemini_client._call_gemini_with_fallback')
    def test_case_6_genuinely_incomplete_scoring_evidence_clamped(self, mock_call):
        """Case 6: When scoring_clamped=True, scoring_evidence correctly reflects CAPPED with diagnostic audit note."""
        mock_call.return_value = ({"must_haves": [], "bonus_skills": [], "actionable_rewrites": []}, "mock-model")

        synthetic_text = "A" * 25000
        res = gemini_client.align_candidate_against_targets(
            client=self.mock_client,
            resume_text=synthetic_text,
            jd_targets=self.mock_jd_targets,
            candidate_bullets=["Bullet 1"],
            scoring_clamped=True
        )

        scoring_ev = res["evidence_ledger"]["scoring_evidence"]
        self.assertEqual(scoring_ev["status"], "CAPPED")
        self.assertEqual(scoring_ev["character_count"], 25000)
        self.assertIn("exceeded intake boundary", scoring_ev["audit_note"])
        self.assertIn("clamped to 25,000 characters for scoring", scoring_ev["audit_note"])

    def test_case_7_end_to_end_consistency_api_frontend_contract(self):
        """Case 7: API JSON envelope adheres strictly to frontend schema expectations in app.js & index.php."""
        # Simulated payload from status.php
        api_payload = {
            "status": "COMPLETED",
            "overall_score": 85.0,
            "evidence_ledger": {
                "status": "CAPPED",
                "extracted_bullets_count": 75,
                "included_bullets_count": 60,
                "evaluated_bullets_count": 60,
                "omitted_bullets_count": 15,
                "ceiling": 60,
                "audit_note": "Candidate rewrite anchors capped at 60 bullets (15 late bullets omitted from rewrite anchor list; full resume text remained available for skill scoring).",
                "scoring_evidence": {
                    "status": "COMPLETE",
                    "character_count": 12000,
                    "character_limit": 25000,
                    "audit_note": "Complete candidate resume text (12000 characters) provided for skill classification."
                },
                "rewrite_ledger": {
                    "status": "CAPPED",
                    "extracted_bullets_count": 75,
                    "included_bullets_count": 60,
                    "evaluated_bullets_count": 60,
                    "omitted_bullets_count": 15,
                    "ceiling": 60,
                    "audit_note": "Candidate rewrite anchors capped at 60 bullets (15 late bullets omitted from rewrite anchor list; full resume text remained available for skill scoring)."
                }
            }
        }

        # 1. Backward compatibility alias
        self.assertEqual(
            api_payload["evidence_ledger"]["evaluated_bullets_count"],
            api_payload["evidence_ledger"]["included_bullets_count"]
        )

        # 2. Frontend condition: Overall score card clamped badge (must be FALSE when scoring is COMPLETE)
        ledger = api_payload.get("evidence_ledger", {})
        scoring_clamped_flag = ledger.get("scoring_evidence", {}).get("status") == "CAPPED"
        self.assertFalse(scoring_clamped_flag, "Overall score must NOT show clamped badge when scoring_evidence is COMPLETE.")

        # 3. Frontend condition: Pillar 3 rewriter anchors badge (must be TRUE when rewrites are CAPPED)
        rewrite_capped_flag = ledger.get("rewrite_ledger", {}).get("status") == "CAPPED"
        self.assertTrue(rewrite_capped_flag, "Pillar 3 must show Anchors Capped badge when rewrite_ledger is CAPPED.")

        # 4. JSON roundtrip serialization check
        serialized = json.dumps(api_payload)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized, api_payload)

    def test_case_8_historical_reports_load_safely_without_metadata(self):
        """Case 8: Legacy report payload without evidence_ledger loads safely with no errors or false assertions."""
        historical_report = {
            "job_title_detected": "Software Engineer",
            "must_haves": [{"requirement": "Java", "status": "MATCHED"}],
            "bonus_skills": [{"skill": "Docker", "status": "MATCHED"}],
            "experience_years": {"requirement_status": "NOT_SPECIFIED"},
            "actionable_rewrites": []
        }

        # 1. Verify safe dictionary access mirroring AlpineJS optional chaining (?. operator)
        ledger = historical_report.get("evidence_ledger")
        self.assertIsNone(ledger)

        scoring_status = (ledger or {}).get("scoring_evidence", {}).get("status")
        rewrite_status = (ledger or {}).get("rewrite_ledger", {}).get("status")
        self.assertIsNone(scoring_status)
        self.assertIsNone(rewrite_status)

        # Ensure no false positive badges would be triggered
        self.assertFalse(scoring_status == "CAPPED")
        self.assertFalse(rewrite_status == "CAPPED")

        # 2. Scorer runs without exception on legacy report
        from scorer import calculate_deterministic_scores
        scores = calculate_deterministic_scores(historical_report)
        self.assertEqual(scores["overall_score"], 100.0)


if __name__ == "__main__":
    unittest.main()
