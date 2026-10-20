"""
PERF-01 Regression & Invariant Test Suite: Stage 1 Content-Addressable JD Cache
Verifies:
1. Whitespace normalization and semantic edit key divergence.
2. Model identity binding (REC-02) and prompt version invalidation.
3. Strict downstream schema validation (REC-01):
   - Type safety (explicit boolean rejection for numbers/strings).
   - Domain validation against the 6 canonical technical domains.
   - Legitimate edge cases (0 must-haves with bonus skills, 0 bonus skills with must-haves).
   - Empty extraction rejection (0 must-haves AND 0 bonus skills).
4. Safe corruption invalidation: corrupt row deletion and fail-safe miss return.
5. End-to-end MySQL storage, payload fidelity, and hit count telemetry.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import json
import hashlib

# Add engine directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'engine')))

from jd_target_cache import (
    compute_jd_cache_key,
    fetch_cached_jd_targets,
    store_cached_jd_targets,
    validate_jd_targets_schema,
    get_configured_gemini_model,
    DEFAULT_GEMINI_MODEL,
    VALID_DOMAINS,
    get_db_connection
)


class TestPerfJdTargetCache(unittest.TestCase):

    def setUp(self):
        self.sample_jd_1 = """
        We are seeking a Full Stack Software Engineer proficient in PHP and React.
        Requirements:
        - 3+ years experience in PHP and MySQL database design.
        - Solid understanding of JavaScript (ES6+) and modern React.
        - Experience with Git version control and RESTful APIs.
        Bonus:
        - Familiarity with Docker and Redis caching.
        """
        self.sample_jd_1_extra_spaces = """
        We are seeking a Full Stack Software Engineer proficient in PHP and React.
        Requirements:
        - 3+ years   experience in PHP   and MySQL database design.
        - Solid understanding of JavaScript (ES6+) and modern React.
        - Experience with Git version control and RESTful APIs.
        Bonus:
        - Familiarity with Docker and Redis caching.
        
        """
        self.sample_jd_modified = """
        We are seeking a Full Stack Software Engineer proficient in Python and Vue.js.
        Requirements:
        - 5+ years experience in Python and PostgreSQL database design.
        - Solid understanding of TypeScript and modern Vue.js.
        - Experience with Git version control and RESTful APIs.
        Bonus:
        - Familiarity with Kubernetes and Redis caching.
        """
        self.valid_targets = {
            "job_title_detected": "Full Stack Software Engineer",
            "required_years": 3.0,
            "must_haves": [
                {"requirement": "PHP Backend Architecture", "domain": "Languages & Frameworks"},
                {"requirement": "MySQL Database Design", "domain": "Database & Systems Architecture"},
                {"requirement": "JavaScript (ES6+) & React", "domain": "Languages & Frameworks"},
                {"requirement": "Git Version Control", "domain": "Developer Tooling & Collaboration"}
            ],
            "bonus_skills": [
                {"skill": "Docker Containerization", "domain": "DevOps, Cloud & Modern Stack"},
                {"skill": "Redis Caching", "domain": "DevOps, Cloud & Modern Stack"}
            ]
        }

    # =========================================================================
    # REC-02: Model & Version Invariant Tests
    # =========================================================================

    def test_01_whitespace_normalization_cache_hit(self):
        """Verifies that incidental whitespace/newlines do not cause false cache misses."""
        hash_1 = compute_jd_cache_key(self.sample_jd_1)
        hash_2 = compute_jd_cache_key(self.sample_jd_1_extra_spaces)
        self.assertEqual(hash_1, hash_2, "Whitespace-normalized JDs must produce identical SHA-256 keys.")

    def test_02_semantic_edit_forces_cache_miss(self):
        """Verifies that any real edit in JD requirements immediately produces a distinct SHA-256 key."""
        hash_orig = compute_jd_cache_key(self.sample_jd_1)
        hash_mod = compute_jd_cache_key(self.sample_jd_modified)
        self.assertNotEqual(hash_orig, hash_mod, "Altered JD text must produce an entirely different cache key.")

    def test_03_prompt_version_bump_invalidates_cache(self):
        """Verifies that changing prompt version salts the key and busts stale schema entries."""
        hash_v1 = compute_jd_cache_key(self.sample_jd_1, prompt_version="v1.0")
        hash_v2 = compute_jd_cache_key(self.sample_jd_1, prompt_version="v2.0")
        self.assertNotEqual(hash_v1, hash_v2, "Prompt version bump must safely invalidate existing cache entries.")

    def test_04_model_identity_invalidates_cache_key(self):
        """REC-02: Verifies that changing configured Gemini model alters the cache key."""
        hash_m1 = compute_jd_cache_key(self.sample_jd_1, model_name="gemini-3.5-flash-lite")
        hash_m2 = compute_jd_cache_key(self.sample_jd_1, model_name="gemini-2.5-flash")
        hash_m3 = compute_jd_cache_key(self.sample_jd_1, model_name="gemini-1.5-pro")
        self.assertNotEqual(hash_m1, hash_m2, "Different model identities must produce distinct cache keys.")
        self.assertNotEqual(hash_m1, hash_m3, "Different model identities must produce distinct cache keys.")

        # Identical model identity must produce exact match
        hash_m1_repeat = compute_jd_cache_key(self.sample_jd_1, model_name="gemini-3.5-flash-lite")
        self.assertEqual(hash_m1, hash_m1_repeat, "Identical model identity must produce identical cache keys.")

    def test_05_authoritative_model_configuration_default(self):
        """Verifies single authoritative model default across module."""
        self.assertEqual(DEFAULT_GEMINI_MODEL, "gemini-3.5-flash-lite")
        self.assertIn("gemini", get_configured_gemini_model().lower())

    # =========================================================================
    # REC-01: Schema Validation & Type Safety Tests
    # =========================================================================

    def test_06_validate_schema_valid_payload(self):
        """REC-01: Valid payload must pass validation."""
        self.assertTrue(validate_jd_targets_schema(self.valid_targets))

    def test_07_validate_schema_rejects_booleans_for_numbers_and_strings(self):
        """REC-01: In Python, bool is a subclass of int. Must reject booleans for numbers and strings."""
        # required_years as True (evaluates to 1 in int check if not guarded)
        bad_years_true = dict(self.valid_targets, required_years=True)
        self.assertFalse(validate_jd_targets_schema(bad_years_true), "Boolean True must not be accepted as required_years.")

        bad_years_false = dict(self.valid_targets, required_years=False)
        self.assertFalse(validate_jd_targets_schema(bad_years_false), "Boolean False must not be accepted as required_years.")

        bad_title_bool = dict(self.valid_targets, job_title_detected=True)
        self.assertFalse(validate_jd_targets_schema(bad_title_bool), "Boolean must not be accepted as job_title_detected.")

    def test_08_validate_schema_missing_and_wrong_types(self):
        """REC-01: Rejects missing required fields, non-dict payloads, and wrong types."""
        self.assertFalse(validate_jd_targets_schema(None))
        self.assertFalse(validate_jd_targets_schema([]))
        self.assertFalse(validate_jd_targets_schema("not a dict"))

        # Missing job_title_detected
        no_title = dict(self.valid_targets, job_title_detected="")
        self.assertFalse(validate_jd_targets_schema(no_title))

        # must_haves not a list
        bad_must = dict(self.valid_targets, must_haves={"not": "a list"})
        self.assertFalse(validate_jd_targets_schema(bad_must))

        # bonus_skills not a list
        bad_bonus = dict(self.valid_targets, bonus_skills="not a list")
        self.assertFalse(validate_jd_targets_schema(bad_bonus))

        # Negative required_years
        negative_years = dict(self.valid_targets, required_years=-2.5)
        self.assertFalse(validate_jd_targets_schema(negative_years))

    def test_09_validate_schema_invalid_domains(self):
        """REC-01: Rejects criteria with domain names outside the 6 canonical domains."""
        bad_domain_must = {
            "job_title_detected": "Engineer",
            "required_years": 1.0,
            "must_haves": [{"requirement": "Coding", "domain": "Nonexistent Magic Domain"}],
            "bonus_skills": []
        }
        self.assertFalse(validate_jd_targets_schema(bad_domain_must))

        bad_domain_bonus = {
            "job_title_detected": "Engineer",
            "required_years": 1.0,
            "must_haves": [{"requirement": "Coding", "domain": "Languages & Frameworks"}],
            "bonus_skills": [{"skill": "Teamwork", "domain": "General Soft Skills"}]
        }
        self.assertFalse(validate_jd_targets_schema(bad_domain_bonus))

    def test_10_validate_schema_legitimate_edge_cases(self):
        """REC-01: Legitimate edge cases must pass; empty extraction must fail."""
        # Case A: 0 must-haves, but non-empty bonus skills (e.g. exploratory research posting)
        zero_must_haves = {
            "job_title_detected": "Exploratory Intern",
            "required_years": 0.0,
            "must_haves": [],
            "bonus_skills": [{"skill": "Python scripting", "domain": "Languages & Frameworks"}]
        }
        self.assertTrue(validate_jd_targets_schema(zero_must_haves), "0 must-haves with bonus skills must be permitted.")

        # Case B: 0 bonus skills, but non-empty must-haves (e.g. strict core-only requirements)
        zero_bonus = {
            "job_title_detected": "Junior Dev",
            "required_years": 0.0,
            "must_haves": [{"requirement": "HTML & CSS", "domain": "Languages & Frameworks"}],
            "bonus_skills": []
        }
        self.assertTrue(validate_jd_targets_schema(zero_bonus), "0 bonus skills with must-haves must be permitted.")

        # Case C: Both must-haves and bonus_skills are empty (empty extraction failure)
        both_empty = {
            "job_title_detected": "Unknown Role",
            "required_years": 0.0,
            "must_haves": [],
            "bonus_skills": []
        }
        self.assertFalse(validate_jd_targets_schema(both_empty), "0 must-haves AND 0 bonus skills must be rejected.")

    # =========================================================================
    # REC-01: Safe Cache Invalidation & Database Lifecycle Tests
    # =========================================================================

    def test_11_corrupt_cache_row_invalidation_and_miss_safety(self):
        """REC-01: Corrupt row in DB triggers automatic deletion and safely returns None (cache miss)."""
        conn = get_db_connection()
        if not conn:
            self.skipTest("Database connection unavailable in local test environment.")

        cache_key = hashlib.sha256(b"corrupt_invalidation_test_key").hexdigest()
        cur = conn.cursor()

        try:
            cur.execute("DELETE FROM jd_target_cache WHERE jd_hash = %s", (cache_key,))
            # Insert valid JSON syntax that violates downstream contract (missing must_haves and bonus_skills)
            cur.execute("""
                INSERT INTO jd_target_cache (jd_hash, prompt_version, job_title_detected, required_years, targets_payload, hit_count)
                VALUES (%s, 'v1.0', 'Corrupt Role', 0.0, '{"unexpected_key": 123}', 1)
            """, (cache_key,))
            conn.commit()

            # Fetch must detect corruption, purge the row, and return None
            fetched = fetch_cached_jd_targets(cache_key, conn=conn)
            self.assertIsNone(fetched, "Corrupt payload must strictly return None (cache miss).")

            # Verify corrupt row was deleted
            cur.execute("SELECT id FROM jd_target_cache WHERE jd_hash = %s", (cache_key,))
            self.assertIsNone(cur.fetchone(), "Corrupt cache row must be safely purged from database.")

        finally:
            cur.execute("DELETE FROM jd_target_cache WHERE jd_hash = %s", (cache_key,))
            conn.commit()
            conn.close()

    def test_12_failed_deletion_does_not_mask_cache_miss(self):
        """REC-01: Even if deletion raises an exception, invalid payload is NEVER returned and cache miss occurs."""
        class MockFailingCursor:
            def execute(self, query, params=None):
                if "SELECT" in query:
                    return None
                elif "DELETE" in query:
                    raise Exception("Simulated disk error during purge")
            def fetchone(self):
                # Return corrupt JSON payload
                return {"targets_payload": '{"corrupted": true}', "hit_count": 1}

        class MockFailingConn:
            def cursor(self, *args, **kwargs):
                return MockFailingCursor()
            @property
            def autocommit(self):
                return True

        failing_conn = MockFailingConn()
        result = fetch_cached_jd_targets("dummy_hash", conn=failing_conn)
        self.assertIsNone(result, "Cache miss (None) must be returned even if purge deletion fails.")

    def test_13_db_storage_and_retrieval_lifecycle(self):
        """Tests end-to-end MySQL storage, payload fidelity, and hit count incrementation."""
        conn = get_db_connection()
        if not conn:
            self.skipTest("Database connection unavailable in local test environment.")

        cache_key = compute_jd_cache_key(self.sample_jd_1, prompt_version="test_v2", model_name="gemini-test-suite")

        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jd_target_cache WHERE jd_hash = %s", (cache_key,))
            conn.commit()

            # Verify initial miss
            self.assertIsNone(fetch_cached_jd_targets(cache_key, conn=conn))

            # Store validated payload
            stored = store_cached_jd_targets(cache_key, self.valid_targets, prompt_version="test_v2", conn=conn)
            self.assertTrue(stored, "store_cached_jd_targets must succeed for valid schema.")

            # Retrieve and verify exact fidelity
            retrieved = fetch_cached_jd_targets(cache_key, conn=conn)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.get("job_title_detected"), "Full Stack Software Engineer")
            self.assertEqual(len(retrieved.get("must_haves")), 4)
            self.assertEqual(len(retrieved.get("bonus_skills")), 2)
            self.assertEqual(retrieved.get("required_years"), 3.0)

            # Hit count incrementation
            cursor.execute("SELECT hit_count FROM jd_target_cache WHERE jd_hash = %s", (cache_key,))
            hit_row = cursor.fetchone()
            self.assertGreaterEqual(hit_row[0], 2, "Hit count must increment on subsequent reads.")

        finally:
            cursor.execute("DELETE FROM jd_target_cache WHERE jd_hash = %s", (cache_key,))
            conn.commit()
            conn.close()

    # =========================================================================
    # Validator Robustness Tests
    # =========================================================================

    def test_14_validator_unhashable_and_non_string_domains(self):
        """Verifies that non-string and unhashable domain values safely fail validation without raising TypeError."""
        unhashable_domains = [
            ["Languages & Frameworks"],  # list
            {"domain": "Languages & Frameworks"},  # dict
            set(["Languages & Frameworks"]),  # set
            None,
            123,
            True,
            False,
        ]
        for bad_dom in unhashable_domains:
            payload_must = {
                "job_title_detected": "Software Engineer",
                "required_years": 2.0,
                "must_haves": [{"requirement": "Python", "domain": bad_dom}],
                "bonus_skills": []
            }
            try:
                res = validate_jd_targets_schema(payload_must)
                self.assertFalse(res, f"Unhashable/non-string domain {bad_dom!r} must return False.")
            except Exception as e:
                self.fail(f"validate_jd_targets_schema raised {type(e).__name__} for domain {bad_dom!r}: {e}")

            payload_bonus = {
                "job_title_detected": "Software Engineer",
                "required_years": 2.0,
                "must_haves": [{"requirement": "Python", "domain": "Languages & Frameworks"}],
                "bonus_skills": [{"skill": "Docker", "domain": bad_dom}]
            }
            try:
                res = validate_jd_targets_schema(payload_bonus)
                self.assertFalse(res, f"Unhashable/non-string bonus domain {bad_dom!r} must return False.")
            except Exception as e:
                self.fail(f"validate_jd_targets_schema raised {type(e).__name__} for bonus domain {bad_dom!r}: {e}")

    def test_15_validator_non_finite_required_years(self):
        """Verifies that non-finite numbers (NaN, inf) are strictly rejected for required_years."""
        non_finite_values = [
            float('nan'),
            float('inf'),
            float('-inf'),
        ]
        for val in non_finite_values:
            payload = dict(self.valid_targets, required_years=val)
            self.assertFalse(
                validate_jd_targets_schema(payload),
                f"Non-finite required_years {val!r} must be strictly rejected."
            )

        # None is treated as 0.0 (unspecified)
        payload_none = dict(self.valid_targets, required_years=None)
        self.assertTrue(
            validate_jd_targets_schema(payload_none),
            "None required_years should default to 0.0 and pass."
        )

        # 0.0 and positive numbers pass
        payload_zero = dict(self.valid_targets, required_years=0.0)
        self.assertTrue(validate_jd_targets_schema(payload_zero))
        payload_pos = dict(self.valid_targets, required_years=5.5)
        self.assertTrue(validate_jd_targets_schema(payload_pos))

    # =========================================================================
    # Fallback-Model Cache Separation & Recovery Tests
    # =========================================================================

    def test_16_fallback_model_cache_separation_and_recovery(self):
        """
        Verifies:
        1. Fallback model execution caches under the fallback model's key, NOT the primary key.
        2. Primary model key remains a cache miss while fallback succeeded.
        3. When primary model is restored, subsequent request executes fresh under primary model
           and stores under primary key.
        """
        from gemini_client import extract_atomic_jd_targets
        conn = get_db_connection()
        if not conn:
            self.skipTest("Database connection unavailable in local test environment.")

        primary_model = "gemini-3.5-flash-lite"
        fallback_model = "gemini-3.1-flash-lite"
        test_jd = "Unique Fallback Test JD: We need an engineer skilled in Go and PostgreSQL."

        primary_key = compute_jd_cache_key(test_jd, model_name=primary_model)
        fallback_key = compute_jd_cache_key(test_jd, model_name=fallback_model)

        cur = conn.cursor()
        try:
            # Purge test keys
            cur.execute("DELETE FROM jd_target_cache WHERE jd_hash IN (%s, %s)", (primary_key, fallback_key))
            conn.commit()

            # Ensure both keys start empty
            self.assertIsNone(fetch_cached_jd_targets(primary_key, conn=conn))
            self.assertIsNone(fetch_cached_jd_targets(fallback_key, conn=conn))

            # Simulate Step 1: Primary fails with 429 quota exhaustion; Fallback succeeds
            fallback_payload = {
                "job_title_detected": "Go Engineer (Fallback Generated)",
                "required_years": 2.0,
                "must_haves": [{"requirement": "Go Programming", "domain": "Languages & Frameworks"}],
                "bonus_skills": [{"skill": "PostgreSQL", "domain": "Database & Systems Architecture"}]
            }

            mock_client = MagicMock()
            def mock_generate_content(model, contents, config):
                if model == primary_model:
                    raise Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for model gemini-3.5-flash-lite")
                mock_resp = MagicMock()
                mock_resp.text = json.dumps(fallback_payload)
                return mock_resp

            mock_client.models.generate_content.side_effect = mock_generate_content

            with patch.dict(os.environ, {
                "GEMINI_MODEL": primary_model,
                "GEMINI_FALLBACK_MODELS": fallback_model,
                "GEMINI_MAX_RETRIES": "1"
            }):
                result = extract_atomic_jd_targets(mock_client, test_jd, conn=conn)

            # Assert caller received the valid payload
            self.assertEqual(result["job_title_detected"], "Go Engineer (Fallback Generated)")

            # CRITICAL ASSERTION: The primary key must NOT be cached!
            cached_primary = fetch_cached_jd_targets(primary_key, conn=conn)
            self.assertIsNone(cached_primary, "Primary model key must NOT contain fallback model output.")

            # The fallback key MUST be cached under its own legitimate identity
            cached_fallback = fetch_cached_jd_targets(fallback_key, conn=conn)
            self.assertIsNotNone(cached_fallback, "Fallback model output must be stored under fallback model key.")
            self.assertEqual(cached_fallback["job_title_detected"], "Go Engineer (Fallback Generated)")

            # Step 2: Primary model recovers (quota restored).
            primary_payload = {
                "job_title_detected": "Go Engineer (Primary Generated)",
                "required_years": 2.0,
                "must_haves": [{"requirement": "Go Programming", "domain": "Languages & Frameworks"}],
                "bonus_skills": [{"skill": "PostgreSQL Architecture", "domain": "Database & Systems Architecture"}]
            }

            mock_client_recovered = MagicMock()
            def mock_generate_primary(model, contents, config):
                mock_resp = MagicMock()
                mock_resp.text = json.dumps(primary_payload)
                return mock_resp

            mock_client_recovered.models.generate_content.side_effect = mock_generate_primary

            with patch.dict(os.environ, {
                "GEMINI_MODEL": primary_model,
                "GEMINI_FALLBACK_MODELS": fallback_model,
                "GEMINI_MAX_RETRIES": "1"
            }):
                recovered_result = extract_atomic_jd_targets(mock_client_recovered, test_jd, conn=conn)

            # Assert primary was queried and returned
            self.assertEqual(recovered_result["job_title_detected"], "Go Engineer (Primary Generated)")

            # Primary key is now populated
            cached_primary_now = fetch_cached_jd_targets(primary_key, conn=conn)
            self.assertIsNotNone(cached_primary_now, "Primary model output must now be cached under primary key.")
            self.assertEqual(cached_primary_now["job_title_detected"], "Go Engineer (Primary Generated)")

            # Subsequent call with primary model should be a warm cache hit (no mock calls)
            mock_client_dummy = MagicMock()
            mock_client_dummy.models.generate_content.side_effect = Exception("Should not be called on warm hit")
            with patch.dict(os.environ, {"GEMINI_MODEL": primary_model}):
                warm_result = extract_atomic_jd_targets(mock_client_dummy, test_jd, conn=conn)
            self.assertEqual(warm_result["job_title_detected"], "Go Engineer (Primary Generated)")

        finally:
            cur.execute("DELETE FROM jd_target_cache WHERE jd_hash IN (%s, %s)", (primary_key, fallback_key))
            conn.commit()
            conn.close()

    def test_17_cold_vs_warm_cache_timing_and_telemetry(self):
        """
        Explicitly demonstrates cold-cache miss followed by warm-cache hit on real MySQL database:
        - Cold run: cache miss, extracts via generator, persists to database, hit_count = 1
        - Warm run: cache hit from database, hit_count = 2, returns identical payload
        """
        from gemini_client import extract_atomic_jd_targets
        conn = get_db_connection()
        if not conn:
            self.skipTest("Database connection unavailable in local test environment.")

        model = "gemini-3.5-flash-lite"
        test_jd = "Telemetry Cold Warm JD: Software Engineer with C++ and Algorithms."
        cache_key = compute_jd_cache_key(test_jd, model_name=model)
        cur = conn.cursor()

        try:
            cur.execute("DELETE FROM jd_target_cache WHERE jd_hash = %s", (cache_key,))
            conn.commit()

            # Ensure cold state
            self.assertIsNone(fetch_cached_jd_targets(cache_key, conn=conn))

            mock_client = MagicMock()
            gen_count = [0]
            def mock_generate(model, contents, config):
                gen_count[0] += 1
                resp = MagicMock()
                resp.text = json.dumps(self.valid_targets)
                return resp
            mock_client.models.generate_content.side_effect = mock_generate

            # Cold Run
            with patch.dict(os.environ, {"GEMINI_MODEL": model}):
                cold_res = extract_atomic_jd_targets(mock_client, test_jd, conn=conn)
            self.assertEqual(gen_count[0], 1, "Cold run must invoke generation.")
            self.assertEqual(cold_res["job_title_detected"], "Full Stack Software Engineer")

            # Check database row hit_count is 1
            cur.execute("SELECT hit_count FROM jd_target_cache WHERE jd_hash = %s", (cache_key,))
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], 1, "Initial store must have hit_count = 1")

            # Warm Run
            with patch.dict(os.environ, {"GEMINI_MODEL": model}):
                warm_res = extract_atomic_jd_targets(mock_client, test_jd, conn=conn)
            self.assertEqual(gen_count[0], 1, "Warm run must NOT invoke generation (cache hit).")
            self.assertEqual(warm_res["job_title_detected"], "Full Stack Software Engineer")

            # Check database row hit_count incremented to 2
            cur.execute("SELECT hit_count FROM jd_target_cache WHERE jd_hash = %s", (cache_key,))
            row2 = cur.fetchone()
            self.assertEqual(row2[0], 2, "Warm hit must increment hit_count to 2.")

        finally:
            cur.execute("DELETE FROM jd_target_cache WHERE jd_hash = %s", (cache_key,))
            conn.commit()
            conn.close()


if __name__ == '__main__':
    print("=== RUNNING PERF-01 JD TARGET CACHE REGRESSION SUITE ===\n")
    unittest.main()
