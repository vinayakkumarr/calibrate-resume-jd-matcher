import os

def calculate_deterministic_scores(extracted_data: dict) -> dict:
    """
    Computes transparent, reproducible mathematical scores with essential-skill gating.
    
    Scoring Formula:
      raw_score = (w_must * must_have_score) + (w_exp * experience_score) + (w_bonus * bonus_score)
    
    Essential-Skill Deal-Breaker Rule:
      - Core Must-Haves are non-negotiable hiring gates.
      - If must_have_score == 0.0%: overall_score is 0.0% (deal-breaker).
      - If must_have_score < 50.0%: overall_score is throttled by gate multiplier (must_have_score / 50.0),
        preventing peripheral bonus skills from inflating an unqualified profile.
      - If must_have_score >= 50.0%: full raw weighted score applies.

    Guards against division-by-zero when required years = 0 or bonus skills = 0.
    """
    if not extracted_data:
        extracted_data = {}
    must_haves = extracted_data.get("must_haves") or []
    bonus_skills = extracted_data.get("bonus_skills") or []
    exp_data = extracted_data.get("experience_years") or {}

    # 1. Must-Haves Score (Core Requirements)
    total_must = len(must_haves)
    if total_must > 0:
        matched_points = sum(
            1.0 if item.get("status") == "MATCHED" else 0.5 if item.get("status") == "WEAK" else 0.0
            for item in must_haves
        )
        must_have_score = round((matched_points / total_must) * 100.0, 2)
    else:
        must_have_score = 100.0

    # 2. Bonus Skills Score (Preferred / Nice-to-Have)
    total_bonus = len(bonus_skills)
    if total_bonus > 0:
        bonus_points = sum(
            1.0 if item.get("status") == "MATCHED" else 0.5 if item.get("status") == "WEAK" else 0.0
            for item in bonus_skills
        )
        bonus_score = round((bonus_points / total_bonus) * 100.0, 2)
        bonus_excluded = False
    else:
        # Exclude bonus component and renormalize active weights across remaining criteria.
        # Prevents awarding unearned 100% credit when bonus skills are missing or not specified.
        bonus_excluded = True
        bonus_score = None

    # 3. Experience Score (Deterministic Tenure Ratio & Tri-State Integrity)
    req_years = exp_data.get("required_years")
    cand_years = float(exp_data.get("candidate_years") or 0.0)
    req_status = exp_data.get("requirement_status")

    # Backward compatibility: infer status if missing (e.g. legacy cached payloads)
    if req_status is None:
        if req_years is not None and not isinstance(req_years, bool) and float(req_years) > 0:
            req_status = "SPECIFIED"
        else:
            req_status = "NOT_SPECIFIED"

    experience_excluded = False
    if req_status == "SPECIFIED":
        req_years_val = float(req_years)
        experience_score = min(100.0, round((cand_years / req_years_val) * 100.0, 2))
    elif req_status in ("NOT_SPECIFIED", "EXTRACTION_FAILED"):
        # Exclude experience tenure component and renormalize active weights across Must-Haves and Bonus.
        # Prevents awarding unearned 100% credit when experience is missing or unparseable.
        experience_excluded = True
        experience_score = None
    else:
        experience_excluded = True
        experience_score = None

    # 4. Overall Weighted Score (Configurable Rubric Weights)
    w_must = float(os.getenv("WEIGHT_MUST_HAVE", "0.50"))
    w_exp = float(os.getenv("WEIGHT_EXPERIENCE", "0.25"))
    w_bonus = float(os.getenv("WEIGHT_BONUS", "0.25"))

    # Dynamic Weight Renormalization across active non-excluded criteria
    active_components = [(w_must, must_have_score)]
    if not experience_excluded and experience_score is not None:
        active_components.append((w_exp, experience_score))
    if not bonus_excluded and bonus_score is not None:
        active_components.append((w_bonus, bonus_score))

    active_weight_sum = sum(weight for weight, _ in active_components)
    if active_weight_sum > 0:
        raw_score = sum((weight / active_weight_sum) * score for weight, score in active_components)
    else:
        raw_score = must_have_score

    # 5. Essential-Skill Non-Linear Gating Rule
    gate_threshold = float(os.getenv("ESSENTIAL_SKILL_GATE_THRESHOLD", "50.0"))
    min_gate_multiplier = float(os.getenv("MIN_GATE_MULTIPLIER", "0.15"))

    if must_have_score == 0.0:
        gate_multiplier = 0.0
    elif must_have_score < gate_threshold:
        gate_multiplier = max(min_gate_multiplier, round(must_have_score / gate_threshold, 4))
    else:
        gate_multiplier = 1.0

    overall_score = round(raw_score * gate_multiplier, 2)
    is_gated = bool(gate_multiplier < 1.0 and must_have_score < gate_threshold)

    # Defensive boundary clamping for database constraint compliance (0.00 - 100.00)
    def clamp(val):
        if val is None:
            return None
        return max(0.00, min(100.00, float(val)))

    return {
        "overall_score": clamp(overall_score),
        "raw_score": clamp(round(raw_score, 2)),
        "is_gated": is_gated,
        "gate_multiplier": gate_multiplier,
        "gate_threshold": gate_threshold,
        "must_have_score": clamp(must_have_score),
        "bonus_score": clamp(bonus_score),
        "bonus_excluded": bonus_excluded,
        "experience_score": clamp(experience_score),
        "experience_excluded": experience_excluded,
        "requirement_status": req_status
    }
