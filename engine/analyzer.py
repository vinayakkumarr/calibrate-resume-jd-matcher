import sys
import os
import re
import json
import argparse
import mysql.connector
from dotenv import load_dotenv

# Ensure UTF-8 encoding across Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Load root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Ensure engine path is available for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cleaner import clean_and_normalize_text
from parsers.pdf_parser import extract_layout_aware_text
from parsers.bullet_extractor import extract_candidate_bullets, snap_to_best_candidate_bullet
from parsers.date_parser import extract_required_years_from_jd, extract_candidate_tenure, detect_experience_mention_in_jd
from grounding_verifier import validate_and_anchor_report
from pre_filter import resolve_acronym_matches, build_active_synonym_context
from gemini_client import analyze_with_gemini
from scorer import calculate_deterministic_scores


def get_db_connection():
    conn_kwargs = {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "database": os.getenv("DB_NAME", "jd_analyser"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASS", ""),
        "autocommit": False
    }
    if os.getenv("DB_SSL", "false").lower() in ("true", "1", "yes"):
        ca_path = os.getenv("DB_SSL_CA", "/etc/ssl/certs/ca-certificates.crt")
        if os.path.exists(ca_path):
            conn_kwargs["ssl_ca"] = ca_path
        else:
            conn_kwargs["ssl_disabled"] = False
    return mysql.connector.connect(**conn_kwargs)

def sanitize_pii(text: str) -> str:
    """Scrubs email addresses and phone numbers from error traces to protect candidate privacy."""
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)
    text = re.sub(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}', '[REDACTED_PHONE]', text)
    return text

def sanitize_client_error(err: Exception) -> str:
    """
    Separates internal diagnostic exceptions from user-facing error messages.
    Guarantees that database details, stack traces, and filesystem paths are never
    persisted in client-facing error fields, while preserving actionable validation messages.
    """
    err_str = str(err).strip()
    lower_err = err_str.lower()

    # Known user-actionable error indicators
    user_facing_indicators = [
        "no readable text",
        "scanned or image",
        "too short",
        "not a valid pdf",
        "unsupported",
        "magic-byte",
        "character count"
    ]

    is_user_facing = isinstance(err, ValueError) and any(ind in lower_err for ind in user_facing_indicators)

    if is_user_facing:
        # Strip inadvertent filesystem paths from user-facing errors
        clean_msg = sanitize_pii(err_str)
        clean_msg = re.sub(r'[A-Za-z]:\\[^:\n\r\t]+', '[FILE]', clean_msg)
        clean_msg = re.sub(r'(?:/[a-zA-Z0-9_\.\-]+){2,}', '[FILE]', clean_msg)
        return clean_msg[:250]

    # Handle known API quota and rate-limit exceptions safely
    if any(ind in lower_err for ind in ["resource_exhausted", "429", "quota", "rate limit", "rate-limit"]):
        return "The AI intelligence service is currently experiencing high demand or temporary rate limits. Please try again shortly."

    # All unexpected runtime/system errors (e.g. FileNotFoundError, MySQL errors, OS errors) return generic safe text
    return "An unexpected processing error occurred while analyzing the document. Your inputs were preserved."

def main():
    parser = argparse.ArgumentParser(description="JD Analyser Python Intelligence Core Worker")
    parser.add_argument("--uuid", required=True, help="Scan UUID ticket")
    args = parser.parse_args()

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Fetch Scan Record
        cursor.execute("SELECT id, resume_relative_path, job_description FROM scans WHERE uuid = %s", (args.uuid,))
        scan = cursor.fetchone()
        if not scan:
            sys.stderr.write(f"Worker Error: Scan ticket {args.uuid} not found in database.\n")
            sys.exit(1)

        # 2. Immediate State Transition: pending -> processing
        cursor.execute("UPDATE scans SET status = 'processing', error_message = NULL WHERE id = %s", (scan['id'],))
        conn.commit()

        # 3. Resolve File Path & Parse Layout / Content
        base_storage = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'storage'))
        resume_path = os.path.join(base_storage, scan['resume_relative_path'])
        
        if not os.path.exists(resume_path):
            raise FileNotFoundError(f"Resume file does not exist: {resume_path}")

        MIN_RESUME_CHARS = int(os.environ.get('MIN_RESUME_CHARS', 80))
        if resume_path.lower().endswith(('.txt', '.md')):
            with open(resume_path, 'r', encoding='utf-8', errors='replace') as f:
                raw_text = f.read()
            cleaned_text = clean_and_normalize_text(raw_text)
            total_words = len(cleaned_text.split())
            if len(cleaned_text) < MIN_RESUME_CHARS:
                raise ValueError(f"Resume text is too short. Please provide at least {MIN_RESUME_CHARS} characters of work experience, technical skills, and achievements.")
            parsed_doc = {
                "text": cleaned_text,
                "word_count": total_words,
                "page_count": 1
            }
        else:
            # Check if cached pre-extracted text exists to avoid re-parsing the PDF
            extracted_cache_path = os.path.join(base_storage, 'uploads', f"{args.uuid}.extracted.txt")
            if os.path.exists(extracted_cache_path):
                with open(extracted_cache_path, 'r', encoding='utf-8', errors='replace') as f:
                    cached_raw = f.read()
                cleaned_cached = clean_and_normalize_text(cached_raw)
                total_words = len(cleaned_cached.split())
                if len(cleaned_cached) >= MIN_RESUME_CHARS and total_words >= 5:
                    parsed_doc = {
                        "text": cleaned_cached,
                        "word_count": total_words,
                        "page_count": 1
                    }
                else:
                    parsed_doc = extract_layout_aware_text(resume_path)
            else:
                parsed_doc = extract_layout_aware_text(resume_path)

        raw_text_len = len(parsed_doc["text"])
        MAX_RESUME_CHARS = 25000
        if raw_text_len > MAX_RESUME_CHARS:
            resume_text = parsed_doc["text"][:MAX_RESUME_CHARS]
            scoring_clamped = True
        else:
            resume_text = parsed_doc["text"]
            scoring_clamped = False

        jd_text = scan['job_description']

        # Pre-extract candidate bullets, experience dates, and active technical synonyms
        candidate_bullets = extract_candidate_bullets(resume_text)
        tenure_info = extract_candidate_tenure(resume_text)
        req_years_jd = extract_required_years_from_jd(jd_text)
        exp_mention_detected = detect_experience_mention_in_jd(jd_text)
        active_synonyms = build_active_synonym_context(resume_text, jd_text)
        acronym_matches = resolve_acronym_matches(resume_text, jd_text)

        # Run staged LLM analysis with content caching
        analysis_report = analyze_with_gemini(
            resume_text=resume_text,
            jd_text=jd_text,
            candidate_bullets=candidate_bullets,
            active_synonyms=active_synonyms,
            scoring_clamped=scoring_clamped,
            conn=conn
        )

        # Resolve experience tenure requirement and status
        exp_obj = analysis_report.get("experience_years") or {}
        raw_model_val = exp_obj.get("required_years")
        model_req_years = float(raw_model_val) if (raw_model_val is not None and not isinstance(raw_model_val, bool) and float(raw_model_val) > 0) else 0.0
        final_req_years = req_years_jd if (model_req_years == 0.0 and req_years_jd > 0.0) else model_req_years

        if final_req_years > 0.0:
            req_status = "SPECIFIED"
            audit_note = f"Required experience deterministically verified at {final_req_years} years."
            resolved_req_years = final_req_years
        elif not exp_mention_detected:
            req_status = "NOT_SPECIFIED"
            audit_note = "Job description does not specify a minimum experience tenure. Experience component excluded and remaining criteria renormalized."
            resolved_req_years = 0.0
        else:
            # Experience mention was detected in JD text, but neither Gemini nor parser extracted a positive number
            req_status = "EXTRACTION_FAILED"
            audit_note = "Experience requirement mentioned in job description but could not be reliably extracted. Experience score was excluded from final score to prevent score distortion."
            resolved_req_years = None

        cand_tech_years = tenure_info.get("technical_years", tenure_info["candidate_years"])
        cand_total_wf = tenure_info.get("general_workforce_years", tenure_info["candidate_years"])

        if cand_total_wf > cand_tech_years:
            if cand_tech_years == 0.0:
                dual_note = f"Candidate possesses {cand_total_wf} yrs non-technical workforce tenure with 0.0 yrs relevant technical experience."
            else:
                dual_note = f"Candidate possesses {cand_tech_years} yrs relevant technical experience (out of {cand_total_wf} yrs total workforce experience)."
            audit_note = f"{audit_note} {dual_note}".strip()

        analysis_report["experience_years"] = {
            "required_years": resolved_req_years,
            "candidate_years": cand_tech_years,
            "technical_years": cand_tech_years,
            "general_workforce_years": cand_total_wf,
            "requirement_status": req_status,
            "experience_mention_detected": exp_mention_detected,
            "audit_note": audit_note
        }

        # Verify and anchor citations against verbatim resume text
        analysis_report = validate_and_anchor_report(analysis_report, resume_text)

        # Anchor rewrite suggestions to candidate source bullets
        if candidate_bullets:
            anchored_rewrites = []
            for rw in analysis_report.get("actionable_rewrites", []):
                snapped = snap_to_best_candidate_bullet(rw.get("original_bullet", ""), candidate_bullets)
                if snapped:
                    rw["original_bullet"] = snapped
                    anchored_rewrites.append(rw)
            analysis_report["actionable_rewrites"] = anchored_rewrites

        # Attach pre-filter synonym matches to report payload
        analysis_report["local_acronym_matches"] = acronym_matches

        # Compute mathematical scores with essential-skill gating
        scores = calculate_deterministic_scores(analysis_report)
        analysis_report["scores"] = scores

        # Commit results and mark scan completed in a single transaction
        conn.start_transaction()
        cursor.execute("""
            INSERT INTO scan_results (scan_id, overall_score, must_have_score, bonus_score, experience_score, analysis_payload)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                overall_score = VALUES(overall_score),
                must_have_score = VALUES(must_have_score),
                bonus_score = VALUES(bonus_score),
                experience_score = VALUES(experience_score),
                analysis_payload = VALUES(analysis_payload)
        """, (
            scan['id'],
            scores['overall_score'],
            scores['must_have_score'],
            scores.get('bonus_score') if scores.get('bonus_score') is not None else 0.0,
            scores.get('experience_score') if scores.get('experience_score') is not None else 0.0,
            json.dumps(analysis_report)
        ))
        
        cursor.execute("UPDATE scans SET status = 'completed', error_message = NULL WHERE id = %s", (scan['id'],))
        conn.commit()

        sys.stdout.write(f"Worker Success [{args.uuid}]: Analysis completed. Overall score: {scores['overall_score']}%\n")

    except Exception as e:
        client_error = sanitize_client_error(e)
        diagnostic_error = sanitize_pii(str(e))[:250]
        if conn and conn.is_connected():
            try:
                conn.rollback()
                cursor = conn.cursor()
                cursor.execute("UPDATE scans SET status = 'failed', error_message = %s WHERE uuid = %s", (client_error, args.uuid))
                conn.commit()
            except Exception as db_err:
                sys.stderr.write(f"Failed to record error state in DB: {str(db_err)}\n")
        
        sys.stderr.write(f"Worker Error [{args.uuid}]: {diagnostic_error}\n")
        sys.exit(1)
    finally:
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    main()
