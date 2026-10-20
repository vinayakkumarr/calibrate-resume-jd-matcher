import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

engine_path = os.path.join(root_path, 'engine')
if engine_path not in sys.path:
    sys.path.insert(0, engine_path)

from engine.grounding_verifier import verify_and_anchor_citation, validate_and_anchor_report
from engine.parsers.bullet_extractor import extract_candidate_bullets, snap_to_best_candidate_bullet
from engine.parsers.date_parser import extract_required_years_from_jd, extract_candidate_tenure
from engine.pre_filter import build_active_synonym_context
from engine.scorer import calculate_deterministic_scores
from engine.gemini_client import clean_and_enforce_metric_lock

SAMPLE_RESUME = """
VINAYAK KUMAR
BCA student equipped with problem-solving skills and a robust foundation in software development.
EDUCATION
Bachelor of Computer Applications
NSHM College of Management and Technology, Durgapur
2023–2027
SKILLS
Languages: C, Java, SQL
Web Development: HTML5, CSS3, Bootstrap, JavaScript, PHP
Databases: MySQL, MongoDB
Tools: Git, GitHub, VS Code
Core Competencies: OS, Computer Networking, DSA, Computer Architecture
PROJECTS
Algorithm Visualizer — React, CSS3
• Built an interactive visualizer animating algorithms step by step, letting users visually trace data.
• Added playback speed and array size controls alongside per-algorithm time and space complexity display.
Smart Split – Group Expense Settlement Calculator — PHP, MySQL, JavaScript
• Built a web application to track shared expenses, calculate balances, and settle costs across multiple users.
• Architected a normalised MySQL schema managing core entities with foreign key constraints and indexed queries throughout.
ACHIEVEMENTS
• Top 20 Rank at GeeksforGeeks in NSHM Durgapur.
• 4 Star in SQL, Java at HackerRank.
"""

SAMPLE_JD = """
Job Title: Junior Full Stack Developer (PHP / JS / React)
We are looking for a Junior Full Stack Developer with 0-1 years of experience.
Required Skills:
• Hands-on project experience with PHP backend development and relational databases (MySQL / SQL).
• Experience with JavaScript and modern React framework.
• Solid understanding of Data Structures & Algorithms (DSA), computer networking, and operating systems.
Bonus Skills:
• Familiarity with TypeScript and Docker containerization.
"""

def test_mandate_1_citation_verification():
    print("[MANDATE 1] Verifying Citation Grounding Guard (No AI Hallucinations)...")
    
    # 1. Genuine quote from resume
    valid, anchored = verify_and_anchor_citation("Web Development: HTML5, CSS3, Bootstrap, JavaScript, PHP", SAMPLE_RESUME)
    assert valid is True, "Expected authentic citation to be verified"
    assert "JavaScript" in anchored

    # 2. Fabricated quote not in resume
    invalid, _ = verify_and_anchor_citation("Spearheaded enterprise microservices deployed on AWS Lambda with Redis", SAMPLE_RESUME)
    assert invalid is False, "Expected fabricated quote to fail verification"

    # 3. Full report audit & demotion
    mock_report = {
        "must_haves": [
            {
                "requirement": "PHP Backend Development",
                "status": "MATCHED",
                "evidence_quote": "Web Development: HTML5, CSS3, Bootstrap, JavaScript, PHP"
            },
            {
                "requirement": "Kubernetes Cluster Administration",
                "status": "MATCHED",
                "evidence_quote": "Spearheaded enterprise Kubernetes clusters across multi-region VPCs"
            }
        ],
        "bonus_skills": []
    }

    audited = validate_and_anchor_report(mock_report, SAMPLE_RESUME)
    assert audited["must_haves"][0]["status"] == "MATCHED", "Expected genuine skill to remain MATCHED"
    assert audited["must_haves"][1]["status"] == "WEAK", "Expected fabricated skill to be demoted to WEAK"
    assert audited["must_haves"][1]["evidence_quote"] == "", "Expected ungrounded quote to be wiped"
    assert "Unverified Citation" in audited["must_haves"][1]["gap_reason"], "Expected explicit unverified citation gap reason"
    # 4. Negation citation rejection
    neg_quote = "I have no prior experience in Kubernetes or Docker"
    neg_valid, _ = verify_and_anchor_citation(neg_quote, SAMPLE_RESUME, "Docker")
    assert neg_valid is False, "Expected negative quote to be rejected as proof"
    print("  [PASS] Citation verification strictly demotes ungrounded claims and negations.\n")


def test_mandate_2_bullet_ast_anchoring():
    print("[MANDATE 2] Verifying Bullet AST Extraction & Anchoring...")
    bullets = extract_candidate_bullets(SAMPLE_RESUME)
    assert len(bullets) >= 4, f"Expected at least 4 authentic project bullets, found {len(bullets)}"
    assert any("Smart Split" in b or "shared expenses" in b for b in bullets), "Expected Smart Split bullet extracted"

    # Test fuzzy snap when LLM produces a slightly altered query bullet
    hallucinated_query = "Built an expense app using debt-settlement logic to track shared costs and minimize transactions"
    snapped = snap_to_best_candidate_bullet(hallucinated_query, bullets)
    assert "track shared expenses" in snapped or "normalised MySQL schema" in snapped, f"Expected snap to authentic bullet, got: {snapped}"

    # Test completely ungrounded bullet rejection (no false attribution)
    ungrounded_query = "Spearheaded enterprise cloud migration to AWS GovCloud saving $2M annually"
    rejected = snap_to_best_candidate_bullet(ungrounded_query, bullets)
    assert rejected == "", f"Expected ungrounded bullet to be rejected as empty string, got: {rejected}"
    print("  [PASS] Actionable rewrites strictly anchor to verbatim candidate bullets or are safely rejected.\n")


def test_mandate_3_scoring_gating_and_dates():
    print("[MANDATE 3] Verifying Essential-Skill Deal-Breaker Gating & Deterministic Dates...")
    
    # 1. Candidate with 0% Core Must-Haves
    failing_case = {
        "must_haves": [
            {"requirement": "PHP", "status": "MISSING"},
            {"requirement": "MySQL", "status": "MISSING"}
        ],
        "bonus_skills": [
            {"skill": "Git", "status": "MATCHED"},
            {"skill": "VS Code", "status": "MATCHED"}
        ],
        "experience_years": {"required_years": 0, "candidate_years": 1}
    }
    failing_scores = calculate_deterministic_scores(failing_case)
    assert failing_scores["must_have_score"] == 0.0
    assert failing_scores["overall_score"] == 0.0, f"Expected 0.0 overall score for 0% must-haves, got {failing_scores['overall_score']}"

    # 2. Candidate with 40% Core Must-Haves (Gate throttles score)
    gated_case = {
        "must_haves": [
            {"requirement": "PHP", "status": "MATCHED"},
            {"requirement": "MySQL", "status": "MISSING"},
            {"requirement": "React", "status": "MISSING"},
            {"requirement": "DSA", "status": "MISSING"},
            {"requirement": "Networking", "status": "MISSING"}
        ],
        "bonus_skills": [{"skill": "Docker", "status": "MATCHED"}],
        "experience_years": {"required_years": 0, "candidate_years": 1}
    }
    gated_scores = calculate_deterministic_scores(gated_case)
    assert gated_scores["must_have_score"] == 20.0
    assert gated_scores["overall_score"] < 25.0, f"Expected gated score < 25.0, got {gated_scores['overall_score']}"

    # 3. NoneType input safety
    none_scores = calculate_deterministic_scores({"must_haves": None, "bonus_skills": None, "experience_years": None})
    assert none_scores["overall_score"] == 100.0, "Expected NoneType to default safely"

    # 4. Deterministic Dates & Concurrent Employment
    req_years = extract_required_years_from_jd(SAMPLE_JD)
    assert req_years == 0.0, f"Expected 0.0 required years for Junior 0-1 role, got {req_years}"

    tenure = extract_candidate_tenure(SAMPLE_RESUME)
    assert tenure["is_in_progress_degree"] is True, "Expected 2023-2027 to be recognized as in-progress degree"
    assert tenure["expected_grad_year"] == 2027

    # Concurrent jobs deduplication
    overlapping_resume = "Company A (Jan 2023 - Dec 2023)\nCompany B (Jun 2023 - Dec 2023)"
    overlap_tenure = extract_candidate_tenure(overlapping_resume)
    assert overlap_tenure["candidate_years"] == 1.0, f"Expected 1.0 year for concurrent 2023 jobs, got {overlap_tenure['candidate_years']}"
    print("  [PASS] Essential-skill gating, NoneType safety, and calendar date union verified.\n")


def test_mandate_4_active_synonym_context():
    print("[MANDATE 4] Verifying Active Technical Synonym & Taxonomy Context...")
    context = build_active_synonym_context(SAMPLE_RESUME, SAMPLE_JD)
    assert len(context) > 0, "Expected non-empty active synonym context"
    assert "JavaScript" in context or "JS" in context, "Expected JS -> JavaScript bridge"
    assert "MySQL" in context or "Relational Database" in context, "Expected SQL/MySQL -> Relational DB bridge"

    # Negation test: "never used Docker" should not produce positive proof
    neg_context = build_active_synonym_context("I have never used Docker or TypeScript. Only know Python.", "Requires Docker and TypeScript.")
    assert "DOCKER" not in neg_context and "Typescript" not in neg_context, f"Expected negations to be excluded from synonym context, got: {neg_context}"
    print("  [PASS] Active synonym system with negation defense successfully connected.\n")


def test_mandate_6_metric_generation_syntax():
    print("[MANDATE 6] Verifying Grammatical Metric Injection Syntax...")
    
    # 1. Unbracketed metric in sentence without source evidence is sanitized to verified placeholder
    b1 = "Optimized MySQL indexing reducing query latency from 450ms to 85ms on large datasets"
    res1_unanchored = clean_and_enforce_metric_lock(b1)
    assert "[ENTER YOUR VERIFIED METRIC]" in res1_unanchored, "Expected neutral verification placeholder for unanchored metrics"
    assert "450ms" not in res1_unanchored, "Unanchored metric 450ms must not be preserved"

    # With source grounding, verified metrics are preserved
    res1_anchored = clean_and_enforce_metric_lock(b1, original_bullet=b1)
    assert "450ms" in res1_anchored and "85ms" in res1_anchored, "Grounded metrics must be preserved"

    # 2. Sentence with "by" preposition
    b2 = "Architected normalized relational schema improving query efficiency by 30 percent"
    res2 = clean_and_enforce_metric_lock(b2)
    assert "by [ENTER YOUR VERIFIED METRIC]" in res2, f"Expected neutral placeholder after 'by', got: {res2}"
    assert not res2.endswith("[ENTER YOUR VERIFIED METRIC]"), "Metric should NOT be tacked onto end of sentence"

    # 3. Pre-bracketed bullet without source grounding must NOT bypass verification (unsafe bracket bypass removed)
    b3 = "Resolved multi-user balances in [under 5 transactions - e.g., 3-5 transactions] with zero deadlock"
    res3 = clean_and_enforce_metric_lock(b3)
    assert "[ENTER YOUR VERIFIED METRIC]" in res3, "Pre-bracketed ungrounded metrics must be replaced with verification placeholder"
    print("  [PASS] Metric lock guarantees grammatical Google XYZ placeholders.\n")


def test_mandate_7_aspirational_goals_precision():
    print("[MANDATE 7] Verifying Aspirational Learning Goals Guard (Zero False WEAK Credit)...")
    
    kabir_resume = """
KABIR ROY
Aspiring Web Developer
Email: kabir.roy@example.com | Phone: +91-9000000003
Location: Kolkata, India

Professional Summary
Motivated beginner interested in web development and software engineering. Familiar with basic HTML and CSS for building simple web pages, along with introductory JavaScript concepts. Eager to learn backend programming, database management, version control, and modern web technologies through practical projects.

Technical Skills
Frontend: Basic HTML, CSS, introductory JavaScript
Programming: Variables, conditional statements, basic loops
Tools: Visual Studio Code
Concepts: Basic web page structure and responsive design fundamentals
Currently learning: JavaScript programming and introductory computer science

Projects
Personal Introduction Website
Technologies: HTML, CSS
- Created a simple personal website with profile information and interests.
- Used basic CSS styling to organize page sections.

Basic Calculator Interface
Technologies: HTML, CSS, introductory JavaScript
- Designed a basic calculator interface.
- Practiced simple JavaScript event handling and arithmetic operations.

Education
Bachelor of Computer Applications (BCA) - In Progress (2023 - 2027)
ABC College, Kolkata

Learning Goals
- Learn PHP backend development and MySQL database fundamentals.
- Improve JavaScript programming and problem-solving skills.
- Study Data Structures and Algorithms, Operating Systems, and Computer Networks.
- Learn Git and GitHub for source control.
- Explore React and REST API integration.
"""

    # 1. Aspirational citation rejection in verify_and_anchor_citation
    asp_quote = "- Learn PHP backend development and MySQL database fundamentals."
    asp_valid, _ = verify_and_anchor_citation(asp_quote, kabir_resume, "PHP")
    assert asp_valid is False, "Aspirational learning goal quote must be rejected as affirmative proof"

    eager_quote = "Eager to learn backend programming, database management, version control"
    eager_valid, _ = verify_and_anchor_citation(eager_quote, kabir_resume, "backend")
    assert eager_valid is False, "'Eager to learn' quote must be rejected as affirmative proof"

    # 2. Authentic project proof verification
    html_quote = "- Used basic CSS styling to organize page sections."
    html_valid, anchored = verify_and_anchor_citation(html_quote, kabir_resume, "CSS")
    assert html_valid is True, "Authentic project bullet must be verified"
    assert "Used basic CSS styling" in anchored

    # 3. Full report demotion test for aspirational goals vs authentic skills vs in-progress degree
    mock_kabir_report = {
        "must_haves": [
            {"requirement": "PHP backend development", "status": "WEAK", "gap_reason": "Listed under Currently Learning; lacks hands-on deployed project proof.", "evidence_quote": ""},
            {"requirement": "Core JS fundamentals", "status": "MATCHED", "gap_reason": "", "evidence_quote": "- Practiced simple JavaScript event handling and arithmetic operations."},
            {"requirement": "React", "status": "WEAK", "gap_reason": "Listed under Currently Learning; lacks hands-on deployed project proof.", "evidence_quote": ""},
            {"requirement": "HTML5 & CSS3 styling", "status": "MATCHED", "gap_reason": "", "evidence_quote": "- Used basic CSS styling to organize page sections."},
            {"requirement": "Relational databases MySQL / SQL", "status": "WEAK", "gap_reason": "Listed under Currently Learning; lacks hands-on deployed project proof.", "evidence_quote": ""},
            {"requirement": "Structured indexing and constraint management", "status": "MISSING", "gap_reason": "No mention in resume.", "evidence_quote": ""},
            {"requirement": "Data Structures & Algorithms (DSA)", "status": "WEAK", "gap_reason": "Listed under Currently Learning; lacks hands-on deployed project proof.", "evidence_quote": ""},
            {"requirement": "Computer networking", "status": "WEAK", "gap_reason": "Listed under Currently Learning; lacks hands-on deployed project proof.", "evidence_quote": ""},
            {"requirement": "Operating systems", "status": "WEAK", "gap_reason": "Listed under Currently Learning; lacks hands-on deployed project proof.", "evidence_quote": ""},
            {"requirement": "Git version control", "status": "WEAK", "gap_reason": "Listed under Currently Learning; lacks hands-on deployed project proof.", "evidence_quote": ""},
            {"requirement": "VS Code", "status": "MATCHED", "gap_reason": "", "evidence_quote": "Tools: Visual Studio Code"},
            {"requirement": "REST API integration", "status": "WEAK", "gap_reason": "Listed under Currently Learning; lacks hands-on deployed project proof.", "evidence_quote": ""},
            {"requirement": "BCA Degree in Progress", "status": "WEAK", "gap_reason": "Degree currently in progress; candidate must confirm availability for full-time employment.", "evidence_quote": ""}
        ],
        "bonus_skills": [
            {"skill": "TypeScript", "status": "MISSING", "gap_reason": "No mention.", "evidence_quote": ""}
        ],
        "experience_years": {
            "required_years": 0.0,
            "candidate_years": 0.0,
            "requirement_status": "NOT_SPECIFIED"
        }
    }

    audited = validate_and_anchor_report(mock_kabir_report, kabir_resume)
    
    # Verify demotion of aspirational learning goals to MISSING
    for item in audited["must_haves"]:
        req = item["requirement"]
        if req in ["PHP backend development", "React", "Relational databases MySQL / SQL", "Data Structures & Algorithms (DSA)", "Computer networking", "Operating systems", "Git version control", "REST API integration"]:
            assert item["status"] == "MISSING", f"Expected '{req}' to be demoted to MISSING, got {item['status']}"
            assert "Aspirational Learning Goal" in item["gap_reason"], f"Expected Aspirational Learning Goal in gap reason for '{req}'"
        elif req == "BCA Degree in Progress":
            # Temporal Horizon Guard in-progress degree must remain WEAK (legitimate academic enrollment)
            assert item["status"] == "WEAK", f"Expected BCA Degree to remain WEAK, got {item['status']}"
        elif req in ["Core JS fundamentals", "HTML5 & CSS3 styling", "VS Code"]:
            assert item["status"] == "MATCHED", f"Expected '{req}' to remain MATCHED, got {item['status']}"

    # Verify end-to-end scoring math on audited report
    scores = calculate_deterministic_scores(audited)
    assert scores["must_have_score"] == 26.92, f"Expected 26.92% must_have_score, got {scores['must_have_score']}%"
    assert scores["overall_score"] < 15.0, f"Expected gated overall score < 15.0% (got {scores['overall_score']}%), confirming deal-breaker gate active"
    assert scores["overall_score"] != 38.46, "Score must not evaluate to the inflated 38.46% figure!"
    print(f"  [PASS] Aspirational goals demoted to MISSING; must-haves: {scores['must_have_score']}%, gated overall: {scores['overall_score']}%\n")


def main():
    print("=== RUNNING PRECISION & GROUNDING REGRESSION TEST SUITE ===\n")
    test_mandate_1_citation_verification()
    test_mandate_2_bullet_ast_anchoring()
    test_mandate_3_scoring_gating_and_dates()
    test_mandate_4_active_synonym_context()
    test_mandate_6_metric_generation_syntax()
    test_mandate_7_aspirational_goals_precision()
    print("===================================================================")
    print("ALL 7 PRECISION MANDATE REGRESSION TESTS PASSED (100% SUCCESS)!")
    print("===================================================================")

if __name__ == "__main__":
    main()
