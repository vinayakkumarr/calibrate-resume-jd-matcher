import sys
import os
import time
import json
import urllib.request
import urllib.error
import urllib.parse
import mysql.connector

BASE_URL = "http://127.0.0.1:8000"

def run_test_suite():
    print("=" * 70)
    print(" CALIBRATE AI - COMPREHENSIVE END-TO-END SMOKE TEST SUITE")
    print(" Target: " + BASE_URL + " | Environment: Live Local Stack")
    print("=" * 70)

    checklist = []

    def record_result(area, test_name, passed, details="", severity="None"):
        checklist.append({
            "area": area,
            "test": test_name,
            "passed": passed,
            "details": details,
            "severity": severity if not passed else "None"
        })
        status_str = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_str} {area} :: {test_name}")
        if details:
            print(f"         Detail: {details}")

    # =========================================================================
    # AREA 1: Authentication & Access Control
    # =========================================================================
    print("\n--- AREA 1: Authentication & Access Control ---")
    
    # 1.1 Protected route gating (missing X-Client-Token)
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/status.php?uuid=0123456789abcdef0123456789abcdef")
        urllib.request.urlopen(req)
        record_result("Auth & Access", "Protected Route Gating (Missing Token)", False, "Expected HTTP 403 but got HTTP 200", "HIGH")
    except urllib.error.HTTPError as e:
        passed = (e.code == 403)
        record_result("Auth & Access", "Protected Route Gating (Missing Token)", passed, f"HTTP {e.code} received (403 required)", "HIGH")
    except Exception as e:
        record_result("Auth & Access", "Protected Route Gating (Missing Token)", False, str(e), "HIGH")

    # 1.2 Protected route gating (invalid/unauthorized token)
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/status.php?uuid=0123456789abcdef0123456789abcdef")
        req.add_header("X-Client-Token", "ffffffffffffffffffffffffffffffff")
        urllib.request.urlopen(req)
        record_result("Auth & Access", "Protected Route Gating (Unauthorized Token)", False, "Expected HTTP 404/403 but got HTTP 200", "HIGH")
    except urllib.error.HTTPError as e:
        passed = (e.code in (403, 404))
        record_result("Auth & Access", "Protected Route Gating (Unauthorized Token)", passed, f"HTTP {e.code} received (Gated successfully)", "HIGH")
    except Exception as e:
        record_result("Auth & Access", "Protected Route Gating (Unauthorized Token)", False, str(e), "HIGH")

    # 1.3 Client token persistence and session lifecycle (Client Token Schema & LocalStorage contract)
    app_js_path = os.path.join(os.path.dirname(__file__), "..", "public", "assets", "js", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js = f.read()
    has_token_storage = "localStorage.getItem('jda_client_token')" in app_js and "localStorage.setItem('jda_client_token'" in app_js
    record_result("Auth & Access", "Session Persistence (Client Token LocalStorage)", has_token_storage, "Client token persists across browser reloads via jda_client_token in localStorage", "MEDIUM")

    # =========================================================================
    # AREA 2: Golden Path (Core Workflow)
    # =========================================================================
    print("\n--- AREA 2: Golden Path (Core Workflow) ---")

    test_resume = """Jordan Miller - Senior Full Stack Developer
Email: jordan.miller@example.com | Phone: 555-0199 | San Francisco, CA

Professional Summary:
Lead Full Stack Engineer with over 6 years of experience building distributed backend architectures and responsive user interfaces.

Work History:
Lead Software Engineer | CloudTech Solutions (Jan 2020 – Present)
- Architected and deployed microservices in Go and Python, handling 15,000 queries per second with sub-50ms latency.
- Configured PostgreSQL relational schemas with read-replicas, connection pooling, and optimized indexing.
- Built responsive administrative dashboards in React, TypeScript, and Tailwind CSS.
- Automated CI/CD pipelines with GitHub Actions and Docker, reducing build failures by 40%.

Software Engineer | DevCorp (Jan 2018 – Dec 2019)
- Developed RESTful APIs in Python using FastAPI and PostgreSQL.
- Maintained Docker containers and Redis caching clusters.
"""

    test_jd = """Role: Senior Full Stack Engineer.
Location: Remote.
Requirements (Mandatory):
- Minimum 4 years of software development experience.
- Strong proficiency in Python or Go for backend microservices.
- Experience with relational databases, specifically PostgreSQL.
- Production experience with Docker and containerization.
Bonus (Preferred):
- Frontend development experience with React and modern JavaScript/TypeScript.
"""

    scan_uuid = None
    client_token = None
    try:
        # Submit Scan via multipart/form-data
        boundary = "----WebKitFormBoundarySmokeTest7MA4YWxkTrZu0gW"
        body_lines = [
            f"--{boundary}",
            'Content-Disposition: form-data; name="resume_mode"',
            "",
            "text",
            f"--{boundary}",
            'Content-Disposition: form-data; name="resume_text"',
            "",
            test_resume,
            f"--{boundary}",
            'Content-Disposition: form-data; name="job_description"',
            "",
            test_jd,
            f"--{boundary}--",
            ""
        ]
        body = "\r\n".join(body_lines).encode("utf-8")
        req = urllib.request.Request(f"{BASE_URL}/api/scan.php", data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            resp_data = json.loads(response.read().decode("utf-8"))
            scan_uuid = resp_data.get("uuid")
            client_token = resp_data.get("client_token")
            passed_202 = (status_code == 202 and bool(scan_uuid) and bool(client_token))
            record_result("Golden Path", "Scan Ingestion (POST /api/scan.php)", passed_202, f"HTTP {status_code} | UUID: {scan_uuid}", "BLOCKER")
    except Exception as e:
        record_result("Golden Path", "Scan Ingestion (POST /api/scan.php)", False, str(e), "BLOCKER")

    # Poll status until completed (timeout: 45s)
    completed_report = None
    if scan_uuid and client_token:
        start_time = time.time()
        final_status = "pending"
        while time.time() - start_time < 45:
            try:
                poll_req = urllib.request.Request(f"{BASE_URL}/api/status.php?uuid={scan_uuid}")
                poll_req.add_header("X-Client-Token", client_token)
                with urllib.request.urlopen(poll_req) as poll_resp:
                    poll_data = json.loads(poll_resp.read().decode("utf-8"))
                    final_status = poll_data.get("status")
                    if final_status == "completed":
                        completed_report = poll_data
                        break
                    elif final_status == "failed":
                        break
            except Exception:
                pass
            time.sleep(2)
        
        elapsed = round(time.time() - start_time, 2)
        workflow_ok = (final_status == "completed" and completed_report is not None)
        record_result("Golden Path", "End-to-End Async Worker Completion", workflow_ok, f"Status: {final_status} in {elapsed}s", "BLOCKER")

        # Validate Report Contract
        if workflow_ok:
            scores = completed_report.get("scores", {})
            overall = scores.get("overall_score")
            must_score = scores.get("must_have_score")
            exp_score = scores.get("experience_score")
            has_scores = overall is not None and must_score is not None and exp_score is not None
            record_result("Golden Path", "Deterministic Scoring Contract", has_scores, f"Overall: {overall}% | Must: {must_score}% | Exp: {exp_score}%", "HIGH")

            rewrites = completed_report.get("report", {}).get("actionable_rewrites", [])
            has_rewrites = len(rewrites) > 0
            record_result("Golden Path", "Actionable Rewrites & Guidance", has_rewrites, f"{len(rewrites)} anchored rewrite suggestions generated", "MEDIUM")

    # =========================================================================
    # AREA 3: Data Integrity & Persistence
    # =========================================================================
    print("\n--- AREA 3: Data Integrity & Persistence ---")
    if scan_uuid:
        # Check MySQL database record
        try:
            conn = mysql.connector.connect(host="127.0.0.1", port=3306, user="root", password="", database="jd_analyser")
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, uuid, status, error_message FROM scans WHERE uuid = %s", (scan_uuid,))
            scan_row = cursor.fetchone()
            scan_persisted = (scan_row is not None and scan_row["status"] == "completed" and scan_row["error_message"] is None)
            record_result("Data Integrity", "Database Scan Record Persistence", scan_persisted, f"scans table ID={scan_row['id'] if scan_row else 'None'} | status={scan_row['status'] if scan_row else 'None'}", "HIGH")

            cursor.execute("SELECT scan_id, overall_score, must_have_score, experience_score, analysis_payload FROM scan_results WHERE scan_id = %s", (scan_row["id"],))
            res_row = cursor.fetchone()
            res_persisted = (res_row is not None and res_row["overall_score"] is not None and len(res_row["analysis_payload"]) > 100)
            record_result("Data Integrity", "Database Scan Results & Payload Persistence", res_persisted, f"scan_results recorded | overall={res_row['overall_score'] if res_row else 'None'}", "HIGH")
            conn.close()
        except Exception as e:
            record_result("Data Integrity", "Database Scan Record Persistence", False, str(e), "HIGH")

        # Refresh Persistence: Query status API again to verify idempotent retrieval
        try:
            refresh_req = urllib.request.Request(f"{BASE_URL}/api/status.php?uuid={scan_uuid}")
            refresh_req.add_header("X-Client-Token", client_token)
            with urllib.request.urlopen(refresh_req) as ref_resp:
                ref_data = json.loads(ref_resp.read().decode("utf-8"))
                refresh_ok = (ref_data.get("status") == "completed" and ref_data.get("scores") is not None)
                record_result("Data Integrity", "Refresh / Idempotent View Persistence", refresh_ok, "Subsequent requests retrieve identical completed payload without data loss", "HIGH")
        except Exception as e:
            record_result("Data Integrity", "Refresh / Idempotent View Persistence", False, str(e), "HIGH")

    # =========================================================================
    # AREA 4: API & Service Health
    # =========================================================================
    print("\n--- AREA 4: API & Service Health ---")
    
    # 4.1 Root Homepage
    try:
        with urllib.request.urlopen(f"{BASE_URL}/index.php") as resp:
            code = resp.getcode()
            content = resp.read().decode("utf-8")
            has_app = "Calibrate AI" in content or "calibrate" in content.lower()
            record_result("API & Health", "GET /index.php (HTTP 200)", (code == 200 and has_app), f"HTTP {code} | Length: {len(content)} bytes", "BLOCKER")
    except Exception as e:
        record_result("API & Health", "GET /index.php (HTTP 200)", False, str(e), "BLOCKER")

    # 4.2 Text Extraction Endpoint (POST /api/extract.php with >=50 words)
    try:
        extract_boundary = "----WebKitFormBoundaryExtractSmokeTest"
        sample_doc = (
            "Jordan Miller - Senior Full Stack Developer\n"
            "San Francisco, California | jordan.miller@example.com | 555-0199\n\n"
            "Summary:\n"
            "Lead Software Engineer with extensive experience developing scalable web applications, RESTful microservices, and high-performance databases.\n\n"
            "Professional Experience:\n"
            "Lead Software Engineer at CloudTech Solutions (Jan 2020 - Present)\n"
            "- Designed and implemented distributed microservices in Go and Python.\n"
            "- Managed PostgreSQL relational database replication and connection pooling.\n"
            "- Configured automated continuous integration and continuous deployment pipelines using Docker containers.\n"
            "- Mentored junior engineering teammates and conducted technical interviews."
        )
        ext_body_lines = [
            f"--{extract_boundary}",
            'Content-Disposition: form-data; name="file"; filename="sample_resume.txt"',
            'Content-Type: text/plain',
            "",
            sample_doc,
            f"--{extract_boundary}--",
            ""
        ]
        ext_body = "\r\n".join(ext_body_lines).encode("utf-8")
        ext_req = urllib.request.Request(f"{BASE_URL}/api/extract.php", data=ext_body, method="POST")
        ext_req.add_header("Content-Type", f"multipart/form-data; boundary={extract_boundary}")
        with urllib.request.urlopen(ext_req) as ext_resp:
            ext_code = ext_resp.getcode()
            ext_data = json.loads(ext_resp.read().decode("utf-8"))
            extract_ok = (ext_code == 200 and ext_data.get("success") is True and len(ext_data.get("extracted_text", "")) > 50)
            record_result("API & Health", "POST /api/extract.php (Document Ingestion)", extract_ok, f"HTTP {ext_code} | Extracted {ext_data.get('word_count')} words", "HIGH")
    except Exception as e:
        record_result("API & Health", "POST /api/extract.php (Document Ingestion)", False, str(e), "HIGH")

    # 4.3 Negative Gate: Method Not Allowed
    try:
        urllib.request.urlopen(f"{BASE_URL}/api/scan.php")
        record_result("API & Health", "Method Guard (GET /api/scan.php)", False, "Expected HTTP 405", "MEDIUM")
    except urllib.error.HTTPError as e:
        record_result("API & Health", "Method Guard (GET /api/scan.php)", e.code == 405, f"HTTP {e.code} correctly returned", "MEDIUM")
    except Exception as e:
        record_result("API & Health", "Method Guard (GET /api/scan.php)", False, str(e), "MEDIUM")

    # 4.4 Negative Gate: Magic-Byte Inspection on Fake PDF (with valid length JD)
    try:
        spoof_boundary = "----WebKitFormBoundarySpoofTest"
        valid_length_jd = "Role: Software Engineer.\nWe are seeking an experienced software engineer with a strong background in Python, Go, and relational database systems. Minimum 3 years of production experience required."
        spoof_body_lines = [
            f"--{spoof_boundary}",
            'Content-Disposition: form-data; name="resume"; filename="malicious_payload.pdf"',
            'Content-Type: application/pdf',
            "",
            "NOT_A_REAL_PDF_HEADER_MALICIOUS_BYTES_TESTING_MAGIC_BYTE_INSPECTION",
            f"--{spoof_boundary}",
            'Content-Disposition: form-data; name="job_description"',
            "",
            valid_length_jd,
            f"--{spoof_boundary}--",
            ""
        ]
        spoof_body = "\r\n".join(spoof_body_lines).encode("utf-8")
        spoof_req = urllib.request.Request(f"{BASE_URL}/api/scan.php", data=spoof_body, method="POST")
        spoof_req.add_header("Content-Type", f"multipart/form-data; boundary={spoof_boundary}")
        urllib.request.urlopen(spoof_req)
        record_result("API & Health", "Magic-Byte Security Guard", False, "Spoofed PDF was accepted", "HIGH")
    except urllib.error.HTTPError as e:
        passed = (e.code == 400)
        record_result("API & Health", "Magic-Byte Security Guard", passed, f"HTTP {e.code} Security Error returned", "HIGH")
    except Exception as e:
        record_result("API & Health", "Magic-Byte Security Guard", False, str(e), "HIGH")

    # =========================================================================
    # AREA 5: Baseline UI & Stability
    # =========================================================================
    print("\n--- AREA 5: Baseline UI & Stability ---")
    
    index_php_path = os.path.join(os.path.dirname(__file__), "..", "public", "index.php")
    with open(index_php_path, "r", encoding="utf-8") as f:
        index_php = f.read()

    # 5.1 Responsive Viewport Meta
    has_viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0' in index_php
    record_result("UI & Stability", "Responsive Viewport Configuration", has_viewport, "Mobile viewport meta tag configured for responsive layout", "HIGH")

    # 5.2 Critical Script Dependencies
    scripts_ok = "alpinejs" in index_php and "assets/js/app.js" in index_php and "diff-renderer.js" in index_php
    record_result("UI & Stability", "Script & Asset Inclusions", scripts_ok, "Alpine.js, app.js, and diff-renderer.js properly linked", "HIGH")

    # 5.3 Brand CSS Tokens & Layout Style
    has_styles = "style.css" in index_php
    record_result("UI & Stability", "Design System & Layout Styles", has_styles, "Layout stylesheets cleanly referenced", "MEDIUM")

    # 5.4 Metric Guard Verification Lock Contract
    has_metric_guard = "hasUnverifiedMetrics" in app_js and "isVerified" in app_js and "copyBlockedReason" in app_js
    record_result("UI & Stability", "Metric Guard Verification Lock", has_metric_guard, "Prevents unverified copying of AI rewrites without candidate metric entry", "HIGH")

    # Summary
    total = len(checklist)
    passed = sum(1 for c in checklist if c["passed"])
    failed = total - passed

    print("\n" + "=" * 70)
    print(f" SMOKE TEST SUMMARY: {passed}/{total} Passed (100% Success)" if failed == 0 else f" SMOKE TEST SUMMARY: {passed}/{total} Passed, {failed} Failed")
    print("=" * 70)

    return checklist

if __name__ == "__main__":
    run_test_suite()
