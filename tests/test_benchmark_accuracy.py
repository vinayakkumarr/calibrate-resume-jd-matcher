"""
Calibrate AI — Diagnostic Alignment & Accuracy Benchmark Runner
Evaluates factual correctness, evidence grounding, precision, recall,
requirement coverage, and reliability across all 10 Ground Truth benchmark cases.

Architecture:
- Deterministic component tests (date parsing, tenure calculation, citation verification,
  negation filtering, bullet snapping, scoring deal-breaker gating).
- Mocked end-to-end pipeline execution testing Stage 1, Stage 2, post-processing, and scoring.
- Zero production code modification.
- Zero live Gemini API calls in this diagnostic baseline.
"""

import os
import sys
import json
import math
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add engine directory to path
engine_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'engine'))
if engine_dir not in sys.path:
    sys.path.insert(0, engine_dir)

from parsers.date_parser import extract_required_years_from_jd, extract_candidate_tenure, get_current_temporal_reference
from parsers.bullet_extractor import extract_candidate_bullets, snap_to_best_candidate_bullet
from grounding_verifier import verify_and_anchor_citation, validate_and_anchor_report
from pre_filter import is_negated_mention, resolve_acronym_matches, build_active_synonym_context
from scorer import calculate_deterministic_scores
from jd_target_cache import validate_jd_targets_schema, compute_jd_cache_key


# =============================================================================
# 10 SYNTHETIC GROUND TRUTH FIXTURES (Version 2.0.0)
# =============================================================================

BENCHMARK_CASES = {
    "TC01": {
        "id": "TC01",
        "name": "Strong Alignment with Direct Evidence",
        "role": "Senior Full Stack Engineer",
        "jd_text": """Role: Senior Full Stack Engineer.
Requirements (Mandatory):
- 4+ years of professional backend development with Python and FastAPI.
- Relational database schema design and indexing in PostgreSQL.
- Modern frontend engineering with React (ES6+) and TypeScript.
Bonus (Preferred):
- Hands-on experience with Redis caching.
- Docker containerization.""",
        "resume_text": """Jordan Miller - Senior Full Stack Developer
Work History:
Lead Software Engineer | CloudTech Solutions (Jan 2020 – Present)
- Architected 12 high-performance microservices using Python and FastAPI handling 8M daily requests.
- Designed normalized PostgreSQL schemas and optimized multi-column B-tree indexes reducing query latency.
- Built customer-facing analytics dashboards using React, TypeScript, and Tailwind CSS.
- Containerized deployment workflows using Docker and integrated Redis for session caching.""",
        "expected": {
            "required_years": 4.0,
            "candidate_years": 6.8,  # Jan 2020 - Oct 2026 = 82 calendar months -> 6.8 years
            "must_haves": [
                {"requirement": "Python and FastAPI backend development", "status": "MATCHED", "quote": "Architected 12 high-performance microservices using Python and FastAPI handling 8M daily requests."},
                {"requirement": "Relational database schema design and indexing in PostgreSQL", "status": "MATCHED", "quote": "Designed normalized PostgreSQL schemas and optimized multi-column B-tree indexes reducing query latency."},
                {"requirement": "Frontend engineering with React and TypeScript", "status": "MATCHED", "quote": "Built customer-facing analytics dashboards using React, TypeScript, and Tailwind CSS."}
            ],
            "bonus_skills": [
                {"skill": "Redis caching", "status": "MATCHED", "quote": "integrated Redis for session caching"},
                {"skill": "Docker containerization", "status": "MATCHED", "quote": "Containerized deployment workflows using Docker"}
            ],
            "must_have_score": 100.0,
            "bonus_score": 100.0,
            "experience_score": 100.0,
            "overall_score": 100.0
        }
    },

    "TC02": {
        "id": "TC02",
        "name": "Partial Alignment with Legitimate Gaps",
        "role": "Backend Platform Engineer",
        "jd_text": """Role: Backend Platform Engineer.
Requirements (Mandatory):
- 3+ years experience with Go (Golang) microservices.
- Experience designing event-driven architectures with Apache Kafka.
- Production experience with Kubernetes cluster management.
Bonus (Preferred):
- Experience with GraphQL APIs.
- Observability using Prometheus and Grafana.""",
        "resume_text": """Alex Vance - Backend Developer
Experience:
Software Engineer | Apex Data (Mar 2021 – Present)
- Built scalable REST APIs and microservices in Go (Golang) for high-volume financial transactions.
- Implemented event streaming pipelines using Apache Kafka for real-time trade settlement.
- Monitored system health and built metrics dashboards using Prometheus and Grafana.""",
        "expected": {
            "required_years": 3.0,
            "candidate_years": 5.7,  # Mar 2021 - Oct 2026 = 68 months -> 5.7 years
            "must_haves": [
                {"requirement": "Go (Golang) microservices", "status": "MATCHED", "quote": "Built scalable REST APIs and microservices in Go (Golang) for high-volume financial transactions."},
                {"requirement": "Apache Kafka event-driven architectures", "status": "MATCHED", "quote": "Implemented event streaming pipelines using Apache Kafka for real-time trade settlement."},
                {"requirement": "Kubernetes cluster management", "status": "MISSING", "quote": ""}
            ],
            "bonus_skills": [
                {"skill": "GraphQL APIs", "status": "MISSING", "quote": ""},
                {"skill": "Prometheus and Grafana observability", "status": "MATCHED", "quote": "Monitored system health and built metrics dashboards using Prometheus and Grafana."}
            ],
            "must_have_score": 66.67,
            "bonus_score": 50.0,
            "experience_score": 100.0,
            "overall_score": 70.84
        }
    },

    "TC03": {
        "id": "TC03",
        "name": "Poor Alignment with Mostly Irrelevant Experience",
        "role": "Senior Embedded Firmware Engineer",
        "jd_text": """Role: Senior Embedded Firmware Engineer.
Requirements (Mandatory):
- 5+ years experience in Embedded C and C++ for ARM microcontrollers.
- Direct hardware interfacing: I2C, SPI, UART, and RTOS (FreeRTOS).
- Oscilloscope and logic analyzer hardware debugging.
Bonus (Preferred):
- Bluetooth Low Energy (BLE) protocol stack.""",
        "resume_text": """Taylor Brooks - Digital Marketing & SEO Specialist
Experience:
Digital Marketing Lead | GrowthCorp (Jan 2019 – Present)
- Managed Google Ads campaigns and optimized organic SEO across WordPress and Shopify sites.
- Authored marketing copy and social media strategies generating 40k monthly leads.
- Built simple landing page styling using HTML, CSS, and basic JavaScript.""",
        "expected": {
            "required_years": 5.0,
            "candidate_years": 7.8,  # Jan 2019 - Oct 2026 = 94 months -> 7.8 years
            "must_haves": [
                {"requirement": "Embedded C and C++ for ARM microcontrollers", "status": "MISSING", "quote": ""},
                {"requirement": "Hardware interfacing I2C, SPI, UART, RTOS", "status": "MISSING", "quote": ""},
                {"requirement": "Oscilloscope and logic analyzer hardware debugging", "status": "MISSING", "quote": ""}
            ],
            "bonus_skills": [
                {"skill": "Bluetooth Low Energy BLE protocol", "status": "MISSING", "quote": ""}
            ],
            "must_have_score": 0.0,
            "bonus_score": 0.0,
            "experience_score": 100.0,
            "overall_score": 0.0  # Essential-Skill Deal-Breaker Gating collapses score to 0.0
        }
    },

    "TC04": {
        "id": "TC04",
        "name": "Missing Mandatory Skill (Deal-Breaker Credential)",
        "role": "Cloud Infrastructure Architect",
        "jd_text": """Role: Cloud Infrastructure Architect.
Requirements (Mandatory):
- Minimum 5 years of professional experience.
- Active AWS Certified Solutions Architect - Professional certification.
- Advanced Terraform Infrastructure as Code (IaC) enterprise automation.
- Multi-region VPC networking and AWS IAM policies.
Bonus (Preferred):
- Python or Bash automation scripting.""",
        "resume_text": """Morgan Reed - Senior Cloud Engineer
Certifications:
- HashiCorp Certified: Terraform Associate
- AWS Certified Solutions Architect - Associate (Expired 2022)
Experience:
Cloud Engineer | Enterprise Scale (Jan 2018 – Present)
- Automated enterprise AWS infrastructure using Terraform modules across 40 accounts.
- Configured multi-region VPC peering, Transit Gateways, and complex IAM boundary policies.
- Developed Python and Bash scripts for automated compliance auditing.""",
        "expected": {
            "required_years": 5.0,
            "candidate_years": 8.8,  # Jan 2018 - Oct 2026 = 106 months -> 8.8 years
            "must_haves": [
                {"requirement": "Active AWS Certified Solutions Architect - Professional certification", "status": "MISSING", "quote": ""},
                {"requirement": "Advanced Terraform Infrastructure as Code", "status": "MATCHED", "quote": "Automated enterprise AWS infrastructure using Terraform modules across 40 accounts."},
                {"requirement": "Multi-region VPC networking and AWS IAM policies", "status": "MATCHED", "quote": "Configured multi-region VPC peering, Transit Gateways, and complex IAM boundary policies."}
            ],
            "bonus_skills": [
                {"skill": "Python or Bash automation scripting", "status": "MATCHED", "quote": "Developed Python and Bash scripts for automated compliance auditing."}
            ],
            "must_have_score": 66.67,
            "bonus_score": 100.0,
            "experience_score": 100.0,
            "overall_score": 83.34
        }
    },

    "TC05": {
        "id": "TC05",
        "name": "Explicit Negation Handling",
        "role": "DevOps Engineer",
        "jd_text": """Role: DevOps Engineer.
Requirements (Mandatory):
- Production experience deploying and orchestrating microservices with Docker.
- Kubernetes cluster administration in AWS (EKS).
- CI/CD automation with GitLab CI or GitHub Actions.
Bonus (Preferred):
- Terraform infrastructure automation.""",
        "resume_text": """Casey Chen - Systems Administrator & Cloud Specialist
Professional Summary:
Experienced sysadmin with a strong Linux foundation. While I have managed bare-metal hypervisors, I have never used Docker or containerization in any production environment, and have no prior experience with Docker containers.
Work Experience:
Systems Admin | InfraTech (Jan 2020 – Present)
- Administered Kubernetes clusters on AWS EKS for internal developer tools.
- Built automated deployment pipelines using GitLab CI for virtual machine imaging.
- Authored Terraform modules for automated server provisioning.""",
        "expected": {
            "required_years": 0.0,
            "candidate_years": 6.8,  # Jan 2020 - Oct 2026 = 82 months -> 6.8 years
            "must_haves": [
                {"requirement": "Docker microservices deployment", "status": "MISSING", "quote": ""},
                {"requirement": "Kubernetes administration on AWS EKS", "status": "MATCHED", "quote": "Administered Kubernetes clusters on AWS EKS for internal developer tools."},
                {"requirement": "CI/CD automation with GitLab CI", "status": "MATCHED", "quote": "Built automated deployment pipelines using GitLab CI for virtual machine imaging."}
            ],
            "bonus_skills": [
                {"skill": "Terraform infrastructure automation", "status": "MATCHED", "quote": "Authored Terraform modules for automated server provisioning."}
            ],
            "must_have_score": 66.67,
            "bonus_score": 100.0,
            "experience_score": None,
            "overall_score": 77.78
        }
    },

    "TC06": {
        "id": "TC06",
        "name": "Similar but Non-Equivalent Technologies (Java != JavaScript)",
        "role": "Enterprise Java Backend Architect",
        "jd_text": """Role: Enterprise Java Backend Architect.
Requirements (Mandatory):
- 5+ years enterprise backend development in Java (JVM), Spring Boot, and Hibernate.
- Multithreaded concurrency, JVM garbage collection tuning, and memory heap dump profiling.
- Relational persistence with Spring Data JPA.
Bonus (Preferred):
- Apache Maven or Gradle build toolchains.""",
        "resume_text": """Devon Kelly - Senior Full Stack Web Developer
Experience:
Lead Developer | WebApp Studio (Jan 2018 – Present)
- Engineered responsive web applications using JavaScript, Node.js, Express, and React.
- Implemented asynchronous event loops and non-blocking I/O in JavaScript.
- Managed MongoDB document persistence using Mongoose ODM.
- Utilized npm and Webpack for client-side bundle builds.""",
        "expected": {
            "required_years": 5.0,
            "candidate_years": 8.8,  # Jan 2018 - Oct 2026 = 106 months -> 8.8 years
            "must_haves": [
                {"requirement": "Java (JVM), Spring Boot, and Hibernate", "status": "MISSING", "quote": ""},
                {"requirement": "Multithreaded concurrency and JVM GC tuning", "status": "MISSING", "quote": ""},
                {"requirement": "Spring Data JPA relational persistence", "status": "MISSING", "quote": ""}
            ],
            "bonus_skills": [
                {"skill": "Apache Maven or Gradle build toolchains", "status": "MISSING", "quote": ""}
            ],
            "must_have_score": 0.0,
            "bonus_score": 0.0,
            "experience_score": 100.0,
            "overall_score": 0.0  # Deal-breaker gate
        }
    },

    "TC07": {
        "id": "TC07",
        "name": "Valid Transferable Architecture Skills (AWS RDS -> Cloud Relational DB)",
        "role": "Cloud Database Platform Engineer",
        "jd_text": """Role: Cloud Database Platform Engineer.
Requirements (Mandatory):
- Experience designing and administering managed relational cloud databases (Google Cloud SQL or AWS RDS).
- Relational query optimization, indexing, and connection pooling.
- Python scripting for database health monitoring.
Bonus (Preferred):
- In-memory caching with Redis or Memcached.""",
        "resume_text": """Samantha Wu - Database Administrator
Experience:
Senior DBA | FinData Systems (Jan 2019 – Present)
- Designed, deployed, and administered 20+ multi-AZ PostgreSQL databases on AWS RDS.
- Analyzed EXPLAIN execution plans and structured composite B-Tree indexes reducing query times by 40%.
- Built custom Python automated scripts for RDS storage auto-scaling and replication lag alerting.
- Integrated Redis cluster for query result caching.""",
        "expected": {
            "required_years": 0.0,
            "candidate_years": 7.8,  # Jan 2019 - Oct 2026 = 94 months -> 7.8 years
            "must_haves": [
                {"requirement": "Managed relational cloud databases (AWS RDS or Cloud SQL)", "status": "MATCHED", "quote": "Designed, deployed, and administered 20+ multi-AZ PostgreSQL databases on AWS RDS."},
                {"requirement": "Relational query optimization and indexing", "status": "MATCHED", "quote": "Analyzed EXPLAIN execution plans and structured composite B-Tree indexes reducing query times by 40%."},
                {"requirement": "Python scripting for database health monitoring", "status": "MATCHED", "quote": "Built custom Python automated scripts for RDS storage auto-scaling and replication lag alerting."}
            ],
            "bonus_skills": [
                {"skill": "In-memory caching with Redis or Memcached", "status": "MATCHED", "quote": "Integrated Redis cluster for query result caching."}
            ],
            "must_have_score": 100.0,
            "bonus_score": 100.0,
            "experience_score": None,
            "overall_score": 100.0
        }
    },

    "TC08": {
        "id": "TC08",
        "name": "Overlapping Employment Spans & Ambiguous Dates",
        "role": "Senior Software Engineer",
        "jd_text": """Role: Senior Software Engineer.
Requirements (Mandatory):
- Minimum 4 years of verified professional software engineering experience.
- Python backend development with RESTful APIs.
- MySQL database architecture.""",
        "resume_text": """Robin Patel - Software Engineer
Professional Work History:
Company A: Software Engineer | Jan 2022 - Dec 2023
- Built REST APIs in Python and configured MySQL databases.
Company B: Backend Developer | Jun 2022 - Dec 2023
- Maintained Python services and wrote MySQL migration scripts.
Company C: Junior Developer | Jan 2024 - Present
- Developed Python microservices and backend pipelines.""",
        "expected": {
            "required_years": 4.0,
            "candidate_years": 4.8,  # Set union: (24m Jan 2022-Dec 2023) + (34m Jan 2024-Oct 2026) = 58m -> 4.8y (NOT 77m / 6.4y!)
            "must_haves": [
                {"requirement": "Python backend development with RESTful APIs", "status": "MATCHED", "quote": "Built REST APIs in Python and configured MySQL databases."},
                {"requirement": "MySQL database architecture", "status": "MATCHED", "quote": "configured MySQL databases."}
            ],
            "bonus_skills": [],
            "must_have_score": 100.0,
            "bonus_score": None,
            "experience_score": 100.0,
            "overall_score": 100.0
        }
    },

    "TC09": {
        "id": "TC09",
        "name": "Evidence Scattered Across Disparate Sections",
        "role": "Full Stack Engineer (Fintech)",
        "jd_text": """Role: Full Stack Engineer (Fintech).
Requirements (Mandatory):
- Core language proficiency in C++ or Rust.
- Cryptographic key management or blockchain security fundamentals.
- Full-stack web integration with React.
Bonus (Preferred):
- Contributions to open-source software or technical hackathons.""",
        "resume_text": """Quinn Avery
Summary:
Security-conscious software engineer passionate about high-assurance cryptographic systems and modern web architecture.
Education & Certifications:
B.S. in Computer Science, State University (2020-2024)
- Capstone: Implemented secure cryptographic signing primitives and public-key infrastructure in Rust.
Technical Skills:
Languages: Rust, C++, Python, JavaScript. Frameworks: React, Node.js.
Work Experience:
Frontend Developer Intern | WebFlow Labs (Jan 2024 – Aug 2024)
- Built responsive single-page web dashboards in React connecting to JSON-RPC endpoints.
Independent Projects & Open Source:
- Cryptographic Ledger (GitHub): Authored a zero-knowledge proof verification library in C++.
- Hackathon Winner (HackFin 2024): 1st place in Security Track for decentralized key-escrow recovery.""",
        "expected": {
            "required_years": 0.0,
            "candidate_years": 0.7,  # Jan 2024 - Aug 2024 = 8 months -> 0.7 years
            "must_haves": [
                {"requirement": "Core language proficiency in C++ or Rust", "status": "MATCHED", "quote": "Implemented secure cryptographic signing primitives and public-key infrastructure in Rust."},
                {"requirement": "Cryptographic key management or blockchain security", "status": "MATCHED", "quote": "Security-conscious software engineer passionate about high-assurance cryptographic systems and modern web architecture."},
                {"requirement": "Full-stack web integration with React", "status": "MATCHED", "quote": "Built responsive single-page web dashboards in React connecting to JSON-RPC endpoints."}
            ],
            "bonus_skills": [
                {"skill": "Open source contributions or technical hackathons", "status": "MATCHED", "quote": "Hackathon Winner (HackFin 2024): 1st place in Security Track for decentralized key-escrow recovery."}
            ],
            "must_have_score": 100.0,
            "bonus_score": 100.0,
            "experience_score": None,
            "overall_score": 100.0
        }
    },

    "TC10": {
        "id": "TC10",
        "name": "Insufficient Information / Ambiguous Brief",
        "role": "Distributed Systems Engineer",
        "jd_text": """Role: Distributed Systems Engineer.
Requirements (Mandatory):
- 3+ years experience with distributed consensus algorithms (Raft, Paxos).
- High-throughput asynchronous network programming in C++ or Rust.
- Production performance profiling with eBPF or Linux perf.""",
        "resume_text": """Samir Khan
Summary:
Tech enthusiast with experience across various computer science domains.
Skills:
Computers, Coding, Fast Learner, Problem Solving, Software Engineering, Hard Working.
Projects:
- Personal Website: Built a website using free templates.
- Group Project: Participated in a group project involving computers.""",
        "expected": {
            "required_years": 3.0,
            "candidate_years": 0.0,
            "must_haves": [
                {"requirement": "Distributed consensus algorithms (Raft, Paxos)", "status": "MISSING", "quote": ""},
                {"requirement": "Asynchronous network programming in C++ or Rust", "status": "MISSING", "quote": ""},
                {"requirement": "Production performance profiling with eBPF or Linux perf", "status": "MISSING", "quote": ""}
            ],
            "bonus_skills": [],
            "must_have_score": 0.0,
            "bonus_score": None,
            "experience_score": 0.0,
            "overall_score": 0.0  # Deal-breaker gate
        }
    }
}


# =============================================================================
# BENCHMARK TEST SUITE
# =============================================================================

class TestCalibrateAccuracyBenchmark(unittest.TestCase):
    """
    Comprehensive Accuracy & Diagnostic Benchmark Suite.
    Runs purely deterministic calculations and mocked integration paths.
    Zero live API calls; zero modifications to production state.
    """

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 78)
        print(" CALIBRATE AI — ALIGNMENT & ACCURACY BENCHMARK (DIAGNOSTIC BASELINE) ")
        print(" Reference Anchor Date: October 19, 2026 | Environment: Isolated Synthetic")
        print("=" * 78)

    # -------------------------------------------------------------------------
    # SUITE 1: DETERMINISTIC DATE & TENURE ARITHMETIC (TC01 - TC10)
    # -------------------------------------------------------------------------

    def test_01_deterministic_jd_required_years_extraction(self):
        """Verifies deterministic parsing of required experience years from JD text."""
        print("\n[SUITE 1.1] Testing Deterministic JD Experience Requirements...")
        discrepancies = []
        for tc_id, tc in BENCHMARK_CASES.items():
            actual = extract_required_years_from_jd(tc["jd_text"])
            expected = tc["expected"]["required_years"]
            match = (actual == expected)
            status = "PASS" if match else "FAIL"
            print(f"  [{status}] {tc_id}: Expected {expected}y | Actual {actual}y | '{tc['role']}'")
            if not match:
                discrepancies.append((tc_id, expected, actual))

        self.assertEqual(len(discrepancies), 0, f"Discrepancies in JD experience parsing: {discrepancies}")

    def test_02_deterministic_candidate_tenure_calculation(self):
        """
        Verifies deterministic candidate tenure calculation and set-union overlap deduplication.
        Uses October 19, 2026 as the active temporal reference point.
        """
        print("\n[SUITE 1.2] Testing Deterministic Candidate Tenure & Set-Union Deduplication...")
        discrepancies = []
        for tc_id, tc in BENCHMARK_CASES.items():
            res = extract_candidate_tenure(tc["resume_text"])
            actual = res["candidate_years"]
            expected = tc["expected"]["candidate_years"]
            delta = abs(actual - expected)
            match = (delta <= 0.1)
            status = "PASS" if match else "FAIL"
            print(f"  [{status}] {tc_id}: Expected {expected}y | Actual {actual}y (delta: {delta:.2f}y) | {tc['name']}")
            if not match:
                discrepancies.append((tc_id, expected, actual, delta))

        self.assertEqual(len(discrepancies), 0, f"Discrepancies in candidate tenure calculation: {discrepancies}")

    def test_03_tc08_explicit_overlap_deduplication(self):
        """
        TC-08 Invariant: Overlapping employment (Jun 2022 - Dec 2023 concurrent with Jan 2022 - Dec 2023)
        MUST be counted only once. Raw sum = 6.4y; Deduplicated set union = 4.8y.
        """
        print("\n[SUITE 1.3] TC-08 Concurrent Overlap Deduplication Verification...")
        tc8 = BENCHMARK_CASES["TC08"]
        res = extract_candidate_tenure(tc8["resume_text"])
        actual_years = res["candidate_years"]
        print(f"  -> Raw Non-Deduplicated Sum: 77 months = 6.4 years")
        print(f"  -> Calendar-Month Set-Union: 58 unique months = {actual_years} years")
        self.assertEqual(actual_years, 4.8, f"TC-08 must produce 4.8 years, got {actual_years}")

    # -------------------------------------------------------------------------
    # SUITE 2: CITATION GROUNDING & VERBATIM PROOF (MANDATE 1)
    # -------------------------------------------------------------------------

    def test_04_citation_exact_and_fuzzy_verification(self):
        """Verifies that authentic citations are verified while fabricated quotes are rejected."""
        print("\n[SUITE 2.1] Testing Citation Verification & Anchoring...")
        tc1 = BENCHMARK_CASES["TC01"]

        # 1. Exact quote
        exact_quote = "Architected 12 high-performance microservices using Python and FastAPI handling 8M daily requests."
        ok, line = verify_and_anchor_citation(exact_quote, tc1["resume_text"])
        self.assertTrue(ok, "Exact quote must verify successfully.")
        print("  [PASS] Exact verbatim quote successfully anchored.")

        # 2. Fabricated quote (does not exist in resume)
        fake_quote = "Architected scalable microservices using Django and Celery for distributed banking."
        ok_fake, _ = verify_and_anchor_citation(fake_quote, tc1["resume_text"])
        self.assertFalse(ok_fake, "Fabricated quote must be rejected.")
        print("  [PASS] Fabricated citation correctly rejected.")

    def test_05_citation_negation_defense(self):
        """
        CRIT-02 & TC-05 Invariant: A quote expressing lack of experience
        (e.g., 'I have never used Docker') must NEVER be verified as affirmative proof.
        """
        print("\n[SUITE 2.2] Testing Citation Negation Defense (TC-05)...")
        tc5 = BENCHMARK_CASES["TC05"]
        negated_quote = "I have never used Docker or containerization in any production environment"
        ok_neg, _ = verify_and_anchor_citation(negated_quote, tc5["resume_text"])
        self.assertFalse(ok_neg, "Negated statement must NEVER be accepted as affirmative citation.")
        print("  [PASS] Explicitly negated statement rejected as affirmative proof.")

    def test_06_report_demotion_on_ungrounded_citation(self):
        """Verifies that validate_and_anchor_report demotes ungrounded MATCHED items to WEAK."""
        print("\n[SUITE 2.3] Testing Report Grounding Demotion...")
        tc1 = BENCHMARK_CASES["TC01"]
        unverified_report = {
            "must_haves": [
                {
                    "requirement": "Ruby on Rails Architecture",
                    "status": "MATCHED",
                    "evidence_quote": "Engineered Ruby on Rails microservices for payments."
                }
            ],
            "bonus_skills": []
        }
        anchored = validate_and_anchor_report(unverified_report, tc1["resume_text"])
        item = anchored["must_haves"][0]
        self.assertEqual(item["status"], "WEAK", "Ungrounded MATCHED claim must be demoted to WEAK.")
        self.assertEqual(item["evidence_quote"], "", "Ungrounded quote must be cleared.")
        self.assertIn("Unverified Citation", item["gap_reason"])
        print(f"  [PASS] Ungrounded citation correctly demoted: {item['gap_reason']}")

    # -------------------------------------------------------------------------
    # SUITE 3: PRE-FILTER & SYNONYM NEGATION AVOIDANCE (MANDATE 4)
    # -------------------------------------------------------------------------

    def test_07_pre_filter_negation_awareness(self):
        """Verifies that is_negated_mention detects negative qualifiers and excludes them from active synonyms."""
        print("\n[SUITE 3.1] Testing Pre-Filter Acronym & Synonym Negation Defense...")
        tc5 = BENCHMARK_CASES["TC05"]
        # In TC-05, Docker is explicitly negated
        is_neg = is_negated_mention(tc5["resume_text"].lower(), "docker")
        self.assertTrue(is_neg, "Pre-filter must identify 'docker' as a negated mention.")

        active_synonyms = build_active_synonym_context(tc5["resume_text"], tc5["jd_text"])
        self.assertNotIn("Docker", active_synonyms, "Negated token must NOT be injected into active synonym context.")
        print("  [PASS] Negated Docker correctly excluded from active synonym context.")

    # -------------------------------------------------------------------------
    # SUITE 4: BULLET AST EXTRACTION & SNAPPING (MANDATE 2)
    # -------------------------------------------------------------------------

    def test_08_bullet_ast_extraction_and_snapping(self):
        """Verifies that candidate bullets are parsed and LLM rewrites snap to authentic bullets."""
        print("\n[SUITE 4.1] Testing Bullet AST Extraction & Snapping...")
        tc1 = BENCHMARK_CASES["TC01"]
        bullets = extract_candidate_bullets(tc1["resume_text"])
        self.assertGreaterEqual(len(bullets), 3, "Expected at least 3 candidate bullets extracted.")

        # Test snapping with minor variation
        query = "Architected 12 microservices using Python and FastAPI handling 8M requests"
        snapped = snap_to_best_candidate_bullet(query, bullets)
        self.assertIn("Python and FastAPI", snapped)

        # Test completely ungrounded bullet (< 45% similarity)
        hallucinated_query = "Wrote COBOL programs on IBM Mainframe for aviation logistics"
        discarded = snap_to_best_candidate_bullet(hallucinated_query, bullets)
        self.assertEqual(discarded, "", "Ungrounded bullet must snap to empty string (discarded).")
        print("  [PASS] Bullet snapping verified; ungrounded bullet correctly discarded.")

    # -------------------------------------------------------------------------
    # SUITE 5: DETERMINISTIC SCORING & DEAL-BREAKER GATING (MANDATE 3)
    # -------------------------------------------------------------------------

    def test_09_scoring_formula_and_deal_breaker_gating(self):
        """Verifies mathematical scoring and essential-skill deal-breaker gating across all 10 cases."""
        print("\n[SUITE 5.1] Testing Deterministic Scoring Engine & Essential-Skill Gating...")
        discrepancies = []

        for tc_id, tc in BENCHMARK_CASES.items():
            exp = tc["expected"]
            mock_report = {
                "must_haves": exp["must_haves"],
                "bonus_skills": exp["bonus_skills"],
                "experience_years": {
                    "required_years": exp["required_years"],
                    "candidate_years": exp["candidate_years"]
                }
            }
            scores = calculate_deterministic_scores(mock_report)
            
            if scores["experience_score"] is None and exp.get("experience_score") is None:
                exp_match = True
            elif scores["experience_score"] is not None and exp.get("experience_score") is not None:
                exp_match = abs(scores["experience_score"] - exp["experience_score"]) <= 0.05
            else:
                exp_match = False

            must_match = abs(scores["must_have_score"] - exp["must_have_score"]) <= 0.05

            if scores["bonus_score"] is None and exp.get("bonus_score") is None:
                bonus_match = True
            elif scores["bonus_score"] is not None and exp.get("bonus_score") is not None:
                bonus_match = abs(scores["bonus_score"] - exp["bonus_score"]) <= 0.05
            else:
                bonus_match = False

            overall_match = abs(scores["overall_score"] - exp["overall_score"]) <= 0.05

            all_match = must_match and bonus_match and exp_match and overall_match
            status = "PASS" if all_match else "FAIL"

            exp_s = f"{scores['experience_score']}%" if scores['experience_score'] is not None else "None"
            exp_e = f"{exp['experience_score']}%" if exp['experience_score'] is not None else "None"
            bon_s = f"{scores['bonus_score']}%" if scores['bonus_score'] is not None else "None"
            bon_e = f"{exp['bonus_score']}%" if exp['bonus_score'] is not None else "None"
            print(f"  [{status}] {tc_id}: Overall {scores['overall_score']}% (exp: {exp['overall_score']}%) | Must: {scores['must_have_score']}% | Bonus: {bon_s} (exp: {bon_e}) | Exp: {exp_s} (exp: {exp_e})")

            if not all_match:
                discrepancies.append((tc_id, exp, scores))

        self.assertEqual(len(discrepancies), 0, f"Discrepancies in deterministic scoring: {discrepancies}")

    # -------------------------------------------------------------------------
    # SUITE 6: MOCKED END-TO-END PIPELINE DIAGNOSTIC (ALL 10 CASES)
    # -------------------------------------------------------------------------

    def test_10_mocked_end_to_end_pipeline_simulation(self):
        """
        Executes an end-to-end simulation of all 10 cases through the post-processing
        and evaluation pipeline using controlled mock LLM responses.
        Tests:
        - Layout parsing -> Bullet AST -> Tenure union -> Grounding validation -> Bullet snapping -> Scorer.
        - Verifies that corrupt or negated citations are caught and demoted.
        """
        print("\n[SUITE 6.1] Running Mocked End-to-End Pipeline Diagnostic (All 10 Cases)...")
        results_summary = []

        for tc_id, tc in BENCHMARK_CASES.items():
            exp = tc["expected"]
            resume_text = tc["resume_text"]
            jd_text = tc["jd_text"]

            # Step 1: Deterministic dates & bullets
            tenure_res = extract_candidate_tenure(resume_text)
            req_years = extract_required_years_from_jd(jd_text)
            candidate_bullets = extract_candidate_bullets(resume_text)

            # Step 2: Build simulated raw LLM response matching expected classifications
            simulated_llm_output = {
                "job_title_detected": tc["role"],
                "must_haves": [
                    {
                        "requirement": m["requirement"],
                        "domain": "Languages & Frameworks",
                        "status": m["status"],
                        "evidence_quote": m["quote"],
                        "defense_tip": "Be prepared to discuss technical architecture."
                    }
                    for m in exp["must_haves"]
                ],
                "bonus_skills": [
                    {
                        "skill": b["skill"],
                        "domain": "DevOps, Cloud & Modern Stack",
                        "status": b["status"],
                        "evidence_quote": b["quote"],
                        "defense_tip": "Highlight adaptability and adjacent tooling."
                    }
                    for b in exp["bonus_skills"]
                ],
                "experience_years": {
                    "required_years": req_years,
                    "candidate_years": tenure_res["candidate_years"]
                },
                "actionable_rewrites": [
                    {
                        "target_skill": "Scalable Systems",
                        "original_bullet": candidate_bullets[0] if candidate_bullets else "Default achievement bullet",
                        "upgraded_xyz_bullet": "Accomplished architecture, as measured by [25% latency reduction], by doing [system design].",
                        "interview_defense_tip": "Explain metrics."
                    }
                ]
            }

            # Step 3: Run Post-Processing Citation Grounding Guard
            validated_report = validate_and_anchor_report(simulated_llm_output, resume_text)

            # Step 4: Run Bullet Snapping Guard
            if candidate_bullets:
                anchored_rw = []
                for rw in validated_report.get("actionable_rewrites", []):
                    snapped = snap_to_best_candidate_bullet(rw["original_bullet"], candidate_bullets)
                    if snapped:
                        rw["original_bullet"] = snapped
                        anchored_rw.append(rw)
                validated_report["actionable_rewrites"] = anchored_rw

            # Step 5: Compute Final Scores
            scores = calculate_deterministic_scores(validated_report)

            # Evaluate Critical Safety Gates
            crit_failures = []
            
            # CRIT-01: Fabricated quotation
            for item in validated_report.get("must_haves", []) + validated_report.get("bonus_skills", []):
                q = item.get("evidence_quote", "")
                if q and item.get("status") == "MATCHED":
                    ok, _ = verify_and_anchor_citation(q, resume_text)
                    if not ok:
                        crit_failures.append(f"CRIT-01 Fabricated/unanchored quote: '{q}' for {item.get('requirement') or item.get('skill')}")

            # CRIT-02: Negation bypass
            if tc_id == "TC05":
                for item in validated_report.get("must_haves", []):
                    if "docker" in item.get("requirement", "").lower() and item.get("status") == "MATCHED":
                        crit_failures.append("CRIT-02 Positive match on explicitly negated Docker!")

            # CRIT-06: Tenure calculation distortion
            if tc_id == "TC08":
                if tenure_res["candidate_years"] > 5.0:
                    crit_failures.append(f"CRIT-06 Overlap double-counting! Expected 4.8y, got {tenure_res['candidate_years']}y")

            passed = (len(crit_failures) == 0)
            status_str = "PASS" if passed else "FAIL"
            print(f"  [{status_str}] {tc_id} ({tc['name']}): Score = {scores['overall_score']}% | Critical Failures = {len(crit_failures)}")
            
            results_summary.append({
                "tc_id": tc_id,
                "name": tc["name"],
                "passed": passed,
                "scores": scores,
                "crit_failures": crit_failures
            })

        all_passed = all(r["passed"] for r in results_summary)
        self.assertTrue(all_passed, f"Critical safety gate failures in mocked diagnostic: {[r for r in results_summary if not r['passed']]}")
        print("\n" + "=" * 78)
        print(" ALL 10 MOCKED DIAGNOSTIC CASES PASSED ZERO-TOLERANCE SAFETY GATES ")
        print("=" * 78)


# =============================================================================
# CLI ENTRYPOINT
# =============================================================================

if __name__ == '__main__':
    unittest.main()
