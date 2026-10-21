"""
Content-addressable cache for parsed job description targets.
Decouples job description decomposition from candidate evaluation and caches
extracted requirements using SHA-256 content hashes to avoid redundant LLM calls.
"""

import os
import re
import json
import hashlib
import sys
import math
from typing import Optional, Dict, Any
import mysql.connector



# Authoritative model default shared across entire application
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"

def get_configured_gemini_model() -> str:
    """Returns the authoritative configured Gemini model from .env or shared default."""
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)


# Legacy 6 domains preserved for 100% backward compatibility with existing cached entries
LEGACY_DOMAINS = frozenset({
    "Languages & Frameworks",
    "Database & Systems Architecture",
    "Computer Science Fundamentals",
    "Developer Tooling & Collaboration",
    "DevOps, Cloud & Modern Stack",
    "Competitive Proof & Credentials"
})

# Canonical 9 universal technical domains covering all levels (Freshers to Staff/Architects & Engineering Leadership)
CANONICAL_9_DOMAINS = frozenset({
    "Languages & Frameworks",
    "Computer Science Fundamentals & System Design",
    "Databases, Data Platforms & Storage",
    "AI, Machine Learning & Analytics",
    "Cloud, Infrastructure & DevOps",
    "Cybersecurity, Identity & IT Operations",
    "Quality Engineering, Tooling & Workflows",
    "Technical Leadership, Strategy & Delivery",
    "Education, Certifications & Professional Proof"
})

# Standard technical domains matching prompt schema and frontend contracts
VALID_DOMAINS = frozenset(CANONICAL_9_DOMAINS | LEGACY_DOMAINS)


def validate_jd_targets_schema(payload: Any) -> bool:
    """
    Validates complete structure and field types against downstream schema contracts.
    Rejects booleans for numeric fields (bool is subclass of int in Python).
    Rejects non-finite numbers (NaN, inf) for required_years.
    Safely rejects unhashable/non-string domain types without raising TypeError.
    Permits legitimate edge cases (e.g. 0 must-haves if bonus skills exist),
    while strictly rejecting total-empty criteria extractions.
    """
    try:
        if not isinstance(payload, dict):
            return False

        job_title = payload.get("job_title_detected")
        if not isinstance(job_title, str) or not job_title.strip() or isinstance(job_title, bool):
            return False

        must_haves = payload.get("must_haves")
        bonus_skills = payload.get("bonus_skills")
        if not isinstance(must_haves, list) or not isinstance(bonus_skills, list):
            return False

        # Total criteria guard: A valid JD extraction must produce at least 1 technical criterion
        if len(must_haves) == 0 and len(bonus_skills) == 0:
            return False

        for item in must_haves:
            if not isinstance(item, dict):
                return False
            req = item.get("requirement")
            dom = item.get("domain")
            if not isinstance(req, str) or not req.strip() or isinstance(req, bool):
                return False
            if not isinstance(dom, str) or dom not in VALID_DOMAINS:
                return False

        for item in bonus_skills:
            if not isinstance(item, dict):
                return False
            skill = item.get("skill") or item.get("requirement")
            dom = item.get("domain")
            if not isinstance(skill, str) or not skill.strip() or isinstance(skill, bool):
                return False
            if not isinstance(dom, str) or dom not in VALID_DOMAINS:
                return False

        req_years = payload.get("required_years")
        if req_years is None:
            req_years = 0.0
        # Explicit bool rejection (bool is subclass of int) and reject non-finite numbers (NaN, inf)
        if (
            isinstance(req_years, bool)
            or not isinstance(req_years, (int, float))
            or not math.isfinite(req_years)
            or req_years < 0
        ):
            return False

        return True
    except Exception:
        return False


def get_db_connection():
    """Returns an isolated database connection using environment variables."""
    try:
        conn_kwargs = {
            "host": os.getenv("DB_HOST", "127.0.0.1"),
            "port": int(os.getenv("DB_PORT", 3306)),
            "database": os.getenv("DB_NAME", "jd_analyser"),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASS", ""),
            "autocommit": True
        }
        if os.getenv("DB_SSL", "false").lower() in ("true", "1", "yes"):
            ca_path = os.getenv("DB_SSL_CA", "/etc/ssl/certs/ca-certificates.crt")
            if os.path.exists(ca_path):
                conn_kwargs["ssl_ca"] = ca_path
            else:
                conn_kwargs["ssl_disabled"] = False
        return mysql.connector.connect(**conn_kwargs)
    except Exception as db_err:
        sys.stderr.write(f"[JD_CACHE_NOTICE] Database connection unavailable for cache: {str(db_err)}\n")
        return None


def compute_jd_cache_key(
    jd_text: str,
    prompt_version: Optional[str] = None,
    model_name: Optional[str] = None
) -> str:
    """
    Computes a deterministic SHA-256 cache key from:
    1. Prompt/Schema version (e.g. 'v1.0')
    2. Configured Gemini model identity (e.g. 'gemini-3.5-flash-lite')
    3. Normalized JD text (whitespace runs collapsed, trimmed, lowercased)
    """
    version = prompt_version or os.getenv("STAGE1_PROMPT_VERSION", "v2.0")
    model = model_name or get_configured_gemini_model()
    normalized = re.sub(r'\s+', ' ', (jd_text or "").strip()).lower()
    raw_payload = f"{version}:{model}:{normalized}"
    return hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()


def fetch_cached_jd_targets(jd_hash: str, conn: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves pre-extracted Stage 1 atomic targets from MySQL cache by SHA-256 hash.
    Validates structural schema against downstream contract.
    Treats invalid entries as cache misses and safely purges corrupt rows.
    """
    if not jd_hash:
        return None

    own_conn = False
    active_conn = conn
    if active_conn is None:
        active_conn = get_db_connection()
        own_conn = True

    if active_conn is None:
        return None

    try:
        cursor = active_conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT targets_payload, hit_count FROM jd_target_cache WHERE jd_hash = %s",
            (jd_hash,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Asynchronously record cache hit telemetry
        try:
            cursor.execute(
                "UPDATE jd_target_cache SET hit_count = hit_count + 1 WHERE jd_hash = %s",
                (jd_hash,)
            )
            if not active_conn.autocommit:
                active_conn.commit()
        except Exception:
            pass  # Non-fatal telemetry update

        raw_payload = row.get("targets_payload")
        parsed = None
        if isinstance(raw_payload, str):
            try:
                parsed = json.loads(raw_payload)
            except Exception:
                parsed = None
        elif isinstance(raw_payload, dict):
            parsed = raw_payload

        # Validate structure and field types against downstream contract
        if not validate_jd_targets_schema(parsed):
            sys.stderr.write(f"[JD_CACHE_WARNING] Corrupt payload for {jd_hash}. Invalidating.\n")
            try:
                cursor.execute("DELETE FROM jd_target_cache WHERE jd_hash = %s", (jd_hash,))
                if not active_conn.autocommit:
                    active_conn.commit()
            except Exception as del_err:
                sys.stderr.write(f"[JD_CACHE_NOTICE] Invalidation purge failed: {str(del_err)}\n")
            # Failed deletion must not mask the cache miss; invalid payload is never returned
            return None

        return parsed
    except Exception as err:
        sys.stderr.write(f"[JD_CACHE_WARNING] Failed to read from jd_target_cache: {str(err)}\n")
        return None
    finally:
        if own_conn and active_conn is not None:
            try:
                active_conn.close()
            except Exception:
                pass


def store_cached_jd_targets(
    jd_hash: str,
    targets: Dict[str, Any],
    prompt_version: Optional[str] = None,
    conn: Optional[Any] = None
) -> bool:
    """
    Persists decomposed Stage 1 atomic targets into MySQL jd_target_cache table.
    Ensures payload is valid before inserting.
    """
    if not jd_hash or not targets or not validate_jd_targets_schema(targets):
        return False

    version = prompt_version or os.getenv("STAGE1_PROMPT_VERSION", "v2.0")
    job_title = str(targets.get("job_title_detected") or "Software Engineer")[:255]
    required_years = float(targets.get("required_years") or 0.0)
    payload_json = json.dumps(targets, ensure_ascii=False)

    own_conn = False
    active_conn = conn
    if active_conn is None:
        active_conn = get_db_connection()
        own_conn = True

    if active_conn is None:
        return False

    try:
        cursor = active_conn.cursor()
        query = """
            INSERT INTO jd_target_cache (
                jd_hash, prompt_version, job_title_detected, required_years, targets_payload, hit_count
            ) VALUES (%s, %s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
                targets_payload = VALUES(targets_payload),
                hit_count = hit_count + 1,
                updated_at = CURRENT_TIMESTAMP
        """
        cursor.execute(query, (jd_hash, version, job_title, required_years, payload_json))
        if not active_conn.autocommit:
            active_conn.commit()
        return True
    except Exception as err:
        sys.stderr.write(f"[JD_CACHE_WARNING] Failed to write to jd_target_cache: {str(err)}\n")
        return False
    finally:
        if own_conn and active_conn is not None:
            try:
                active_conn.close()
            except Exception:
                pass
