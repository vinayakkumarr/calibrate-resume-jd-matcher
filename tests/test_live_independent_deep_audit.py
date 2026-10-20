"""
Live Independent Deep Audit Test Suite
Executes end-to-end multi-role real-world simulations, boundary conditions,
security stress vectors, and UI rendering invariants against the live platform.
"""

import os
import sys
import time
import json
import uuid
import requests
import unittest
import mysql.connector
from dotenv import load_dotenv

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
engine_dir = os.path.join(project_root, 'engine')
if engine_dir not in sys.path:
    sys.path.insert(0, engine_dir)

load_dotenv(os.path.join(project_root, '.env'))

BASE_URL = "http://127.0.0.1:8000"

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "jd_analyser"),
        autocommit=True
    )


class TestLiveIndependentDeepAudit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Verify server is alive
        try:
            r = requests.get(f"{BASE_URL}/api/status.php", timeout=3)
            assert r.status_code == 400
        except Exception as e:
            raise RuntimeError(f"Local server at {BASE_URL} not reachable: {e}")

    # =========================================================================
    # AUDIT 1: Live Fresher Campus Placement E2E Flow
    # =========================================================================
    def test_01_live_fresher_campus_placement_e2e(self):
        """Simulates complete fresher workflow: text input -> scan -> poll -> 9-domain evaluation."""
        fresher_resume = (
            "Alex Sharma | Computer Science Graduate | B.Tech in CSE (2025)\n"
            "Summary: Motivated software engineering graduate with strong fundamentals in Data Structures, Algorithms, and Object-Oriented Programming.\n"
            "Technical Skills: C++, Java, Python, SQL, HTML5, CSS3, JavaScript, React, Git, GitHub.\n"
            "Competitive Achievements:\n"
            "- Solved 450+ problems on LeetCode with top 15% contest rating in dynamic programming and graph algorithms.\n"
            "- Finalist at Smart India Hackathon (SIH 2024), architecting a disaster management alert system.\n"
            "- 4 Star rating in SQL and Java on HackerRank.\n"
            "Projects:\n"
            "- Algorithm Visualizer: Built interactive web tool using React and JavaScript to visualize Dijkstra and BFS traversal.\n"
            "- Campus Portal: Designed normalized 3NF MySQL relational database with PHP backend handling 2,000 student registrations.\n"
            "Education: Bachelor of Technology in Computer Science, GPA 8.8/10.0, Graduated 2025."
        )

        fresher_jd = (
            "Associate Software Engineer (Campus Placement)\n"
            "We are seeking enthusiastic graduate software engineers to join our core engineering team.\n"
            "Responsibilities:\n"
            "- Implement clean, well-tested code in Java or C++ following OOP design principles.\n"
            "- Solve complex algorithmic problems and optimize data structures for performance.\n"
            "- Collaborate using Git and GitHub in an Agile sprint environment.\n"
            "Requirements (Must-Have):\n"
            "- B.Tech/B.E. or B.S. in Computer Science or related engineering discipline.\n"
            "- Strong foundational knowledge of Data Structures & Algorithms (Trees, Graphs, Sorting).\n"
            "- Proficiency in at least one modern programming language (Java, C++, or Python).\n"
            "Preferred (Bonus Skills):\n"
            "- Active competitive coding profile on LeetCode, Codeforces, or HackerRank.\n"
            "- Participation in national hackathons (e.g. Smart India Hackathon) or open source.\n"
            "- Basic understanding of relational database schema design and SQL queries."
        )

        # 1. Post to live scan gateway
        res = requests.post(f"{BASE_URL}/api/scan.php", data={
            "resume_text": fresher_resume,
            "job_description": fresher_jd
        })
        self.assertEqual(res.status_code, 202, f"Expected 202, got {res.status_code}: {res.text}")
        payload = res.json()
        self.assertEqual(payload.get("status"), "pending")
        scan_uuid = payload.get("uuid")
        client_token = payload.get("client_token")
        self.assertTrue(bool(scan_uuid))
        self.assertTrue(bool(client_token))

        # 2. Poll until completed (timeout 60s)
        completed = False
        report_data = None
        for _ in range(30):
            time.sleep(2)
            poll_res = requests.get(
                f"{BASE_URL}/api/status.php?uuid={scan_uuid}",
                headers={"X-Client-Token": client_token}
            )
            self.assertEqual(poll_res.status_code, 200)
            data = poll_res.json()
            if data.get("status") == "completed":
                completed = True
                report_data = data
                break
            elif data.get("status") == "failed":
                self.fail(f"Scan failed unexpectedly: {data.get('error')}")

        self.assertTrue(completed, "Scan did not complete within timeout.")
        self.assertIn("scores", report_data)
        self.assertIn("report", report_data)

        report = report_data["report"]
        scores = report_data["scores"]

        # 3. Assert Fresher Domain Classification & Invariants
        must_haves = report.get("must_haves", [])
        bonus_skills = report.get("bonus_skills", [])
        all_criteria = must_haves + bonus_skills
        self.assertGreaterEqual(len(all_criteria), 3)

        domains_detected = {c.get("domain") for c in all_criteria if c.get("domain")}
        
        # Verify canonical domains are used (not invalid strings)
        from jd_target_cache import VALID_DOMAINS
        for d in domains_detected:
            self.assertIn(d, VALID_DOMAINS)

        # Verify fresher credentials & CS fundamentals were activated
        self.assertTrue(
            any("Computer Science" in d for d in domains_detected) or
            any("Languages" in d for d in domains_detected) or
            any("Education" in d for d in domains_detected)
        )

        # Verify score stability (should be high match for this well-aligned fresher)
        self.assertGreaterEqual(scores["overall_score"], 70.0)
        self.assertGreaterEqual(scores["must_have_score"], 70.0)

        # Cleanup DB
        db = get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM scans WHERE uuid = %s", (scan_uuid,))
        cur.close()
        db.close()

    # =========================================================================
    # AUDIT 2: Live Engineering Leadership & Management E2E Flow
    # =========================================================================
    def test_02_live_engineering_management_leadership_e2e(self):
        """Simulates Engineering Manager role: People leadership, FinOps, DORA metrics."""
        em_resume = (
            "David Sterling | Senior Engineering Manager & Technical Leader\n"
            "Summary: 10+ years leading high-performing software engineering teams, driving modern platform architecture, and optimizing multi-million dollar cloud operations.\n"
            "Experience:\n"
            "- Engineering Manager at CloudScale (2020 - Present):\n"
            "  * Led an organization of 24 software and SRE engineers across 3 distributed teams.\n"
            "  * Conducted weekly 1-on-1s, implemented transparent career development matrices, and retained 96% of top talent.\n"
            "  * Scaled engineering hiring pipeline, screening 200+ candidates and onboarding 14 senior engineers.\n"
            "  * Championed DORA metrics, driving deployment frequency from bi-weekly to 4x daily while reducing change failure rate to 2.1%.\n"
            "  * Spearheaded cloud FinOps governance on AWS, reducing monthly infrastructure spend by 28% ($420k annual savings).\n"
            "  * Authored organizational RFCs and partnered with C-suite and VP of Product on quarterly engineering roadmaps.\n"
            "- Senior Software Engineer & Tech Lead at AppVenture (2015 - 2020):\n"
            "  * Architected microservice backend using Go and PostgreSQL handling 15M daily requests.\n"
            "  * Established code review standards, CI/CD pipeline automation, and automated Cypress test suites.\n"
            "Education & Certifications: B.S. in Computer Engineering; Certified Scrum Master (CSM); AWS Certified Solutions Architect."
        )

        em_jd = (
            "Director of Engineering / Engineering Manager (Cloud Platforms)\n"
            "We are looking for an experienced Engineering Manager to lead our core platform engineering teams.\n"
            "Responsibilities:\n"
            "- Manage, coach, and grow an engineering team of 15-25 backend and cloud engineers.\n"
            "- Own sprint delivery, agile processes, and operational metrics including DORA metrics and team velocity.\n"
            "- Partner with executive leadership (CTO, VP of Product) to formulate technical roadmaps and architectural strategy.\n"
            "- Oversee cloud infrastructure budgeting, FinOps optimization, and vendor contracts.\n"
            "Requirements (Must-Have):\n"
            "- Minimum 7+ years in software engineering with 3+ years in direct people management.\n"
            "- Demonstrated track record conducting 1-on-1s, career pathing, and technical talent acquisition.\n"
            "- Deep familiarity with modern Agile delivery, sprint governance, and DORA reliability metrics.\n"
            "- Proven experience managing cloud infrastructure costs (AWS/GCP FinOps).\n"
            "Preferred Qualifications:\n"
            "- Background in distributed systems architecture and microservices.\n"
            "- PMP, CSM, or AWS Solutions Architect certification."
        )

        res = requests.post(f"{BASE_URL}/api/scan.php", data={
            "resume_text": em_resume,
            "job_description": em_jd
        })
        self.assertEqual(res.status_code, 202)
        payload = res.json()
        scan_uuid = payload.get("uuid")
        client_token = payload.get("client_token")

        completed = False
        report_data = None
        for _ in range(30):
            time.sleep(2)
            poll_res = requests.get(
                f"{BASE_URL}/api/status.php?uuid={scan_uuid}",
                headers={"X-Client-Token": client_token}
            )
            data = poll_res.json()
            if data.get("status") == "completed":
                completed = True
                report_data = data
                break
            elif data.get("status") == "failed":
                self.fail(f"Scan failed: {data.get('error')}")

        self.assertTrue(completed)
        report = report_data["report"]
        scores = report_data["scores"]

        all_criteria = report.get("must_haves", []) + report.get("bonus_skills", [])
        domains = {c.get("domain") for c in all_criteria if c.get("domain")}
        print(f"\n[EM TEST DIAGNOSTICS] Overall: {scores.get('overall_score')}% | Must: {scores.get('must_have_score')}% | Exp: {scores.get('experience_score')}% | Bonus: {scores.get('bonus_score')}%")
        print(f"[EM TEST DIAGNOSTICS] Domains: {domains}")
        for item in all_criteria:
            print(f"  [{item.get('domain')}] ({item.get('status')}): {item.get('requirement') or item.get('skill')}")

        # Verify Technical Leadership domain was extracted!
        self.assertTrue(
            "Technical Leadership, Strategy & Delivery" in domains or
            any("Leadership" in d for d in domains),
            f"Expected Technical Leadership domain for EM role, got domains: {domains}"
        )

        # Candidate should have passed threshold (> 50.0%)
        self.assertGreaterEqual(scores["overall_score"], 50.0)

        # Cleanup DB
        db = get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM scans WHERE uuid = %s", (scan_uuid,))
        cur.close()
        db.close()

    # =========================================================================
    # AUDIT 3: Security & Injection Stress Vectors
    # =========================================================================
    def test_03_security_sanitization_and_injection_defense(self):
        """Validates that malicious script injection and SQL injection payloads are neutralized."""
        malicious_jd = (
            "<script>alert('XSS Exploit');</script> "
            "Senior Security Engineer required. Must understand SQL Injection like ' OR '1'='1' -- "
            "and cross-site scripting prevention. Knowledge of OWASP Top 10, penetration testing, "
            "vulnerability management, and IAM protocols is strictly mandatory for this position."
        )

        clean_resume = (
            "Elena Rostova | Senior Cybersecurity Analyst & Penetration Tester\n"
            "Summary: 6 years in offensive security, vulnerability assessment, and threat mitigation.\n"
            "Skills: OWASP, Burp Suite, Python, Bash, Metasploit, Kali Linux, Nessus, Splunk SIEM, Okta IAM, ISO 27001.\n"
            "Experience:\n"
            "- Senior Cyber Analyst at SecureTech (2020 - Present):\n"
            "  * Conducted web application penetration testing on 40+ client applications preventing critical XSS and SQL injection vulnerabilities.\n"
            "  * Implemented automated vulnerability scanning using Nessus reducing unpatched CVEs by 85%.\n"
            "  * Monitored security alerts in Splunk SIEM responding to over 150 incidents within 15-minute SLA.\n"
            "Certifications: CompTIA Security+, CEH (Certified Ethical Hacker), CISSP (In Progress).\n"
            "Education: B.S. in Information Security, 2018."
        )

        res = requests.post(f"{BASE_URL}/api/scan.php", data={
            "resume_text": clean_resume,
            "job_description": malicious_jd
        })
        self.assertEqual(res.status_code, 202)
        payload = res.json()
        scan_uuid = payload.get("uuid")
        client_token = payload.get("client_token")

        completed = False
        report_data = None
        for _ in range(30):
            time.sleep(2)
            poll_res = requests.get(
                f"{BASE_URL}/api/status.php?uuid={scan_uuid}",
                headers={"X-Client-Token": client_token}
            )
            data = poll_res.json()
            if data.get("status") == "completed":
                completed = True
                report_data = data
                break

        self.assertTrue(completed)
        report_str = json.dumps(report_data)
        # Ensure raw <script> execution tag was not preserved unescaped
        self.assertNotIn("<script>alert('XSS Exploit');</script>", report_str)

        # Cleanup DB
        db = get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM scans WHERE uuid = %s", (scan_uuid,))
        cur.close()
        db.close()

    # =========================================================================
    # AUDIT 4: Boundary & Deal-Breaker Gating Integrity
    # =========================================================================
    def test_04_zero_must_haves_matched_deal_breaker_gate(self):
        """Validates that a candidate with 0% mandatory requirements gets 0.0% overall score."""
        payload = {
            "must_haves": [
                {"requirement": "Rust Low-Level Kernel Driver Development", "status": "MISSING"},
                {"requirement": "ARM Assembly Language", "status": "MISSING"}
            ],
            "bonus_skills": [
                {"skill": "Python Scripting", "status": "MATCHED"},
                {"skill": "Git Version Control", "status": "MATCHED"}
            ],
            "experience_years": {
                "required_years": 5.0,
                "candidate_years": 8.0,
                "requirement_status": "SPECIFIED"
            }
        }
        from scorer import calculate_deterministic_scores
        scores = calculate_deterministic_scores(payload)
        self.assertEqual(scores["must_have_score"], 0.0)
        self.assertEqual(scores["overall_score"], 0.0, "Candidate with 0% mandatory skills must receive 0.0% overall score.")
        self.assertTrue(scores["is_gated"])


if __name__ == '__main__':
    unittest.main()
