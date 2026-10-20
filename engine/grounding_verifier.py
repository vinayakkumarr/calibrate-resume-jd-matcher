import re
from rapidfuzz import fuzz



def verify_and_anchor_citation(quote: str, resume_text: str, technical_keyword: str = "") -> tuple[bool, str]:
    """
    Verifies that a claimed LLM citation actually exists in the candidate's resume text.
    Returns (is_verified, authentic_resume_line).
    If unverified, returns (False, "").
    """
    if not quote or not resume_text:
        return False, ""

    clean_quote = quote.strip()
    quote_lower = clean_quote.lower()
    resume_lower = resume_text.lower()

    # Negation guard: if quote expresses lack of experience, reject as affirmative proof
    negation_patterns = [r'\bnever\b', r'\bno\s+prior\b', r'\bnot\s+familiar\b', r'\bzero\s+experience\b', r'\bhave\s+not\b', r'\bhaven\'?t\b', r'\blacks?\b']
    if any(re.search(p, quote_lower) for p in negation_patterns):
        return False, ""

    # Aspirational guard: if quote expresses future learning intent or wishlist, reject as affirmative proof
    aspirational_quote_patterns = [
        r'\b(?:eager|want|wants|wishing|wish|plans?|planning|aiming|aims|hope|hoping)\s+to\s+learn\b',
        r'\b(?:learning\s+goals?|learning\s+objectives?)\b',
        r'\b(?:future\s+goals?|future\s+aspirations?)\b',
        r'^\s*[-•*]?\s*(?:learn|study|explore)\s+[a-z0-9#\+\.\s]+(?:\b|$)'
    ]
    if any(re.search(p, quote_lower) for p in aspirational_quote_patterns):
        return False, ""

    # 1. Exact Substring Check
    if quote_lower in resume_lower:
        for line in resume_text.splitlines():
            if quote_lower in line.lower():
                line_clean = line.strip()
                if not any(re.search(p, line_clean.lower()) for p in negation_patterns) and not any(re.search(p, line_clean.lower()) for p in aspirational_quote_patterns):
                    return True, line_clean
                return False, ""
        return True, clean_quote

    # 2. Line-Level High-Precision Fuzzy Matching
    lines = [line.strip() for line in resume_text.splitlines() if len(line.strip()) > 5]
    best_line = ""
    best_score = 0.0

    for line in lines:
        line_lower = line.lower()
        score = fuzz.token_set_ratio(quote_lower, line_lower)
        partial = fuzz.partial_ratio(quote_lower, line_lower)
        combined = max(score, partial)

        if combined > best_score:
            best_score = combined
            best_line = line

    # Strict threshold: Must reach >= 75.0 similarity and not be a negation or aspirational line
    if best_score >= 75.0 and best_line:
        if not any(re.search(p, best_line.lower()) for p in negation_patterns) and not any(re.search(p, best_line.lower()) for p in aspirational_quote_patterns):
            return True, best_line

    return False, ""


ASPIRATIONAL_GAP_PATTERNS = [
    r'\blacks?\s+hands-on\s+deployed\s+project\b',
    r'\blisted\s+under\s+currently\s+learning\b',
    r'\blearning\s+goals?\b',
    r'\baspirational\b',
    r'\bfuture\s+interests?\b',
    r'\bplans?\s+to\s+learn\b',
    r'\beager\s+to\s+learn\b'
]


def validate_and_anchor_report(analysis_report: dict, resume_text: str) -> dict:
    """
    Verifies every citation against verbatim resume text.
    Demotes ungrounded claims to WEAK with an explicit unverified citation reason.
    Demotes aspirational learning goals without demonstrated projects to MISSING.
    """
    if not analysis_report or not resume_text:
        return analysis_report

    # 1. Audit Must-Haves
    for item in analysis_report.get("must_haves", []):
        status = item.get("status", "MISSING")
        quote = item.get("evidence_quote", "")
        req = item.get("requirement", "")
        gap = item.get("gap_reason", "")

        if status == "MATCHED":
            verified, anchored_quote = verify_and_anchor_citation(quote, resume_text, req)
            if verified:
                item["evidence_quote"] = anchored_quote
            else:
                is_aspirational = any(re.search(p, quote.lower()) for p in [
                    r'\b(?:eager|want|wish|plan|aim|hope)\s+to\s+learn\b',
                    r'\blearning\s+goals?\b',
                    r'\bcurrently\s+learning\b'
                ]) if quote else False
                if is_aspirational:
                    item["status"] = "MISSING"
                    item["evidence_quote"] = ""
                    item["gap_reason"] = f"Aspirational Learning Goal: '{req}' is listed as a future learning objective without demonstrated project implementation or coursework."
                else:
                    item["status"] = "WEAK"
                    item["evidence_quote"] = ""
                    item["gap_reason"] = f"Unverified Citation: Claimed proficiency in '{req}' could not be grounded in verbatim resume text."
        elif status == "WEAK":
            if any(re.search(p, gap, re.IGNORECASE) for p in ASPIRATIONAL_GAP_PATTERNS):
                item["status"] = "MISSING"
                item["evidence_quote"] = ""
                item["gap_reason"] = f"Aspirational Learning Goal: '{req}' is listed as a future learning objective or interest without demonstrated project implementation or coursework."
            elif quote:
                verified, anchored_quote = verify_and_anchor_citation(quote, resume_text, req)
                if verified:
                    item["evidence_quote"] = anchored_quote
                else:
                    item["evidence_quote"] = ""

    # 2. Audit Bonus Skills
    for item in analysis_report.get("bonus_skills", []):
        status = item.get("status", "MISSING")
        quote = item.get("evidence_quote", "")
        skill = item.get("skill", "")
        gap = item.get("gap_reason", "")

        if status == "MATCHED":
            verified, anchored_quote = verify_and_anchor_citation(quote, resume_text, skill)
            if verified:
                item["evidence_quote"] = anchored_quote
            else:
                is_aspirational = any(re.search(p, quote.lower()) for p in [
                    r'\b(?:eager|want|wish|plan|aim|hope)\s+to\s+learn\b',
                    r'\blearning\s+goals?\b',
                    r'\bcurrently\s+learning\b'
                ]) if quote else False
                if is_aspirational:
                    item["status"] = "MISSING"
                    item["evidence_quote"] = ""
                    item["gap_reason"] = f"Aspirational Learning Goal: Bonus skill '{skill}' is listed as a future learning objective without demonstrated project implementation."
                else:
                    item["status"] = "WEAK"
                    item["evidence_quote"] = ""
                    item["gap_reason"] = f"Unverified Citation: Bonus skill '{skill}' could not be grounded in verbatim resume text."
        elif status == "WEAK":
            if any(re.search(p, gap, re.IGNORECASE) for p in ASPIRATIONAL_GAP_PATTERNS):
                item["status"] = "MISSING"
                item["evidence_quote"] = ""
                item["gap_reason"] = f"Aspirational Learning Goal: Bonus skill '{skill}' is listed as a future learning objective or interest without demonstrated project implementation."
            elif quote:
                verified, anchored_quote = verify_and_anchor_citation(quote, resume_text, skill)
                if verified:
                    item["evidence_quote"] = anchored_quote
                else:
                    item["evidence_quote"] = ""

    # 3. Audit Actionable Rewrites for metric grounding
    if "actionable_rewrites" in analysis_report:
        analysis_report["actionable_rewrites"] = validate_and_anchor_rewrites(
            analysis_report.get("actionable_rewrites", []),
            resume_text
        )

    return analysis_report


# Technical identifiers and standard versions that must not be treated as numeric achievement claims
TECH_IDENTIFIERS_PATTERN = re.compile(
    r'\b(?:python\s*[23](?:\.\d+)?|es[56]|es20\d{2}|html5|css3|[123]nf|bcnf|s3|ec2|ebs|eks|gke|rds|'
    r'i2c|spi|uart|oauth\s*2(?:\.0)?|soc\s*[12]|iso\s*\d+|tls\s*1\.[23]|http/[123]|'
    r'arm(?:64|v\d+)?|x(?:86|64)|ipv[46]|p(?:50|90|95|99))\b',
    re.IGNORECASE
)

NUMERIC_CLAIM_PATTERN = re.compile(
    r'(\b\d+(?:\.\d+)?%|\b\d+(?:\.\d+)?\s*[kmbt]\b|\b\d+(?:\.\d+)?\s*(?:million|billion|k|m|ms|s|seconds?|minutes?|hours?|days?|users?|queries|reqs?|requests?|transactions?)\b|\b\d+(?:\.\d+)?\b)',
    re.IGNORECASE
)


ENTITY_UNITS = {
    'microservice': 'service', 'service': 'service',
    'user': 'user', 'query': 'query', 'querie': 'query', 'queries': 'query',
    'request': 'request', 'req': 'request',
    'transaction': 'transaction',
    'day': 'day', 'hour': 'hour', 'minute': 'minute',
    'month': 'month', 'year': 'year',
    'second': 'second', 'sec': 'second', 'ms': 'ms',
    'ticket': 'ticket', 'project': 'project',
    'server': 'server', 'instance': 'instance', 'host': 'instance',
    'endpoint': 'endpoint', 'table': 'table',
    'record': 'record', 'row': 'record', 'event': 'event', 'message': 'message',
    'pipeline': 'pipeline', 'dataset': 'dataset',
    'cluster': 'cluster', 'node': 'node', 'pod': 'pod', 'container': 'container',
    'core': 'core', 'vcpu': 'core', 'cpu': 'core',
    'vulnerability': 'vulnerability', 'vulnerabilitie': 'vulnerability', 'vulnerabilities': 'vulnerability',
    'alert': 'alert', 'incident': 'incident',
    'defect': 'defect', 'bug': 'defect', 'test': 'test'
}

def _get_metric_unit(text: str, num_str: str) -> str:
    m_attached = re.search(r'\b' + re.escape(num_str) + r'([a-z%]+)', text, re.IGNORECASE)
    if m_attached:
        s = m_attached.group(1).lower().rstrip('s')
        if s in ('m', 'million'): return 'million'
        if s in ('k', 'thousand'): return 'thousand'
        if s in ('b', 'billion'): return 'billion'
        if s in ('%', 'percent'): return 'percent'
        if s in ('ms', 'millisecond'): return 'ms'
        if s in ('s', 'sec', 'second'): return 'second'
        if s in ENTITY_UNITS: return ENTITY_UNITS[s]

    m_after = re.search(r'\b' + re.escape(num_str) + r'\b(?:\s+[\w-]+){0,4}', text, re.IGNORECASE)
    if m_after:
        for tok in re.findall(r'[a-zA-Z%]+', m_after.group(0).lower()):
            if tok in ('%', 'percent'): return 'percent'
            if tok in ('m', 'million'): return 'million'
            if tok in ('k', 'thousand'): return 'thousand'
            if tok in ('b', 'billion'): return 'billion'
            t = tok.rstrip('s')
            if t in ENTITY_UNITS:
                return ENTITY_UNITS[t]
    return None

def verify_metric_claim_grounding(claim_text: str, orig_bullet: str, full_rewrite_lower: str = "") -> bool:
    """
    Verifies that a numeric achievement claim in a rewrite is grounded in the specific original bullet.
    Requires matching numeric value AND compatible unit/context.
    Rejects incompatible units (e.g. 30 days -> 30 requests, 5 tickets -> 5 microservices).
    """
    if not orig_bullet or not claim_text:
        return False

    orig_lower = orig_bullet.lower()
    claim_clean = claim_text.strip().lower()
    digits = re.search(r'\d+(?:\.\d+)?', claim_clean)
    if not digits:
        return False
    num_str = digits.group(0)

    # Number must exist in original bullet (either standalone or attached with scale like 8M)
    if not re.search(r'\b' + re.escape(num_str) + r'(?:[a-z%]+)?\b', orig_lower):
        return False

    # Extract unit/metric context in rewrite
    unit_rewrite = _get_metric_unit(claim_clean, num_str)
    if not unit_rewrite and full_rewrite_lower:
        unit_rewrite = _get_metric_unit(full_rewrite_lower, num_str)

    # Extract unit/metric context in source bullet
    unit_source = _get_metric_unit(orig_lower, num_str)

    # Incompatible unit check:
    if unit_rewrite and unit_source:
        return unit_rewrite == unit_source
    if unit_rewrite and not unit_source:
        return False
    if unit_source and not unit_rewrite:
        return False

    return True


def validate_and_anchor_rewrites(actionable_rewrites: list, resume_text: str = "") -> list:
    """
    Validates numeric achievement claims in rewrites against original candidate bullets.
    Replaces ungrounded claims with [ENTER YOUR VERIFIED METRIC] placeholders,
    preserves authentic source metrics, and provides verification metadata.
    """
    if not actionable_rewrites:
        return []

    validated_rewrites = []
    neutral_placeholder = "[ENTER YOUR VERIFIED METRIC]"

    for rw in actionable_rewrites:
        bullet = rw.get("upgraded_xyz_bullet", "")
        original_bullet = rw.get("original_bullet", "")

        # If original_bullet is missing, all numeric claims are unverified
        if not original_bullet:
            tech_masks = []
            def mask_tech_unanchored(match):
                idx = len(tech_masks)
                tech_masks.append(match.group(0))
                return f"__TECH_ID_{idx}__"

            masked = TECH_IDENTIFIERS_PATTERN.sub(mask_tech_unanchored, bullet)
            masked = re.sub(r'\[.*?\]', neutral_placeholder, masked)
            matches = list(NUMERIC_CLAIM_PATTERN.finditer(masked))
            res_text = masked
            for m in sorted(matches, key=lambda x: x.start(), reverse=True):
                res_text = res_text[:m.start()] + neutral_placeholder + res_text[m.end():]
            res_text = re.sub(r'(\[ENTER YOUR VERIFIED METRIC\](?:\s*,?\s*|\s+))+', '[ENTER YOUR VERIFIED METRIC] ', res_text).strip()
            for idx, orig_val in enumerate(tech_masks):
                res_text = res_text.replace(f"__TECH_ID_{idx}__", orig_val)

            rw["upgraded_xyz_bullet"] = res_text
            rw["metrics_grounded"] = False
            rw["unverified_metrics"] = ["(missing original bullet source evidence)"]
            rw["verified_metrics"] = []
            rw["requires_candidate_verification"] = True
            validated_rewrites.append(rw)
            continue

        # 1. Unbracket non-metric text that LLM may have wrapped (e.g. [uptime monitoring dashboards])
        cleaned_bullet = bullet
        for bracketed in re.findall(r'\[(.*?)\]', bullet):
            if not re.search(r'\d', bracketed) and not bracketed.startswith("ENTER YOUR VERIFIED METRIC"):
                cleaned_bullet = cleaned_bullet.replace(f"[{bracketed}]", bracketed)

        # 2. Mask technical identifiers
        tech_masks = []
        def mask_tech(match):
            idx = len(tech_masks)
            tech_masks.append(match.group(0))
            return f"__TECH_ID_{idx}__"

        masked_bullet = TECH_IDENTIFIERS_PATTERN.sub(mask_tech, cleaned_bullet)
        masked_lower = masked_bullet.lower()

        # 3. Detect and classify numeric claims
        matches = list(NUMERIC_CLAIM_PATTERN.finditer(masked_bullet))
        unverified_metrics = []
        verified_metrics = []
        replacements = []

        for m in matches:
            claim = m.group(0)
            is_grounded = verify_metric_claim_grounding(claim, original_bullet, full_rewrite_lower=masked_lower)
            if is_grounded:
                verified_metrics.append(claim)
            else:
                unverified_metrics.append(claim)
                replacements.append((m.start(), m.end(), neutral_placeholder))

        # Apply ungrounded replacements from right to left
        res_text = masked_bullet
        for start, end, placeholder in sorted(replacements, key=lambda x: x[0], reverse=True):
            res_text = res_text[:start] + placeholder + res_text[end:]

        # 4. Unmask technical identifiers
        for idx, orig_val in enumerate(tech_masks):
            res_text = res_text.replace(f"__TECH_ID_{idx}__", orig_val)

        rw["upgraded_xyz_bullet"] = res_text
        rw["metrics_grounded"] = (len(unverified_metrics) == 0)
        rw["unverified_metrics"] = unverified_metrics
        rw["verified_metrics"] = verified_metrics
        rw["requires_candidate_verification"] = (len(unverified_metrics) > 0 or bool(re.search(r'\[.*?\]', res_text)))
        validated_rewrites.append(rw)

    return validated_rewrites
