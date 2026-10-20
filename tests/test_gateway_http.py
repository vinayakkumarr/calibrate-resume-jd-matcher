import os
import sys
import uuid
import time
import requests
import mysql.connector
from dotenv import load_dotenv

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

BASE_URL = "http://127.0.0.1:8000"

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "jd_analyser")
    )

def test_gateway_endpoints():
    print("=== RUNNING MILESTONE 1 HTTP GATEWAY VERIFICATION ===")
    
    # 1. Test GET on scan.php (Expect 405)
    r = requests.get(f"{BASE_URL}/api/scan.php")
    assert r.status_code == 405, f"Expected 405, got {r.status_code}"
    print("[PASS] TC-METHOD: GET /api/scan.php rejected with HTTP 405.")

    # 2. Test Missing Inputs on scan.php (Expect 422)
    r = requests.post(f"{BASE_URL}/api/scan.php")
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"
    print("[PASS] TC-INPUT-MISSING: Empty POST rejected with HTTP 422.")

    # 3. Test Short JD (<200 chars) (TC-06, Expect 422)
    short_jd = "This job description is far too short to provide actionable skill matching."
    files = {'resume': ('test.pdf', b'%PDF-1.4\n%mock\n%%EOF', 'application/pdf')}
    data = {'job_description': short_jd}
    r = requests.post(f"{BASE_URL}/api/scan.php", files=files, data=data)
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"
    assert "minimum 80 characters" in r.text
    print("[PASS] TC-06: Short JD (<80 chars) rejected with HTTP 422.")

    # 4. Test Magic-Byte Rejection (TC-03, Expect 400)
    fake_pdf = b"<?php echo 'malicious php payload'; ?>"
    valid_jd = ("Senior Software Engineer required with 5+ years of experience in distributed systems, "
                "MySQL database optimization, high-throughput backend APIs, cloud infrastructure, and CI/CD pipelines. "
                "Must possess strong communication skills, demonstrated leadership in technical architecture, and a passion for engineering excellence.")
    files = {'resume': ('malicious.pdf', fake_pdf, 'application/pdf')}
    data = {'job_description': valid_jd}
    r = requests.post(f"{BASE_URL}/api/scan.php", files=files, data=data)
    assert r.status_code == 400, f"Expected 400 for fake PDF, got {r.status_code}: {r.text}"
    assert "Security Error" in r.text
    print("[PASS] TC-03: Magic-byte inspection rejected malicious payload disguised as PDF.")

    scan_uuid = None
    watchdog_uuid = None

    try:
        # 5. Test Valid PDF Upload & Scan Initialization (Expect 202)
        real_pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"
        files = {'resume': ('valid_resume.pdf', real_pdf_bytes, 'application/pdf')}
        data = {'job_description': valid_jd}
        r = requests.post(f"{BASE_URL}/api/scan.php", files=files, data=data)
        assert r.status_code == 202, f"Expected 202, got {r.status_code}: {r.text}"
        res_json = r.json()
        scan_uuid = res_json['uuid']
        client_token = res_json.get('client_token', '')
        assert len(scan_uuid) == 32
        assert res_json['status'] == 'pending'
        print(f"[PASS] TC-UPLOAD: Valid PDF accepted with HTTP 202 (Ticket UUID: {scan_uuid}).")

        # 6. Test Status Endpoint - Invalid UUID (Expect 400)
        r = requests.get(f"{BASE_URL}/api/status.php?uuid=invalid-uuid-format")
        assert r.status_code == 400, f"Expected 400, got {r.status_code}"
        print("[PASS] TC-STATUS-INVALID: Invalid UUID rejected with HTTP 400.")

        # 6b. Test Status Endpoint - Missing or Invalid Client Token (Expect 403)
        r = requests.get(f"{BASE_URL}/api/status.php?uuid={'0'*32}")
        assert r.status_code == 403, f"Expected 403 without token, got {r.status_code}"
        print("[PASS] TC-STATUS-403: Missing client token rejected with HTTP 403.")

        # 7. Test Status Endpoint - Not Found with Valid Token (Expect 404)
        r = requests.get(f"{BASE_URL}/api/status.php?uuid={'0'*32}", headers={'X-Client-Token': 'f'*32})
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        print("[PASS] TC-STATUS-404: Non-existent UUID returned HTTP 404.")

        # 8. Test Status Endpoint - Polling Active Ticket (Expect 200)
        r = requests.get(f"{BASE_URL}/api/status.php?uuid={scan_uuid}", headers={'X-Client-Token': client_token})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        status_json = r.json()
        assert status_json['uuid'] == scan_uuid
        assert status_json['status'] in ('pending', 'processing', 'completed', 'failed')
        print(f"[PASS] TC-STATUS-POLL: Status query returned unified envelope (Status: {status_json['status']}).")

        # 9. Test Watchdog 90-Second Timeout Auto-Fail (TC-05)
        db = get_db_connection()
        cursor = db.cursor()
        watchdog_uuid = uuid.uuid4().hex
        watchdog_token = uuid.uuid4().hex
        cursor.execute("""
            INSERT INTO scans (uuid, client_token, ip_subnet, resume_original_name, resume_relative_path, job_description, status, created_at)
            VALUES (%s, %s, 'hash', 'test.pdf', 'uploads/test.pdf', %s, 'processing', NOW() - INTERVAL 95 SECOND)
        """, (watchdog_uuid, watchdog_token, valid_jd))
        db.commit()
        cursor.close()
        db.close()

        r = requests.get(f"{BASE_URL}/api/status.php?uuid={watchdog_uuid}", headers={'X-Client-Token': watchdog_token})
        assert r.status_code == 200
        watchdog_res = r.json()
        assert watchdog_res['status'] == 'failed', f"Expected 'failed', got {watchdog_res['status']}"
        assert "90 seconds" in watchdog_res['error_message']
        print("[PASS] TC-05: Watchdog auto-failed stale scan (>90s) and reported timeout error.")

        # ---------------------------------------------------------------------
        # JD File Upload Test Suite
        # ---------------------------------------------------------------------
        # 10. Test Valid JD Upload via PDF File (Expect 202)
        valid_resume_pdf_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'valid_tech_resume.pdf')
        with open(valid_resume_pdf_path, 'rb') as f:
            sample_resume_pdf = f.read()

        valid_jd_pdf_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'valid_tech_jd.pdf')
        with open(valid_jd_pdf_path, 'rb') as f:
            sample_jd_pdf = f.read()

        jd_pdf_files = {
            'resume': ('candidate_resume.pdf', sample_resume_pdf, 'application/pdf'),
            'job_description_file': ('target_jd.pdf', sample_jd_pdf, 'application/pdf')
        }
        r = requests.post(f"{BASE_URL}/api/scan.php", files=jd_pdf_files, data={'jd_mode': 'file'})
        assert r.status_code == 202, f"Expected 202 for JD PDF upload, got {r.status_code}: {r.text}"
        jd_pdf_res = r.json()
        jd_pdf_uuid = jd_pdf_res['uuid']
        print(f"[PASS] TC-JD-PDF: Valid JD PDF file accepted with HTTP 202 (UUID: {jd_pdf_uuid}).")

        # Verify extracted JD text in DB
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT job_description FROM scans WHERE uuid = %s", (jd_pdf_uuid,))
        row = cursor.fetchone()
        assert row and len(row['job_description']) >= 200, "Expected extracted JD text in database"
        cursor.execute("DELETE FROM scans WHERE uuid = %s", (jd_pdf_uuid,))
        db.commit()
        cursor.close()
        db.close()
        jd_pdf_file_path = os.path.join(os.path.dirname(__file__), '..', 'storage', 'uploads', f"{jd_pdf_uuid}.pdf")
        if os.path.exists(jd_pdf_file_path):
            os.remove(jd_pdf_file_path)

        # 11. Test Valid JD Upload via Plain Text File (Expect 202)
        jd_txt_files = {
            'resume': ('candidate_resume.pdf', sample_jd_pdf, 'application/pdf'),
            'job_description_file': ('target_jd.txt', valid_jd.encode('utf-8'), 'text/plain')
        }
        r = requests.post(f"{BASE_URL}/api/scan.php", files=jd_txt_files, data={'jd_mode': 'file'})
        assert r.status_code == 202, f"Expected 202 for JD TXT upload, got {r.status_code}: {r.text}"
        jd_txt_res = r.json()
        jd_txt_uuid = jd_txt_res['uuid']
        print(f"[PASS] TC-JD-TXT: Valid JD TXT file accepted with HTTP 202 (UUID: {jd_txt_uuid}).")

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("DELETE FROM scans WHERE uuid = %s", (jd_txt_uuid,))
        db.commit()
        cursor.close()
        db.close()
        jd_txt_file_path = os.path.join(os.path.dirname(__file__), '..', 'storage', 'uploads', f"{jd_txt_uuid}.pdf")
        if os.path.exists(jd_txt_file_path):
            os.remove(jd_txt_file_path)

        # 12. Test Unsupported JD File Format (Expect 400)
        jd_bin_files = {
            'resume': ('candidate_resume.pdf', sample_jd_pdf, 'application/pdf'),
            'job_description_file': ('malicious.exe', b'MZ\x90\x00executable', 'application/octet-stream')
        }
        r = requests.post(f"{BASE_URL}/api/scan.php", files=jd_bin_files, data={'jd_mode': 'file'})
        assert r.status_code == 400, f"Expected 400 for unsupported format, got {r.status_code}: {r.text}"
        assert "Unsupported job description file format" in r.text
        print("[PASS] TC-JD-FORMAT: Unsupported file format rejected with HTTP 400.")

        # 13. Test Spoofed JD PDF Magic-Bytes (Expect 400)
        jd_spoofed_files = {
            'resume': ('candidate_resume.pdf', sample_jd_pdf, 'application/pdf'),
            'job_description_file': ('fake_jd.pdf', b'Not a genuine PDF header', 'application/pdf')
        }
        r = requests.post(f"{BASE_URL}/api/scan.php", files=jd_spoofed_files, data={'jd_mode': 'file'})
        assert r.status_code == 400, f"Expected 400 for spoofed PDF header, got {r.status_code}: {r.text}"
        assert "Security Error" in r.text
        print("[PASS] TC-JD-MAGIC: Spoofed JD PDF rejected by magic-byte inspection.")

        # 14. Test Short JD File (<200 chars) (Expect 422)
        jd_short_files = {
            'resume': ('candidate_resume.pdf', sample_jd_pdf, 'application/pdf'),
            'job_description_file': ('short_jd.txt', b'Too short job description.', 'text/plain')
        }
        r = requests.post(f"{BASE_URL}/api/scan.php", files=jd_short_files, data={'jd_mode': 'file'})
        assert r.status_code == 422, f"Expected 422 for short JD file, got {r.status_code}: {r.text}"
        assert "minimum 80 characters" in r.text
        print("[PASS] TC-JD-SHORT: Short JD document (<80 chars) rejected with HTTP 422.")

        # ---------------------------------------------------------------------
        # Hybrid Resume Panel Test Suite
        # ---------------------------------------------------------------------
        # 15. Test Valid Resume Text Ingestion (Expect 202)
        valid_resume_text = (
            "Alex Rivera - Lead Distributed Systems Engineer. "
            "Over 6 years of experience architecting high-throughput backend microservices using Python, FastAPI, "
            "MySQL, Redis, Docker, and Kubernetes. Led cross-functional engineering teams delivering sub-50ms APIs "
            "processing 20M+ daily events. Spearheaded database query optimization cutting database CPU usage by 40%."
        )
        r = requests.post(f"{BASE_URL}/api/scan.php", data={
            'resume_mode': 'text',
            'resume_text': valid_resume_text,
            'job_description': valid_jd
        })
        assert r.status_code == 202, f"Expected 202 for pasted resume text, got {r.status_code}: {r.text}"
        resume_text_res = r.json()
        resume_text_uuid = resume_text_res['uuid']
        print(f"[PASS] TC-RESUME-TEXT: Pasted resume text accepted with HTTP 202 (UUID: {resume_text_uuid}).")

        # Verify scan record and created .txt storage file
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT resume_original_name, resume_relative_path FROM scans WHERE uuid = %s", (resume_text_uuid,))
        row = cursor.fetchone()
        assert row and row['resume_original_name'] == 'Pasted Resume Text'
        assert row['resume_relative_path'].endswith('.txt')
        cursor.execute("DELETE FROM scans WHERE uuid = %s", (resume_text_uuid,))
        db.commit()
        cursor.close()
        db.close()
        resume_txt_file_path = os.path.join(os.path.dirname(__file__), '..', 'storage', 'uploads', f"{resume_text_uuid}.txt")
        if os.path.exists(resume_txt_file_path):
            os.remove(resume_txt_file_path)

        # 16. Test Valid Resume TXT File Upload (Expect 202)
        resume_txt_upload_files = {
            'resume': ('candidate_resume.txt', valid_resume_text.encode('utf-8'), 'text/plain')
        }
        r = requests.post(f"{BASE_URL}/api/scan.php", files=resume_txt_upload_files, data={'job_description': valid_jd})
        assert r.status_code == 202, f"Expected 202 for uploaded TXT resume, got {r.status_code}: {r.text}"
        resume_upload_res = r.json()
        resume_upload_uuid = resume_upload_res['uuid']
        print(f"[PASS] TC-RESUME-TXT-FILE: Uploaded TXT resume accepted with HTTP 202 (UUID: {resume_upload_uuid}).")

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("DELETE FROM scans WHERE uuid = %s", (resume_upload_uuid,))
        db.commit()
        cursor.close()
        db.close()
        resume_upload_file_path = os.path.join(os.path.dirname(__file__), '..', 'storage', 'uploads', f"{resume_upload_uuid}.txt")
        if os.path.exists(resume_upload_file_path):
            os.remove(resume_upload_file_path)

        # 17. Test Short Resume Text (<80 chars) (Expect 422)
        r = requests.post(f"{BASE_URL}/api/scan.php", data={
            'resume_mode': 'text',
            'resume_text': 'Short resume text.',
            'job_description': valid_jd
        })
        assert r.status_code == 422, f"Expected 422 for short resume text, got {r.status_code}: {r.text}"
        assert "Resume text is too short" in r.text
        assert "minimum 80 characters" in r.text
        print("[PASS] TC-RESUME-SHORT: Short resume text (<80 chars) rejected with HTTP 422.")

        # 18. Test Missing Resume Inputs (Expect 422)
        r = requests.post(f"{BASE_URL}/api/scan.php", data={
            'job_description': valid_jd
        })
        assert r.status_code == 422, f"Expected 422 for missing resume, got {r.status_code}: {r.text}"
        assert "Both a resume" in r.text
        print("[PASS] TC-RESUME-MISSING: Missing resume input rejected with HTTP 422.")

        # 18b. Test Concise Inputs in Advisory Range (80-199 chars) (Expect 202)
        concise_jd = "Looking for an experienced AWS Cloud Architect to manage microservices and container deployments." # 97 chars
        concise_resume = "Senior Cloud Architect with 8+ years designing scalable AWS infrastructure and CI/CD pipelines." # 96 chars
        r = requests.post(f"{BASE_URL}/api/scan.php", data={
            'resume_mode': 'text',
            'resume_text': concise_resume,
            'job_description': concise_jd
        })
        assert r.status_code == 202, f"Expected 202 for concise 80-199 char inputs, got {r.status_code}: {r.text}"
        concise_uuid = r.json().get('uuid')
        assert concise_uuid, "Expected uuid returned"
        print("[PASS] TC-CONCISE-INPUT: Concise input (80-199 chars) accepted with HTTP 202.")
        concise_upload_file_path = os.path.join(os.path.dirname(__file__), '..', 'storage', 'uploads', f"{concise_uuid}.txt")
        if os.path.exists(concise_upload_file_path):
            os.remove(concise_upload_file_path)

        # 19. Test GET on extract.php (Expect 405)
        r = requests.get(f"{BASE_URL}/api/extract.php")
        assert r.status_code == 405, f"Expected 405, got {r.status_code}"
        print("[PASS] TC-EXTRACT-METHOD: GET /api/extract.php rejected with HTTP 405.")

        # 20. Test Missing file on extract.php (Expect 422)
        r = requests.post(f"{BASE_URL}/api/extract.php")
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"
        print("[PASS] TC-EXTRACT-MISSING: Missing file rejected with HTTP 422.")

        # 21. Test Fake PDF on extract.php (Expect 400)
        r = requests.post(f"{BASE_URL}/api/extract.php", files={'file': ('fake.pdf', b'Not a PDF', 'application/pdf')})
        assert r.status_code == 400, f"Expected 400 for fake PDF, got {r.status_code}"
        print("[PASS] TC-EXTRACT-MAGIC: Magic-byte inspection rejected invalid PDF on extract.php.")

        # 22. Test Valid Tech Resume on extract.php (Expect 200)
        valid_pdf_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'valid_tech_resume.pdf')
        with open(valid_pdf_path, 'rb') as f:
            r = requests.post(f"{BASE_URL}/api/extract.php", files={'file': ('valid_tech_resume.pdf', f, 'application/pdf')})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get('success') is True, "Expected success: true"
        assert data.get('word_count', 0) > 50, "Expected word_count > 50"
        assert "Alex Rivera" in data.get('extracted_text', ""), "Expected candidate name in extracted text"
        print("[PASS] TC-EXTRACT-VALID-PDF: Layout-aware text extracted with 100% accuracy on extract.php.")

        # 23. Test Low-text PDF on extract.php (Expect 422)
        low_text_pdf = os.path.join(os.path.dirname(__file__), 'fixtures', 'low_text_resume.pdf')
        with open(low_text_pdf, 'rb') as f:
            r = requests.post(f"{BASE_URL}/api/extract.php", files={'file': ('low_text.pdf', f, 'application/pdf')})
        assert r.status_code == 422, f"Expected 422 for low-text PDF, got {r.status_code}"
        print("[PASS] TC-EXTRACT-LOW-TEXT: Low-text / image-only PDF caught and rejected with HTTP 422.")

        # 24. Test Text Document on extract.php (Expect 200)
        sample_txt = ("Senior Distributed Systems Engineer with 8+ years designing high-throughput ingestion pipelines and microservices. "
                      "Proficient in Python, FastAPI, MySQL, PostgreSQL, Docker, Kubernetes, Redis, and AWS cloud infrastructure. "
                      "Architected core event-driven systems handling 25M daily requests with sub-50ms latency. "
                      "Led engineering teams across sprint cycles, technical design reviews, and high-availability production rollouts.")
        r = requests.post(f"{BASE_URL}/api/extract.php", files={'file': ('resume.txt', sample_txt.encode('utf-8'), 'text/plain')})
        assert r.status_code == 200, f"Expected 200 for valid txt, got {r.status_code}: {r.text}"
        assert r.json().get('success') is True, "Expected success: true"
        print("[PASS] TC-EXTRACT-VALID-TXT: Plaintext document extracted and normalized on extract.php.")

        # 25. Test Resume TXT File Exceeding Upper Limit (>25,000 chars) (Expect 422)
        oversized_resume_txt = "A" * 25001
        r = requests.post(f"{BASE_URL}/api/scan.php", files={'resume': ('huge_resume.txt', oversized_resume_txt.encode('utf-8'), 'text/plain')}, data={'job_description': valid_jd})
        assert r.status_code == 422, f"Expected 422 for oversized resume txt file, got {r.status_code}: {r.text}"
        assert "exceeds maximum limit" in r.text
        print("[PASS] TC-RESUME-TXT-TOO-LONG: Oversized resume TXT file (>25k chars) rejected with HTTP 422.")



    finally:
        db = get_db_connection()
        cursor = db.cursor()
        for u in [scan_uuid, watchdog_uuid]:
            if u:
                cursor.execute("DELETE FROM scans WHERE uuid = %s", (u,))
        db.commit()
        cursor.close()
        db.close()

        if scan_uuid:
            test_file_path = os.path.join(os.path.dirname(__file__), '..', 'storage', 'uploads', f"{scan_uuid}.pdf")
            if os.path.exists(test_file_path):
                os.remove(test_file_path)

    print("\n✅ ALL GATEWAY ACCEPTANCE TESTS PASSED!")

if __name__ == "__main__":
    test_gateway_endpoints()
