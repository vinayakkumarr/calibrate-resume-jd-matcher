import os
import sys
import time
import requests
import mysql.connector
from dotenv import load_dotenv

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

BASE_URL = "http://127.0.0.1:8000"

def test_full_pipeline():
    print("=== RUNNING FULL END-TO-END ASYNCHRONOUS PIPELINE TEST ===")
    
    resume_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'valid_tech_resume.pdf')
    with open(resume_path, 'rb') as f:
        pdf_bytes = f.read()

    job_description = (
        "We are looking for a Senior Backend Engineer to join our high-growth platform team. "
        "The ideal candidate has 4+ years of professional experience with Python and FastAPI, "
        "proven track record designing scalable REST APIs and relational MySQL schemas, "
        "and hands-on experience with Docker, Redis caching, and deploying to AWS Kubernetes clusters."
    )

    # 1. Submit Upload Request
    print("1. Submitting scan request to api/scan.php...")
    files = {'resume': ('alex_rivera_resume.pdf', pdf_bytes, 'application/pdf')}
    data = {'job_description': job_description, 'client_token': 'e2e_test_token'}
    
    res = requests.post(f"{BASE_URL}/api/scan.php", files=files, data=data)
    assert res.status_code == 202, f"Expected 202, got {res.status_code}: {res.text}"
    ticket = res.json()
    scan_uuid = ticket['uuid']
    print(f"   -> Scan accepted! Ticket UUID: {scan_uuid}")

    # 2. Poll Status Endpoint
    print("2. Polling api/status.php for asynchronous execution...")
    start_time = time.time()
    completed = False
    final_data = None

    while time.time() - start_time < 90:
        status_res = requests.get(f"{BASE_URL}/api/status.php?uuid={scan_uuid}")
        assert status_res.status_code == 200
        poll_json = status_res.json()
        current_status = poll_json['status']
        print(f"   Status: [{current_status}] - {poll_json.get('progress_message')}")

        if current_status == 'completed':
            completed = True
            final_data = poll_json
            break
        elif current_status == 'failed':
            raise AssertionError(f"Scan failed with error: {poll_json.get('error_message')}")

        time.sleep(2.0)

    assert completed, "Scan did not complete within 90 seconds"
    print(f"\n3. Analysis Finished in {time.time() - start_time:.1f} seconds!")
    print(f"   Overall Score:    {final_data['scores']['overall_score']}%")
    print(f"   Must-Have Score:  {final_data['scores']['must_have_score']}%")
    print(f"   Experience Score: {final_data['scores']['experience_score']}%")
    print(f"   Bonus Score:      {final_data['scores']['bonus_score']}%")

    report = final_data['report']
    print(f"   Detected Role:    {report.get('job_title_detected')}")
    print(f"   Must-Haves Audited: {len(report.get('must_haves', []))}")
    print(f"   XYZ Rewrites:       {len(report.get('actionable_rewrites', []))}")

    # Clean up test scan in database and storage
    db = mysql.connector.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', 3306)),
        database=os.getenv('DB_NAME', 'jd_analyser'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASS', ''),
        autocommit=True
    )
    cursor = db.cursor()
    cursor.execute("DELETE FROM scans WHERE uuid = %s", (scan_uuid,))
    cursor.close()
    db.close()

    uploaded_pdf = os.path.join(os.path.dirname(__file__), '..', 'storage', 'uploads', f"{scan_uuid}.pdf")
    if os.path.exists(uploaded_pdf):
        os.remove(uploaded_pdf)

    print("\n✅ FULL END-TO-END PIPELINE PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_full_pipeline()
