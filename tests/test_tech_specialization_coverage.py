"""
Test Suite: Tech & Software Specialization Coverage Across 7 Core Role Families
Verifies AST bullet extraction, taxonomy bridge matching, metric grounding,
and deterministic scoring across:
1. Software Engineering & Full Stack
2. Data Engineering & Analytics
3. Cloud Infrastructure, DevOps & SRE
4. Cybersecurity & IT Security
5. IT Operations, Systems & Enterprise Support
6. Quality Engineering & Automated Testing
7. Solutions Architecture & Technical Leadership
"""

import os
import sys
import unittest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
engine_dir = os.path.join(project_root, 'engine')
if engine_dir not in sys.path:
    sys.path.insert(0, engine_dir)

from parsers.bullet_extractor import extract_candidate_bullets, snap_to_best_candidate_bullet
from pre_filter import (
    COMMON_TECH_SYNONYMS,
    TECH_TAXONOMY_BRIDGES,
    build_active_synonym_context,
    is_negated_mention
)
from grounding_verifier import verify_metric_claim_grounding, _get_metric_unit
from scorer import calculate_deterministic_scores
from jd_target_cache import validate_jd_targets_schema, CANONICAL_9_DOMAINS, VALID_DOMAINS


class TestTechSpecializationCoverage(unittest.TestCase):

    # -------------------------------------------------------------------------
    # 1. AST Bullet Extractor: Action Verbs & Technical Content
    # -------------------------------------------------------------------------
    def test_01_data_engineering_bullet_extraction(self):
        """Data engineering bullets with analyzed/modeled/queried are extracted."""
        bullet = "Modeled dimensional data warehouses and queried 50M rows daily using Snowflake and dbt."
        bullets = extract_candidate_bullets(f"Experience\n- {bullet}")
        self.assertTrue(len(bullets) >= 1)
        self.assertIn("Snowflake", bullets[0])

    def test_02_cloud_sre_bullet_extraction(self):
        """Cloud & SRE bullets with provisioned/orchestrated/monitored are extracted."""
        bullet = "Provisioned multi-region AWS infrastructure using Terraform and monitored cluster health with Prometheus."
        bullets = extract_candidate_bullets(f"Experience\n- {bullet}")
        self.assertTrue(len(bullets) >= 1)
        self.assertIn("Terraform", bullets[0])

    def test_03_cybersecurity_bullet_extraction(self):
        """Cybersecurity bullets with patched/hardened/audited/secured are extracted."""
        bullet = "Hardened Linux servers, audited IAM roles in Okta, and patched 120 critical CVE vulnerabilities."
        bullets = extract_candidate_bullets(f"Experience\n- {bullet}")
        self.assertTrue(len(bullets) >= 1)
        self.assertIn("vulnerabilities", bullets[0])

    def test_04_it_ops_bullet_extraction(self):
        """IT Ops bullets with administered/resolved/configured are extracted."""
        bullet = "Administered Active Directory domain controllers, managed SSO policies, and resolved 250 enterprise tickets."
        bullets = extract_candidate_bullets(f"Experience\n- {bullet}")
        self.assertTrue(len(bullets) >= 1)
        self.assertIn("Active Directory", bullets[0])

    def test_05_qa_testing_bullet_extraction(self):
        """QA bullets with tested/validated/benchmarked are extracted."""
        bullet = "Tested microservice APIs and validated end-to-end user workflows using Cypress and Playwright."
        bullets = extract_candidate_bullets(f"Experience\n- {bullet}")
        self.assertTrue(len(bullets) >= 1)
        self.assertIn("Cypress", bullets[0])

    # -------------------------------------------------------------------------
    # 2. Taxonomy Bridges & Acronym Handling
    # -------------------------------------------------------------------------
    def test_06_data_warehouse_taxonomy_bridges(self):
        """Data warehouse synonyms and bridges resolve correctly."""
        resume = "Built analytical pipelines in Snowflake and BigQuery for business data."
        jd = "Seeking candidate with cloud data warehousing experience."
        context = build_active_synonym_context(resume, jd)
        self.assertIn("SNOWFLAKE", context)
        self.assertIn("Cloud Data Warehousing", context)

        # BI tools bridge
        resume_bi = "Developed executive performance reports using Tableau."
        jd_bi = "Requires hands-on experience in business intelligence reporting."
        context_bi = build_active_synonym_context(resume_bi, jd_bi)
        self.assertIn("TABLEAU", context_bi)
        self.assertIn("Business Intelligence Reporting", context_bi)

    def test_07_observability_and_iac_bridges(self):
        """Observability and IaC tooling bridges resolve correctly."""
        resume = "Monitored infrastructure telemetry using Datadog and Grafana dashboards."
        jd = "Looking for telemetry and observability engineer."
        context = build_active_synonym_context(resume, jd)
        self.assertIn("DATADOG", context)
        self.assertIn("GRAFANA", context)
        self.assertIn("Observability And Telemetry Monitoring", context)

        # Terraform / IaC bridge
        resume_iac = "Automated multi-account AWS infrastructure using Terraform and Terragrunt."
        jd_iac = "Deep expertise in declarative infrastructure as code automation."
        context_iac = build_active_synonym_context(resume_iac, jd_iac)
        self.assertIn("TERRAFORM", context_iac)
        self.assertIn("Infrastructure As Code", context_iac)

        # Automated testing bridge
        resume_qa = "Created automated test suites using Cypress and Playwright."
        jd_qa = "Must have extensive background writing automated test suites."
        context_qa = build_active_synonym_context(resume_qa, jd_qa)
        self.assertIn("CYPRESS", context_qa)
        self.assertIn("Automated Test Suites", context_qa)

        # Identity & IAM bridge
        resume_iam = "Administered user lifecycle and SSO integrations with Okta."
        jd_iam = "Manage enterprise identity and access management across organization."
        context_iam = build_active_synonym_context(resume_iam, jd_iam)
        self.assertIn("OKTA", context_iam)
        self.assertIn("Enterprise Identity And Access Management", context_iam)

    def test_08_tech_acronyms_expansion(self):
        """Acronym expansions for Data, SRE, Security, and IT are present and active."""
        self.assertIn("etl", COMMON_TECH_SYNONYMS)
        self.assertIn("bi", COMMON_TECH_SYNONYMS)
        self.assertIn("iac", COMMON_TECH_SYNONYMS)
        self.assertIn("sre", COMMON_TECH_SYNONYMS)
        self.assertIn("siem", COMMON_TECH_SYNONYMS)
        self.assertIn("iam", COMMON_TECH_SYNONYMS)
        self.assertIn("soc", COMMON_TECH_SYNONYMS)
        self.assertIn("mfa", COMMON_TECH_SYNONYMS)
        self.assertIn("sso", COMMON_TECH_SYNONYMS)
        self.assertIn("vpn", COMMON_TECH_SYNONYMS)
        self.assertIn("dns", COMMON_TECH_SYNONYMS)
        self.assertIn("e2e", COMMON_TECH_SYNONYMS)

        resume = "Built production ETL pipelines, configured IaC templates, and maintained SRE SLOs."
        jd = "Must have strong ETL, IaC, and SRE background."
        context = build_active_synonym_context(resume, jd)
        self.assertIn("ETL", context)
        self.assertIn("IAC", context)
        self.assertIn("SRE", context)

    # -------------------------------------------------------------------------
    # 3. Metric Grounding for Technical Units
    # -------------------------------------------------------------------------
    def test_09_data_unit_grounding(self):
        """Data metrics (records, rows, pipelines) are accurately grounded and cross-unit spoofing blocked."""
        orig_bullet = "Engineered real-time streaming pipeline processing 500 daily records with zero dropped events."

        # Valid rewrite preserving 500 records
        claim_valid = "500 daily records"
        self.assertTrue(verify_metric_claim_grounding(claim_valid, orig_bullet))

        # Invalid rewrite swapping records with users
        claim_invalid = "500 active users"
        self.assertFalse(verify_metric_claim_grounding(claim_invalid, orig_bullet))

    def test_10_cloud_sre_unit_grounding(self):
        """Cloud and cluster metrics (nodes, clusters, pods) are accurately grounded."""
        orig_bullet = "Managed autoscaling Kubernetes cluster with 80 nodes across 3 availability zones."

        # Valid rewrite preserving 80 nodes
        self.assertTrue(verify_metric_claim_grounding("80 nodes", orig_bullet))

        # Incompatible unit swapping nodes with servers or microservices
        self.assertFalse(verify_metric_claim_grounding("80 microservices", orig_bullet))

    def test_11_cybersecurity_unit_grounding(self):
        """Security metrics (vulnerabilities, alerts) are accurately grounded."""
        orig_bullet = "Remediated 45 critical vulnerabilities in 30 days following an external SOC2 audit."

        # Valid grounding for 45 vulnerabilities
        self.assertTrue(verify_metric_claim_grounding("45 vulnerabilities", orig_bullet))
        # Valid grounding for 30 days
        self.assertTrue(verify_metric_claim_grounding("30 days", orig_bullet))

        # Incompatible unit swapping 45 vulnerabilities with 45 endpoints
        self.assertFalse(verify_metric_claim_grounding("45 endpoints", orig_bullet))

    # -------------------------------------------------------------------------
    # 4. Multi-Family Deterministic Scoring
    # -------------------------------------------------------------------------
    def test_12_data_engineer_profile_scoring(self):
        """Data Engineer scoring profile with must-haves, experience, and bonus skills."""
        payload = {
            "must_haves": [
                {"requirement": "SQL", "status": "MATCHED"},
                {"requirement": "Python", "status": "MATCHED"},
                {"requirement": "Snowflake", "status": "MATCHED"},
                {"requirement": "Apache Spark", "status": "WEAK"},
            ],
            "bonus_skills": [
                {"skill": "dbt", "status": "MATCHED"},
                {"skill": "Kafka", "status": "WEAK"},
            ],
            "experience_years": {"required_years": 4.0, "candidate_years": 5.0, "requirement_status": "SPECIFIED"}
        }
        res = calculate_deterministic_scores(payload)
        self.assertEqual(res["must_have_score"], 87.5)
        self.assertEqual(res["experience_score"], 100.0)
        self.assertEqual(res["bonus_score"], 75.0)
        # Expected: 87.5*0.50 + 100*0.25 + 75*0.25 = 43.75 + 25 + 18.75 = 87.5
        self.assertEqual(res["overall_score"], 87.5)

    def test_13_cybersecurity_analyst_zero_bonus_renormalization(self):
        """Security profile where JD has 0 bonus skills renormalizes dynamically."""
        payload = {
            "must_haves": [
                {"requirement": "SIEM", "status": "MATCHED"},
                {"requirement": "Incident Response", "status": "MATCHED"},
                {"requirement": "Network Security", "status": "WEAK"},
            ],
            "bonus_skills": [],
            "experience_years": {"required_years": 5.0, "candidate_years": 3.0, "requirement_status": "SPECIFIED"}
        }
        res = calculate_deterministic_scores(payload)
        self.assertIsNone(res["bonus_score"])
        self.assertTrue(res["bonus_excluded"])
        self.assertEqual(res["experience_score"], 60.0)
        # Must haves: (1 + 1 + 0.5)/3 = 83.33%
        # Experience: 3/5 = 60.0%
        # Active weights: 0.50 + 0.25 = 0.75
        # (83.33*0.50 + 60*0.25)/0.75 = (41.665 + 15)/0.75 = 56.665/0.75 = 75.55%
        self.assertAlmostEqual(res["overall_score"], 75.56, places=1)

    def test_14_sre_profile_perfect_match(self):
        """SRE profile with all criteria 100% matched produces 100.0."""
        payload = {
            "must_haves": [
                {"requirement": "Kubernetes", "status": "MATCHED"},
                {"requirement": "Terraform", "status": "MATCHED"},
                {"requirement": "Linux Internals", "status": "MATCHED"},
            ],
            "bonus_skills": [
                {"skill": "Golang", "status": "MATCHED"}
            ],
            "experience_years": {"required_years": 5.0, "candidate_years": 8.0, "requirement_status": "SPECIFIED"}
        }
        res = calculate_deterministic_scores(payload)
        self.assertEqual(res["overall_score"], 100.0)
        self.assertEqual(res["must_have_score"], 100.0)
        self.assertEqual(res["experience_score"], 100.0)
        self.assertEqual(res["bonus_score"], 100.0)

    # -------------------------------------------------------------------------
    # 5. Career Stage & Seniority Coverage Across 9 Universal Domains
    # -------------------------------------------------------------------------
    def test_15_canonical_9_domains_schema_validation(self):
        """All 9 canonical domains pass strict schema validation."""
        self.assertEqual(len(CANONICAL_9_DOMAINS), 9)
        for domain in CANONICAL_9_DOMAINS:
            payload = {
                "job_title_detected": f"Specialist in {domain}",
                "required_years": 3.0,
                "must_haves": [{"requirement": "Core Requirement", "domain": domain}],
                "bonus_skills": [{"skill": "Bonus Competency", "domain": domain}]
            }
            self.assertTrue(validate_jd_targets_schema(payload), f"Domain failed validation: {domain}")

    def test_16_fresher_campus_hire_profile(self):
        """Fresher profile with DSA, OOP, LeetCode, and B.Tech degree matches and scores cleanly."""
        fresher_payload = {
            "job_title_detected": "Associate Software Engineer",
            "required_years": 0.0,
            "must_haves": [
                {"requirement": "Data Structures & Algorithms (Trees, Graphs, DP)", "domain": "Computer Science Fundamentals & System Design", "status": "MATCHED"},
                {"requirement": "Object-Oriented Programming (Java / C++)", "domain": "Languages & Frameworks", "status": "MATCHED"},
                {"requirement": "B.Tech or B.S. in Computer Science", "domain": "Education, Certifications & Professional Proof", "status": "MATCHED"},
            ],
            "bonus_skills": [
                {"skill": "LeetCode / HackerRank Problem Solving", "domain": "Education, Certifications & Professional Proof", "status": "MATCHED"},
                {"skill": "Smart India Hackathon or Capstone Project", "domain": "Education, Certifications & Professional Proof", "status": "MATCHED"}
            ],
            "experience_years": {"required_years": 0.0, "candidate_years": 0.5, "requirement_status": "UNSPECIFIED"}
        }
        self.assertTrue(validate_jd_targets_schema(fresher_payload))
        scores = calculate_deterministic_scores(fresher_payload)
        self.assertEqual(scores["must_have_score"], 100.0)
        self.assertEqual(scores["bonus_score"], 100.0)
        self.assertTrue(scores["experience_excluded"])
        # Renormalized: must=0.50, bonus=0.25 -> 100%
        self.assertEqual(scores["overall_score"], 100.0)

    def test_17_engineering_manager_leadership_profile(self):
        """Engineering Manager profile with People Leadership, DORA Metrics, Sprint Delivery, and FinOps."""
        em_payload = {
            "job_title_detected": "Engineering Manager (Platform Team)",
            "required_years": 7.0,
            "must_haves": [
                {"requirement": "People Management (1-on-1s, Career Progression, Hiring)", "domain": "Technical Leadership, Strategy & Delivery", "status": "MATCHED"},
                {"requirement": "Agile Delivery & DORA Metrics (Lead Time, MTTR, Deployment Frequency)", "domain": "Technical Leadership, Strategy & Delivery", "status": "MATCHED"},
                {"requirement": "Cloud Infrastructure Cost Governance (FinOps)", "domain": "Technical Leadership, Strategy & Delivery", "status": "WEAK"},
                {"requirement": "Distributed Architecture Comprehension", "domain": "Computer Science Fundamentals & System Design", "status": "MATCHED"},
            ],
            "bonus_skills": [
                {"skill": "Certified Scrum Master (CSM) or PMP", "domain": "Education, Certifications & Professional Proof", "status": "MATCHED"}
            ],
            "experience_years": {"required_years": 7.0, "candidate_years": 8.5, "requirement_status": "SPECIFIED"}
        }
        self.assertTrue(validate_jd_targets_schema(em_payload))
        scores = calculate_deterministic_scores(em_payload)
        # must_haves: (1 + 1 + 0.5 + 1)/4 = 3.5/4 = 87.5%
        self.assertEqual(scores["must_have_score"], 87.5)
        self.assertEqual(scores["experience_score"], 100.0)
        self.assertEqual(scores["bonus_score"], 100.0)
        # overall: 87.5*0.50 + 100*0.25 + 100*0.25 = 43.75 + 25 + 25 = 93.75%
        self.assertEqual(scores["overall_score"], 93.75)

    def test_18_staff_principal_architect_profile(self):
        """Staff/Principal Architect profile with High Availability (99.999%), RFC/ADR Governance, and Multi-Cloud."""
        staff_payload = {
            "job_title_detected": "Principal Enterprise Architect",
            "required_years": 12.0,
            "must_haves": [
                {"requirement": "High-Level Distributed Systems Architecture (99.999% HA)", "domain": "Computer Science Fundamentals & System Design", "status": "MATCHED"},
                {"requirement": "Multi-Cloud Strategy (AWS & GCP Enterprise Deployments)", "domain": "Cloud, Infrastructure & DevOps", "status": "MATCHED"},
                {"requirement": "Cross-Organization RFC / ADR Architectural Governance", "domain": "Technical Leadership, Strategy & Delivery", "status": "MATCHED"},
                {"requirement": "Zero Trust Security Architecture & Compliance", "domain": "Cybersecurity, Identity & IT Operations", "status": "MATCHED"},
            ],
            "bonus_skills": [
                {"skill": "Granted Technology Patents or IEEE Technical Publications", "domain": "Education, Certifications & Professional Proof", "status": "MATCHED"}
            ],
            "experience_years": {"required_years": 12.0, "candidate_years": 15.0, "requirement_status": "SPECIFIED"}
        }
        self.assertTrue(validate_jd_targets_schema(staff_payload))
        scores = calculate_deterministic_scores(staff_payload)
        self.assertEqual(scores["overall_score"], 100.0)
        self.assertEqual(scores["must_have_score"], 100.0)
        self.assertEqual(scores["bonus_score"], 100.0)


if __name__ == '__main__':
    unittest.main()
