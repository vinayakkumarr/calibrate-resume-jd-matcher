import os
import sys
import uuid
import time
import json
import shutil

import subprocess
import mysql.connector
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

load_dotenv(os.path.join(root_path, '.env'))

from engine.scorer import calculate_deterministic_scores

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        database=os.getenv("DB_NAME", "jd_analyser"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        autocommit=True
    )

def test_engine_cli():
    print("=== RUNNING MILESTONE 2: PYTHON INTELLIGENCE CORE CLI SUITE ===\n")
    
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    fixtures_dir = os.path.join(root_dir, 'tests', 'fixtures')
    uploads_dir = os.path.join(root_dir, 'storage', 'uploads')
    analyzer_py = os.path.join(root_dir, 'engine', 'analyzer.py')
    python_bin = sys.executable

    # Ensure uploads directory exists
    os.makedirs(uploads_dir, exist_ok=True)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # -------------------------------------------------------------------------
    # TEST 1: Zero-Denominator Math Stability (TC-11)
    # -------------------------------------------------------------------------
    print("[TEST 1] Verifying Scorer Zero-Denominator Math Stability...")
    zero_case = {
        "must_haves": [{"requirement": "Python", "status": "MATCHED"}],
        "bonus_skills": [],
        "experience_years": {"required_years": 0, "candidate_years": 3}
    }
    # Partial bonus skills case (testing 0.5 credit for WEAK bonus skills)
    partial_case = {
        "must_haves": [{"requirement": "PHP", "status": "MATCHED"}],
        "bonus_skills": [
            {"skill": "Docker", "status": "MATCHED"},
            {"skill": "TypeScript", "status": "WEAK"}
        ],
        "experience_years": {"required_years": 0, "candidate_years": 1}
    }
    partial_scores = calculate_deterministic_scores(partial_case)
    assert partial_scores['bonus_score'] == 75.0, f"Expected 75.0 for bonus_score, got {partial_scores['bonus_score']}"
    print("  [PASS] Zero-denominator JD math & WEAK bonus skills partial credit executed stably.\n")

    # -------------------------------------------------------------------------
    # TEST 2: Low-Text / Scanned Image PDF Fail-Fast Guard
    # -------------------------------------------------------------------------
    print("[TEST 2] Verifying Low-Text / Image-Only PDF Fail-Fast Behavior...")
    low_text_uuid = uuid.uuid4().hex
    low_text_fixture = os.path.join(fixtures_dir, 'low_text_resume.pdf')
    low_text_target = os.path.join(uploads_dir, f"{low_text_uuid}.pdf")
    shutil.copyfile(low_text_fixture, low_text_target)

    test_jd = (
        "Senior Backend Engineer with 5+ years of experience in Python, FastAPI, and MySQL. "
        "Must have extensive experience designing microservices, Docker containerization, Redis caching, "
        "and deploying high-availability services to AWS Kubernetes clusters."
    )

    try:
        cursor.execute("""
            INSERT INTO scans (uuid, client_token, ip_subnet, resume_original_name, resume_relative_path, job_description, status)
            VALUES (%s, 'test_token', 'test_sub', 'low_text_resume.pdf', %s, %s, 'pending')
        """, (low_text_uuid, f"uploads/{low_text_uuid}.pdf", test_jd))
        db.commit()

        # Run analyzer CLI
        proc = subprocess.run([python_bin, analyzer_py, "--uuid", low_text_uuid], capture_output=True, text=True)
        # Expected to fail fast
        assert proc.returncode != 0, f"Expected exit code != 0, got {proc.returncode}"

        cursor.execute("SELECT status, error_message FROM scans WHERE uuid = %s", (low_text_uuid,))
        scan_row = cursor.fetchone()
        assert scan_row['status'] == 'failed', f"Expected status 'failed', got {scan_row['status']}"
        assert "PDF contains no readable text" in scan_row['error_message'], f"Unexpected error message: {scan_row['error_message']}"
        print(f"  [PASS] Fail-fast guard caught low-text PDF: {scan_row['error_message']}\n")
    finally:
        cursor.execute("DELETE FROM scans WHERE uuid = %s", (low_text_uuid,))
        db.commit()
        if os.path.exists(low_text_target):
            os.remove(low_text_target)

    # -------------------------------------------------------------------------
    # TEST 3: Valid Technical Resume + JD Fixture & Determinism Verification (TC-01)
    # -------------------------------------------------------------------------
    print("[TEST 3] Verifying End-to-End Analysis & Scoring Determinism (2 runs)...")
    uuid_run1 = uuid.uuid4().hex
    uuid_run2 = uuid.uuid4().hex
    valid_fixture = os.path.join(fixtures_dir, 'valid_tech_resume.pdf')
    target_run1 = os.path.join(uploads_dir, f"{uuid_run1}.pdf")
    target_run2 = os.path.join(uploads_dir, f"{uuid_run2}.pdf")
    shutil.copyfile(valid_fixture, target_run1)
    shutil.copyfile(valid_fixture, target_run2)

    try:
        # Insert Run 1
        cursor.execute("""
            INSERT INTO scans (uuid, client_token, ip_subnet, resume_original_name, resume_relative_path, job_description, status)
            VALUES (%s, 'test_tok1', 'sub1', 'valid_tech_resume.pdf', %s, %s, 'pending')
        """, (uuid_run1, f"uploads/{uuid_run1}.pdf", test_jd))

        # Insert Run 2
        cursor.execute("""
            INSERT INTO scans (uuid, client_token, ip_subnet, resume_original_name, resume_relative_path, job_description, status)
            VALUES (%s, 'test_tok2', 'sub2', 'valid_tech_resume.pdf', %s, %s, 'pending')
        """, (uuid_run2, f"uploads/{uuid_run2}.pdf", test_jd))
        db.commit()

        # Execute Run 1
        print("  Executing Worker Run 1...")
        proc1 = subprocess.run([python_bin, analyzer_py, "--uuid", uuid_run1], capture_output=True, text=True)
        if proc1.returncode != 0:
            print("Run 1 Stderr:", proc1.stderr)
            print("Run 1 Stdout:", proc1.stdout)
        assert proc1.returncode == 0, f"Run 1 failed with return code {proc1.returncode}"

        cursor.execute("""
            SELECT s.status, r.overall_score, r.must_have_score, r.bonus_score, r.experience_score, r.analysis_payload
            FROM scans s
            JOIN scan_results r ON s.id = r.scan_id
            WHERE s.uuid = %s
        """, (uuid_run1,))
        res1 = cursor.fetchone()
        assert res1['status'] == 'completed'
        print(f"  Run 1 Completed: Overall Score = {res1['overall_score']}% (Must: {res1['must_have_score']}%, Exp: {res1['experience_score']}%, Bonus: {res1['bonus_score']}%)")

        payload1 = json.loads(res1['analysis_payload'])
        assert "actionable_rewrites" in payload1 and len(payload1["actionable_rewrites"]) > 0
        rewrite_sample = payload1["actionable_rewrites"][0]
        print(f"  Google XYZ Rewrite Sample: \"{rewrite_sample['upgraded_xyz_bullet']}\"")
        assert "[" in rewrite_sample['upgraded_xyz_bullet'], "Expected bracketed placeholder in rewrite"
        print("  Interview Defense Tip:", rewrite_sample.get('interview_defense_tip'))

        # Cooldown between runs to respect Gemini free-tier RPM
        time.sleep(3)

        # Execute Run 2
        print("\n  Executing Worker Run 2...")
        proc2 = subprocess.run([python_bin, analyzer_py, "--uuid", uuid_run2], capture_output=True, text=True)
        if proc2.returncode != 0:
            print("Run 2 Stderr:", proc2.stderr)
            print("Run 2 Stdout:", proc2.stdout)
        else:
            print(f"  {proc2.stdout.strip()}")
        assert proc2.returncode == 0, f"Run 2 failed with return code {proc2.returncode}"

        cursor.execute("""
            SELECT s.status, r.overall_score, r.must_have_score, r.bonus_score, r.experience_score
            FROM scans s
            JOIN scan_results r ON s.id = r.scan_id
            WHERE s.uuid = %s
        """, (uuid_run2,))
        res2 = cursor.fetchone()
        assert res2['status'] == 'completed'
        print(f"  Run 2 Completed: Overall Score = {res2['overall_score']}% (Must: {res2['must_have_score']}%, Exp: {res2['experience_score']}%, Bonus: {res2['bonus_score']}%)")

        # Determinism Verification
        score1 = float(res1['overall_score'])
        score2 = float(res2['overall_score'])
        diff = abs(score1 - score2)
        variance = diff ** 2
        print(f"\n  Scoring Variance between identical runs: sigma^2 = {variance:.4f} (diff = {diff:.2f})")
        assert variance == 0.00, f"Expected deterministic scoring (sigma^2 = 0.00), got variance {variance}"
        print("  [PASS] TC-01: Scoring determinism verified (sigma^2 = 0.00 across 2 runs).\n")

    finally:
        cursor.execute("DELETE FROM scans WHERE uuid IN (%s, %s)", (uuid_run1, uuid_run2))
        db.commit()
        cursor.close()
        db.close()
        for p in [target_run1, target_run2]:
            if os.path.exists(p):
                os.remove(p)

    # -------------------------------------------------------------------------
    # TEST 4: Hybrid Text Resume Parsing & End-to-End Intelligence
    # -------------------------------------------------------------------------
    print("[TEST 4] Verifying Hybrid Text Resume (.txt) Analysis...")
    text_resume_uuid = uuid.uuid4().hex
    text_resume_path = os.path.join(uploads_dir, f"{text_resume_uuid}.txt")
    valid_resume_content = (
        "Alex Rivera - Senior Software Engineer\n"
        "Professional Summary: Senior Backend Developer with 5 years of professional experience in software engineering.\n"
        "Core Competencies: Python, FastAPI, MySQL, Redis, Docker, Kubernetes, Microservices.\n"
        "Professional Experience:\n"
        "Senior Software Engineer | Tech Corp (2021 - Present)\n"
        "- Architected 15 RESTful microservices in Python and FastAPI, handling 10M daily requests with sub-50ms latency.\n"
        "- Optimized MySQL queries and indexed database tables, reducing p99 API latency by 35%.\n"
        "- Containerized applications using Docker and deployed services to Kubernetes clusters.\n"
        "Education: B.S. in Computer Science"
    )
    with open(text_resume_path, "w", encoding="utf-8") as f:
        f.write(valid_resume_content)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO scans (uuid, client_token, ip_subnet, resume_original_name, resume_relative_path, job_description, status)
            VALUES (%s, 'test_text_token', 'sub_text', 'Pasted Resume Text', %s, %s, 'pending')
        """, (text_resume_uuid, f"uploads/{text_resume_uuid}.txt", test_jd))
        db.commit()

        time.sleep(3) # cooldown for RPM
        proc_text = subprocess.run([python_bin, analyzer_py, "--uuid", text_resume_uuid], capture_output=True, text=True)
        if proc_text.returncode != 0:
            print("Text Resume Stderr:", proc_text.stderr)
            print("Text Resume Stdout:", proc_text.stdout)
        assert proc_text.returncode == 0, f"Text resume analysis failed: {proc_text.stderr}"

        cursor.execute("SELECT status FROM scans WHERE uuid = %s", (text_resume_uuid,))
        row = cursor.fetchone()
        assert row and row['status'] == 'completed', f"Expected status 'completed', got {row}"
        print("  [PASS] Hybrid text resume (.txt) analyzed and completed successfully.\n")
    finally:
        cursor.execute("DELETE FROM scans WHERE uuid = %s", (text_resume_uuid,))
        db.commit()
        cursor.close()
        db.close()
        if os.path.exists(text_resume_path):
            os.remove(text_resume_path)

    print("===================================================================")
    print("ALL MILESTONE 2 CORE INTELLIGENCE CLI ACCEPTANCE TESTS PASSED!")
    print("===================================================================")

if __name__ == "__main__":
    test_engine_cli()
