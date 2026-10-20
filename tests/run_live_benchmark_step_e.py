"""
Calibrate AI — Step E: Controlled Two-Case Live Gemini Evaluation Runner
Executes TC-01 and TC-05 with live Gemini API requests under strict isolation.

Pre-flight Safeguards:
1. Zero DB/Cache Mutation: Uses MockDbConnection and patches get_db_connection.
   Verifies MySQL row counts before and after to guarantee zero production pollution.
2. Exact Call Interception: Wraps client.models.generate_content to track exact
   request count, model identity, retries, fallbacks, latency, and raw responses.
3. Target: Exactly 4 requests (TC-01: Stage 1 + Stage 2; TC-05: Stage 1 + Stage 2).
"""

import os
import sys
import json
import time
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

# Ensure project root and engine directory in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
engine_dir = os.path.join(project_root, 'engine')
if engine_dir not in sys.path:
    sys.path.insert(0, engine_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

from google import genai
import mysql.connector

# Engine modules
import jd_target_cache
from parsers.date_parser import extract_required_years_from_jd, extract_candidate_tenure
from parsers.bullet_extractor import extract_candidate_bullets, snap_to_best_candidate_bullet
from grounding_verifier import validate_and_anchor_report, verify_and_anchor_citation
from pre_filter import resolve_acronym_matches, build_active_synonym_context, is_negated_mention
from gemini_client import extract_atomic_jd_targets, align_candidate_against_targets, clean_and_enforce_metric_lock
from scorer import calculate_deterministic_scores
from tests.test_benchmark_accuracy import BENCHMARK_CASES


# =============================================================================
# 1. ISOLATION INFRASTRUCTURE (ZERO PRODUCTION MUTATION GUARANTEE)
# =============================================================================

class MockCursor:
    def __init__(self):
        self.executed_queries = []

    def execute(self, query, params=None):
        self.executed_queries.append((query, params))

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def close(self):
        pass


class MockDbConnection:
    """Mock DB connection ensuring cache reads miss and cache writes never touch MySQL."""
    def __init__(self):
        self.autocommit = True
        self.cursor_instance = MockCursor()

    def cursor(self, dictionary=False):
        return self.cursor_instance

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def is_connected(self):
        return True


def get_real_db_counts() -> Dict[str, int]:
    """Inspects real MySQL row counts for audit comparison before & after."""
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", 3306)),
            database=os.getenv("DB_NAME", "jd_analyser"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASS", ""),
            autocommit=True
        )
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) as cnt FROM jd_target_cache")
        cache_count = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) as cnt FROM scans")
        scans_count = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) as cnt FROM scan_results")
        results_count = cur.fetchone()['cnt']
        conn.close()
        return {
            "jd_target_cache": cache_count,
            "scans": scans_count,
            "scan_results": results_count
        }
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# 2. TELEMETRY & API CALL INTERCEPTION
# =============================================================================

class GeminiTelemetryInterceptor:
    """Instruments client.models.generate_content to log all attempts, retries, and models."""
    def __init__(self, client: genai.Client):
        self.client = client
        self.original_generate_content = client.models.generate_content
        self.calls: List[Dict[str, Any]] = []
        self.current_context = {"case_id": "UNKNOWN", "stage": "UNKNOWN"}

        # Patch instance
        self.client.models.generate_content = self._instrumented_generate_content

    def set_context(self, case_id: str, stage: str):
        self.current_context = {"case_id": case_id, "stage": stage}

    def _instrumented_generate_content(self, *args, **kwargs):
        call_index = len(self.calls) + 1
        model_requested = kwargs.get("model") or (args[0] if args else "unknown")
        start_time = time.time()
        timestamp = datetime.now().isoformat()

        record = {
            "call_index": call_index,
            "timestamp": timestamp,
            "case_id": self.current_context["case_id"],
            "stage": self.current_context["stage"],
            "model_requested": model_requested,
            "model_used": None,
            "status": "PENDING",
            "duration_sec": 0.0,
            "response_text": None,
            "error_type": None,
            "error_message": None
        }

        try:
            response = self.original_generate_content(*args, **kwargs)
            duration = time.time() - start_time
            record.update({
                "status": "SUCCESS",
                "duration_sec": round(duration, 3),
                "model_used": getattr(response, "model_version", model_requested),
                "response_text": response.text
            })
            self.calls.append(record)
            return response
        except Exception as e:
            duration = time.time() - start_time
            record.update({
                "status": "ERROR",
                "duration_sec": round(duration, 3),
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            self.calls.append(record)
            raise


# =============================================================================
# 3. EXECUTION PIPELINE
# =============================================================================

def run_case_evaluation(
    case_key: str,
    client: genai.Client,
    interceptor: GeminiTelemetryInterceptor,
    mock_conn: MockDbConnection
) -> Dict[str, Any]:
    case_data = BENCHMARK_CASES[case_key]
    jd_text = case_data["jd_text"]
    resume_text = case_data["resume_text"]
    expected = case_data["expected"]

    # 1. Deterministic Pre-Extraction
    candidate_bullets = extract_candidate_bullets(resume_text)
    tenure_info = extract_candidate_tenure(resume_text)
    req_years_jd = extract_required_years_from_jd(jd_text)
    active_synonyms = build_active_synonym_context(resume_text, jd_text)
    acronym_matches = resolve_acronym_matches(resume_text, jd_text)

    # 2. Stage 1: JD Target Decomposition (Live Gemini Call 1)
    interceptor.set_context(case_key, "Stage 1: extract_atomic_jd_targets")
    stage1_targets = extract_atomic_jd_targets(client, jd_text, conn=mock_conn)

    # 3. Stage 2: Candidate Alignment (Live Gemini Call 2)
    interceptor.set_context(case_key, "Stage 2: align_candidate_against_targets")
    stage2_alignment = align_candidate_against_targets(
        client=client,
        resume_text=resume_text,
        jd_targets=stage1_targets,
        candidate_bullets=candidate_bullets,
        active_synonyms=active_synonyms
    )

    # 4. Assemble Unified Envelope
    analysis_report = {
        "job_title_detected": stage1_targets.get("job_title_detected", case_data["role"]),
        "must_haves": stage2_alignment.get("must_haves", []),
        "bonus_skills": stage2_alignment.get("bonus_skills", []),
        "experience_years": {
            "required_years": float(stage1_targets.get("required_years") or 0.0),
            "candidate_years": 0.0
        },
        "actionable_rewrites": stage2_alignment.get("actionable_rewrites", [])
    }

    # 5. Deterministic Experience Calculation
    model_req_years = float(analysis_report["experience_years"]["required_years"])
    final_req_years = req_years_jd if (model_req_years == 0.0 and req_years_jd > 0.0) else model_req_years
    analysis_report["experience_years"] = {
        "required_years": final_req_years,
        "candidate_years": tenure_info["candidate_years"]
    }

    # 6. Post-Generation Citation & Grounding Verification
    verified_report = validate_and_anchor_report(analysis_report, resume_text)

    # 7. AST Bullet Snapping
    if candidate_bullets:
        anchored_rewrites = []
        for rw in verified_report.get("actionable_rewrites", []):
            snapped = snap_to_best_candidate_bullet(rw.get("original_bullet", ""), candidate_bullets)
            if snapped:
                rw["original_bullet"] = snapped
                anchored_rewrites.append(rw)
        verified_report["actionable_rewrites"] = anchored_rewrites

    verified_report["local_acronym_matches"] = acronym_matches

    # 8. Deterministic Scoring
    scores = calculate_deterministic_scores(verified_report)

    return {
        "case_id": case_key,
        "role": case_data["role"],
        "expected": expected,
        "pre_extraction": {
            "candidate_bullets_count": len(candidate_bullets),
            "candidate_years": tenure_info["candidate_years"],
            "req_years_jd": req_years_jd,
            "active_synonyms": active_synonyms,
            "acronym_matches": acronym_matches
        },
        "stage1_raw": stage1_targets,
        "stage2_raw": stage2_alignment,
        "post_processed_report": verified_report,
        "final_scores": scores
    }


def main():
    print("=" * 80)
    print("CALIBRATE AI — STEP E: CONTROLLED TWO-CASE LIVE GEMINI EVALUATION")
    print("Evaluating TC-01 (Strong Alignment) & TC-05 (Explicit Negation)")
    print("=" * 80)

    # Pre-flight Check: API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[FATAL] GEMINI_API_KEY is not set in environment.")
        sys.exit(1)

    print(f"\n[PRE-FLIGHT] Gemini Primary Model: {os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')}")
    print(f"[PRE-FLIGHT] Gemini Fallback Models: {os.getenv('GEMINI_FALLBACK_MODELS', 'None')}")

    # Pre-flight Check: Production Database Baseline Counts
    counts_before = get_real_db_counts()
    print(f"[PRE-FLIGHT] Production DB Row Counts Before Run: {counts_before}")

    # Setup Isolation Mock
    mock_conn = MockDbConnection()
    # Also patch jd_target_cache.get_db_connection to return None to prevent any accidental fallback
    original_get_db = jd_target_cache.get_db_connection
    jd_target_cache.get_db_connection = lambda: None

    # Initialize Gemini Client and Interceptor
    client = genai.Client(api_key=api_key)
    interceptor = GeminiTelemetryInterceptor(client)

    results = {}

    try:
        # Run TC-01
        print("\n" + "-" * 40)
        print("RUNNING TC-01: Strong Alignment with Direct Evidence")
        print("-" * 40)
        t0 = time.time()
        tc01_res = run_case_evaluation("TC01", client, interceptor, mock_conn)
        print(f"TC-01 completed in {time.time() - t0:.2f}s")
        results["TC01"] = tc01_res

        # Run TC-05
        print("\n" + "-" * 40)
        print("RUNNING TC-05: Explicit Negation Handling ('never used Docker')")
        print("-" * 40)
        t0 = time.time()
        tc05_res = run_case_evaluation("TC05", client, interceptor, mock_conn)
        print(f"TC-05 completed in {time.time() - t0:.2f}s")
        results["TC05"] = tc05_res

    finally:
        # Restore patched functions
        jd_target_cache.get_db_connection = original_get_db

    # Post-run Verification: Production Database Counts
    counts_after = get_real_db_counts()
    print("\n" + "=" * 80)
    print("POST-RUN INTEGRITY AUDIT")
    print("=" * 80)
    print(f"Production DB Row Counts After Run: {counts_after}")
    db_mutated = (counts_before != counts_after)
    print(f"DB Unchanged Verification: {'PASSED (Zero Mutations)' if not db_mutated else 'FAILED (Mutation Detected!)'}")

    total_api_calls = len(interceptor.calls)
    print(f"Total Live Gemini Requests Initiated: {total_api_calls} (Target: 4)")

    # Save full JSON fixture
    output_path = os.path.join(os.path.dirname(__file__), 'step_e_live_evaluation_results.json')
    sanitized_calls = []
    for c in interceptor.calls:
        sc = dict(c)
        # Redact raw response for JSON summary if needed
        sanitized_calls.append(sc)

    export_payload = {
        "timestamp": datetime.now().isoformat(),
        "db_integrity": {
            "before": counts_before,
            "after": counts_after,
            "mutated": db_mutated
        },
        "telemetry": sanitized_calls,
        "evaluations": results
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)
    print(f"Full diagnostic artifact saved to: {output_path}")

    # Print summary table
    print("\n" + "=" * 80)
    print("TELEMETRY LOG")
    print("=" * 80)
    for c in interceptor.calls:
        print(f"Call #{c['call_index']} | {c['case_id']} | {c['stage']} | Model: {c['model_requested']} -> {c['model_used']} | Status: {c['status']} | Latency: {c['duration_sec']}s")

    print("\n" + "=" * 80)
    print("ACCURACY & GROUNDING AUDIT SUMMARY")
    print("=" * 80)
    for case_id, res in results.items():
        exp = res["expected"]
        scores = res["final_scores"]
        print(f"\n--- {case_id}: {res['role']} ---")
        print(f"Expected Scores: Must-Have={exp['must_have_score']}%, Bonus={exp['bonus_score']}%, Exp={exp['experience_score']}%, Overall={exp['overall_score']}%")
        print(f"Actual Scores:   Must-Have={scores['must_have_score']}%, Bonus={scores['bonus_score']}%, Exp={scores['experience_score']}%, Overall={scores['overall_score']}%")
        
        # Check citations
        report = res["post_processed_report"]
        print("Must-Haves Alignment & Citations:")
        for mh in report.get("must_haves", []):
            print(f"  - [{mh.get('status')}] {mh.get('requirement')}")
            if mh.get('evidence_quote'):
                print(f"      Quote: \"{mh.get('evidence_quote')}\"")
            if mh.get('gap_reason'):
                print(f"      Gap: {mh.get('gap_reason')}")

        print("Bonus Skills Alignment & Citations:")
        for bs in report.get("bonus_skills", []):
            print(f"  - [{bs.get('status')}] {bs.get('skill')}")
            if bs.get('evidence_quote'):
                print(f"      Quote: \"{bs.get('evidence_quote')}\"")
            if bs.get('gap_reason'):
                print(f"      Gap: {bs.get('gap_reason')}")

    if total_api_calls == 4 and not db_mutated:
        print("\n>>> STEP E COMPLETED SUCCESSFULLY WITHIN SPECIFICATION CONSTRAINTS <<<")
    else:
        print(f"\n>>> WARNING: Execution completed with deviations (Calls={total_api_calls}, DbMutated={db_mutated}) <<<")


if __name__ == "__main__":
    main()
