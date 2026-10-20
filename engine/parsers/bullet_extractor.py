import re
from rapidfuzz import fuzz



BULLET_PREFIX_REGEX = re.compile(
    r'^[\s\t]*([•\*\-\–\—⋄\u2022\u25cf\u25cb\u25c7\u25c6]|\d+[\.\)])\s+',
    re.UNICODE
)

ACTION_VERB_REGEX = re.compile(
    r'\b(built|architected|developed|engineered|designed|implemented|optimized|created|integrated|'
    r'spearheaded|maintained|refactored|automated|deployed|configured|migrated|authored|led|collaborated|'
    r'analyzed|modeled|queried|benchmarked|audited|monitored|investigated|patched|provisioned|resolved|'
    r'tested|validated|administered|orchestrated|secured|hardened)\b',
    re.IGNORECASE
)

def extract_candidate_bullets(resume_text: str) -> list[str]:
    """
    Extracts authentic candidate achievement bullets and substantive project lines
    directly from parsed resume text. Guarantees that actionable rewrites anchor
    to verbatim candidate sentences.
    """
    if not resume_text:
        return []

    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    candidate_bullets = []
    seen = set()

    for line in lines:
        cleaned_line = BULLET_PREFIX_REGEX.sub('', line).strip()
        
        # Strip header markers or noise
        if len(cleaned_line) < 25:
            continue
            
        # Check if line looks like a resume bullet (prefixed or starts with action verb)
        is_prefixed = bool(BULLET_PREFIX_REGEX.match(line))
        has_action_verb = bool(ACTION_VERB_REGEX.search(cleaned_line[:40]))
        has_engineering_content = any(kw in cleaned_line.lower() for kw in (
            'using', 'with', 'schema', 'api', 'app', 'platform', 'database', 'queries',
            'algorithm', 'system', 'interface', 'code', 'data', 'pipeline', 'dashboard',
            'metric', 'cloud', 'cluster', 'security', 'vulnerability', 'infrastructure',
            'server', 'test', 'report', 'model', 'warehouse', 'network', 'endpoint',
            'directory', 'policy', 'incident', 'etl'
        ))

        if (is_prefixed or has_action_verb or has_engineering_content) and not cleaned_line.startswith(('EDUCATION', 'SKILLS', 'PROJECTS', 'EXPERIENCE', 'LANGUAGES', 'CERTIFICATIONS')):
            norm = cleaned_line.lower()
            if norm not in seen:
                seen.add(norm)
                candidate_bullets.append(cleaned_line)

    return candidate_bullets


def snap_to_best_candidate_bullet(query_bullet: str, candidate_bullets: list[str]) -> str:
    """
    Given a query bullet (e.g. proposed by an LLM), snaps it to the best matching
    authentic candidate bullet using fuzzy similarity. Never returns a fabricated bullet.
    """
    if not candidate_bullets:
        return query_bullet.strip()

    query_clean = BULLET_PREFIX_REGEX.sub('', query_bullet).strip().lower()
    
    # 1. Exact match check
    for cand in candidate_bullets:
        cand_clean = BULLET_PREFIX_REGEX.sub('', cand).strip().lower()
        if query_clean == cand_clean or query_clean in cand_clean or cand_clean in query_clean:
            return cand

    # 2. Fuzzy ratio check
    best_score = -1.0
    best_bullet = candidate_bullets[0]

    for cand in candidate_bullets:
        cand_clean = BULLET_PREFIX_REGEX.sub('', cand).strip().lower()
        score = fuzz.token_sort_ratio(query_clean, cand_clean)
        if score > best_score:
            best_score = score
            best_bullet = cand

    # If fuzzy match is acceptable (>= 45%), use the matched candidate bullet
    if best_score >= 45.0:
        return best_bullet

    # If completely ungrounded, return empty string so caller can reject fabricated rewrite
    return ""
