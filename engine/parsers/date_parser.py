import re
from datetime import datetime

def get_current_temporal_reference() -> tuple[int, int]:
    """Dynamically returns (current_year, current_month) to prevent hardcoding temporal anchors."""
    now = datetime.now()
    return now.year, now.month

WORD_TO_NUM = {
    "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
    "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0
}

def _parse_num_or_word(token: str) -> float:
    t = (token or "").strip().lower()
    if t in WORD_TO_NUM:
        return WORD_TO_NUM[t]
    try:
        return float(t)
    except ValueError:
        return 0.0


def detect_experience_mention_in_jd(jd_text: str) -> bool:
    """
    Deterministically detects whether a JD mentions experience or tenure requirements.
    Distinguishes roles that genuinely specify no minimum tenure from roles where extraction failed.
    """
    if not jd_text:
        return False

    lower = jd_text.lower()
    # Mask company history/founding age so they don't count as candidate requirements
    lower_cleaned = re.sub(
        r'\b(?:founded|established|in\s+business|operating)\s+(?:for\s+)?(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*years?\s*(?:ago)?\b',
        '[COMPANY_AGE]',
        lower
    )

    patterns = [
        r'\b(?:minimum\s*(?:of\s*)?|at\s*least\s*|requires?\s*(?:a\s*minimum\s*of\s*)?|experience\s*required|work\s*experience)\b',
        r'\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\+?\s*years?\b',
        r'\byoe\b',
        r'\byears?\s*of\s*(?:[\w-]+\s+){0,4}experience\b',
        r'\bexperience\s*(?:level|expectation|requirement)\b'
    ]
    return any(bool(re.search(p, lower_cleaned)) for p in patterns)


def extract_required_years_from_jd(jd_text: str) -> float:
    """
    Deterministically parses minimum required professional experience years from JD text.
    Handles 'X+ years', 'X-Y years', 'minimum X years', word-numbers ('five years'),
    and entry-level/fresher heuristics while ignoring company founding dates.
    """
    if not jd_text:
        return 0.0

    lower = jd_text.lower()

    # Mask company founding / business age (e.g. "Founded 10 years ago, we require 2 years of experience")
    lower_cleaned = re.sub(
        r'\b(?:founded|established|in\s+business|operating)\s+(?:for\s+)?(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*years?\s*(?:ago)?\b',
        '[COMPANY_AGE]',
        lower
    )

    # Heuristic for entry-level / fresh graduate roles
    if any(k in lower_cleaned for k in ("fresher", "fresh graduate", "entry level", "junior full stack", "internship", "0-1 year", "0 to 1 year")):
        # If explicitly requires 2+ years, prioritize explicit number
        explicit = re.search(r'\b([2-9]|\d{2}|two|three|four|five)\+?\s*years?\b', lower_cleaned)
        if not explicit:
            return 0.0

    num_pattern = r'(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)'

    # Pattern 1: Range "X to Y years/yoe" or "X-Y years/yoe"
    range_match = re.search(r'\b(' + num_pattern + r')\s*(?:-|to)\s*(?:' + num_pattern + r')\s*(?:years?|yoe)\b', lower_cleaned)
    if range_match:
        return _parse_num_or_word(range_match.group(1))

    # Pattern 2: Explicit requirement prefix: "minimum (of) X years/yoe", "at least X years/yoe", "requires X(+) years/yoe"
    min_prefix_match = re.search(r'\b(?:minimum\s*(?:of\s*)?|at\s*least\s*|requires?\s*(?:a\s*minimum\s*of\s*)?)(' + num_pattern + r')\+?\s*(?:years?|yoe)\b', lower_cleaned)
    if min_prefix_match:
        return _parse_num_or_word(min_prefix_match.group(1))

    # Pattern 3: Standalone "X+ years / X+ yoe" (e.g. "3+ years", "5+ years experience", "6+ yoe")
    plus_match = re.search(r'\b(' + num_pattern + r')\+\s*(?:years?|yoe)\b', lower_cleaned)
    if plus_match:
        return _parse_num_or_word(plus_match.group(1))

    # Pattern 4: "X years of ... experience" (accommodates intervening adjectives, e.g. "professional", "industry")
    exp_match = re.search(r'\b(' + num_pattern + r')\s*years?(?:\s*of)?\s*(?:[\w-]+\s+){0,4}experience\b', lower_cleaned)
    if exp_match:
        return _parse_num_or_word(exp_match.group(1))

    # Pattern 5: Standalone "X yoe" (e.g. "requires 5 yoe in python", "needs 4 yoe")
    yoe_match = re.search(r'\b(' + num_pattern + r')\s*yoe\b', lower_cleaned)
    if yoe_match:
        return _parse_num_or_word(yoe_match.group(1))

    return 0.0


NON_TECH_OCCUPATIONS = re.compile(
    r'\b(?:'
    r'cashier|grocery\s+cashier|checkout\s+operator|store\s+clerk|grocery\s+clerk|'
    r'barista|bartender|waiter|waitress|server|busser|host|hostess|food\s+runner|'
    r'cook|chef|line\s+cook|prep\s+cook|dishwasher|kitchen\s+staff|crew\s+member|fast\s+food|'
    r'retail\s+associate|sales\s+associate|store\s+associate|retail\s+sales|retail\s+cashier|retail\s+worker|'
    r'driver|delivery\s+driver|uber\s+driver|lyft\s+driver|courier|truck\s+driver|valet|chauffeur|'
    r'cleaner|janitor|housekeeper|maid|custodian|sanitation\s+worker|'
    r'security\s+guard|bouncer|doorman|guard|'
    r'warehouse\s+worker|warehouse\s+associate|order\s+picker|package\s+handler|forklift\s+operator|stocker|shelf\s+stocker|mover|'
    r'receptionist|front\s+desk|desk\s+clerk|office\s+assistant|clerical\s+assistant|file\s+clerk|'
    r'lifeguard|babysitter|nanny|dog\s+walker|pet\s+sitter|'
    r'hair\s+stylist|barber|esthetician|massage\s+therapist|'
    r'carpenter|plumber|electrician|painter|mechanic|construction\s+worker|laborer'
    r')\b',
    re.IGNORECASE
)

TECH_SUBSTANCE = re.compile(
    r'\b(?:'
    r'software|developer|engineer|programmer|architect|coder|coding|devops|sre|sysadmin|administrator|'
    r'backend|frontend|full\s*stack|api|apis|rest|graphql|microservice|microservices|server|servers|'
    r'cloud|aws|gcp|azure|docker|kubernetes|k8s|terraform|linux|unix|git|ci/cd|pipeline|pipelines|'
    r'python|java|javascript|typescript|c\+\+|c\#|golang|rust|php|html|css|react|angular|vue|node|ruby|swift|kotlin|scala|sql|nosql|mongodb|postgres|mysql|redis|'
    r'database|databases|schema|schemas|query|queries|analytics|analyst|data|etl|bi|tableau|power\s*bi|'
    r'machine\s*learning|deep\s*learning|ai|artificial\s*intelligence|nlp|computer\s*vision|tensorflow|pytorch|'
    r'security|cybersecurity|infosec|cryptography|penetration|firewall|network|networking|tcp/ip|dns|vpn|'
    r'qa|tester|testing|automation|selenium|cypress|playwright|junit|pytest|'
    r'hardware|embedded|firmware|iot|microcontroller|arm|arduino|raspberry\s*pi|'
    r'it\s*support|helpdesk|tech\s*support|system\s*support|desktop\s*support|pos\s*system|pos\s*software'
    r')\b',
    re.IGNORECASE
)

ACADEMIC_TITLES = re.compile(
    r'\b(?:bachelor|master|ph\.?d|b\.?s\.?|m\.?s\.?|b\.?e\.?|b\.?tech|m\.?tech|diploma|associate\s+degree|degree\s+in|university|college|school\s+of)\b',
    re.IGNORECASE
)

WORK_TITLES = re.compile(
    r'\b(?:intern|internship|co-?op|developer|engineer|analyst|specialist|assistant|fellow|researcher|scientist|lead|manager|architect|consultant|programmer|administrator)\b',
    re.IGNORECASE
)


def _is_academic_block(block_text: str) -> bool:
    """Detects whether a date span belongs to academic degrees or education rather than professional employment."""
    if not block_text:
        return False
    return bool(ACADEMIC_TITLES.search(block_text)) and not bool(WORK_TITLES.search(block_text))


def _is_non_technical_job_block(block_text: str) -> bool:
    """
    Deterministically checks if a job block represents non-technical service/labor work
    with zero technical engineering/computing/IT substance.
    A job is classified as non-technical ONLY IF:
    1. It matches non-technical service occupation keywords (cashier, barista, retail clerk, etc.)
    2. AND it contains ZERO technical keywords, tools, or action verbs.
    """
    if not block_text:
        return False
    lower = block_text.lower()
    has_non_tech = bool(NON_TECH_OCCUPATIONS.search(lower))
    if not has_non_tech:
        return False
    has_tech = bool(TECH_SUBSTANCE.search(lower))
    return not has_tech


def _extract_job_block(lines: list[str], target_idx: int, date_re: re.Pattern) -> str:
    """
    Extracts the contextual lines around a date match (job title and bullets)
    without bleeding into previous or subsequent job listings.
    """
    curr_line = lines[target_idx]
    has_text_in_curr = len(re.sub(r'[\s\|\-\–—\(\),]', '', date_re.sub('', curr_line))) > 3

    pre_lines = []
    for k in range(target_idx - 1, max(-1, target_idx - 4), -1):
        line = lines[k].strip()
        if not line:
            if pre_lines:
                break
            continue
        if date_re.search(line):
            break
        if line.startswith(('-', '*', '•', '–', '—', '▪')):
            break
        if re.match(r'^(?:experience|work history|professional experience|employment)\s*:?$', line, re.IGNORECASE):
            break
        pre_lines.insert(0, lines[k])
        if len(pre_lines) >= (1 if has_text_in_curr else 2):
            break

    post_lines = []
    for k in range(target_idx + 1, min(len(lines), target_idx + 9)):
        line = lines[k].strip()
        if not line:
            break
        if date_re.search(line):
            break
        if re.match(r'^(?:experience|work history|education|skills|certifications|projects)\s*:?$', line, re.IGNORECASE):
            break
        post_lines.append(lines[k])

    return '\n'.join(pre_lines + [curr_line] + post_lines)


def extract_candidate_tenure(resume_text: str) -> dict:
    """
    Deterministically extracts academic spans and professional work tenure from resume text.
    Eliminates overlapping concurrent job double-counting via calendar month set-union logic.
    Differentiates relevant technical tenure from non-technical workforce tenure (e.g. cashier vs software dev).
    """
    if not resume_text:
        return {
            "candidate_years": 0.0,
            "technical_years": 0.0,
            "general_workforce_years": 0.0,
            "is_in_progress_degree": False,
            "expected_grad_year": None
        }

    current_year, current_month = get_current_temporal_reference()

    # 1. Detect In-Progress Degree Tenure (e.g. 2023–2027 or 2023 - 2027)
    degree_span = re.search(r'\b(20\d{2})\s*[-–—]\s*(20\d{2})\b', resume_text)
    is_in_progress = False
    expected_grad = None

    if degree_span:
        start_year = int(degree_span.group(1))
        end_year = int(degree_span.group(2))
        if end_year >= current_year:
            is_in_progress = True
            expected_grad = end_year

    # 2. Check for "Present" / "Pursuing" academic markers
    if re.search(r'\b(pursuing|currently\s+enrolled|expected\s+20\d{2})\b', resume_text, re.IGNORECASE):
        is_in_progress = True

    # 3. Detect Explicit Work Experience / Internship spans
    lines = resume_text.splitlines()

    # Named English month pattern (e.g. "Jan 2020 - Present", "March 1998 to Dec 2005")
    month_re = re.compile(
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*((?:19[7-9]\d|20\d{2}))\s*(?:[-–—]|to|until)\s*(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*((?:19[7-9]\d|20\d{2}))|present)\b',
        re.IGNORECASE
    )
    month_map = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

    # Numeric date pattern (e.g. "01/2020 - 12/2022", "5.2018 to Present", "12/1998 - 05/2006")
    num_date_re = re.compile(
        r'\b(0?[1-9]|1[0-2])[\/\.]((?:19[7-9]\d|20\d{2}))\s*(?:[-–—]|to|until)\s*(?:(0?[1-9]|1[0-2])[\/\.]((?:19[7-9]\d|20\d{2}))|present)\b',
        re.IGNORECASE
    )

    technical_months = set()
    all_workforce_months = set()

    def _record_month_interval(start_y: int, start_m: int, end_y: int, end_m: int, is_non_tech: bool):
        # Bound career plausibility: Start year >= 1970, end year <= current, single job span <= 50 years
        if (
            start_y >= 1970
            and end_y <= current_year
            and (end_y > start_y or (end_y == start_y and end_m >= start_m))
            and (end_y - start_y) <= 50
        ):
            curr_y, curr_m = start_y, start_m
            while (curr_y < end_y) or (curr_y == end_y and curr_m <= end_m):
                all_workforce_months.add((curr_y, curr_m))
                if not is_non_tech:
                    technical_months.add((curr_y, curr_m))
                curr_m += 1
                if curr_m > 12:
                    curr_m = 1
                    curr_y += 1

    # Match named months
    for m in month_re.finditer(resume_text):
        target_idx = resume_text[:m.start()].count('\n')
        target_idx = min(target_idx, len(lines) - 1)
        block = _extract_job_block(lines, target_idx, month_re)

        # Ignore pure academic degree spans from employment tenure
        if _is_academic_block(block):
            continue

        is_non_tech = _is_non_technical_job_block(block)

        m1, y1, m2, y2 = m.group(1), m.group(2), m.group(3), m.group(4)
        start_y = int(y1)
        start_m = month_map.get(m1.lower()[:3], 1)
        if y2:
            end_y = int(y2)
            end_m = month_map.get(m2.lower()[:3], 12)
        else:
            end_y = current_year
            end_m = current_month

        _record_month_interval(start_y, start_m, end_y, end_m, is_non_tech)

    # Match numeric dates (slash / dot notation)
    for m in num_date_re.finditer(resume_text):
        target_idx = resume_text[:m.start()].count('\n')
        target_idx = min(target_idx, len(lines) - 1)
        block = _extract_job_block(lines, target_idx, num_date_re)

        if _is_academic_block(block):
            continue

        is_non_tech = _is_non_technical_job_block(block)

        m1, y1, m2, y2 = m.group(1), m.group(2), m.group(3), m.group(4)
        start_y = int(y1)
        start_m = int(m1)
        if y2:
            end_y = int(y2)
            end_m = int(m2)
        else:
            end_y = current_year
            end_m = current_month

        _record_month_interval(start_y, start_m, end_y, end_m, is_non_tech)

    # Fallback for resumes formatted with year-only spans (e.g. "2018 - 2022", "1998 - Present", "2015 to 2020")
    if len(all_workforce_months) == 0:
        year_re = re.compile(r'\b((?:19[7-9]\d|20\d{2}))\s*(?:[-–—]|to|until)\s*(((?:19[7-9]\d|20\d{2}))|present)\b', re.IGNORECASE)
        for m in year_re.finditer(resume_text):
            target_idx = resume_text[:m.start()].count('\n')
            target_idx = min(target_idx, len(lines) - 1)
            block = _extract_job_block(lines, target_idx, year_re)

            if _is_academic_block(block):
                continue

            is_non_tech = _is_non_technical_job_block(block)

            y1_str, y2_str = m.group(1), m.group(2)
            start_y = int(y1_str)
            if y2_str.lower() == 'present':
                end_y = current_year
                end_m = current_month
            else:
                end_y = int(y2_str)
                end_m = 12

            _record_month_interval(start_y, 1, end_y, end_m, is_non_tech)

    candidate_years = round(len(technical_months) / 12.0, 1)
    technical_years = candidate_years
    general_workforce_years = round(len(all_workforce_months) / 12.0, 1)

    # If the candidate is a college student with active projects and hackathons (or 0 detected job dates),
    # clamp baseline to 0.5 - 1.0 year hands-on project tenure for junior matching
    if candidate_years == 0.0 and is_in_progress:
        has_projects = any(k in resume_text.lower() for k in ("project", "hackathon", "algorithm visualizer", "matcher"))
        if has_projects:
            candidate_years = 1.0
            technical_years = 1.0

    return {
        "candidate_years": float(candidate_years),
        "technical_years": float(technical_years),
        "general_workforce_years": float(general_workforce_years),
        "is_in_progress_degree": is_in_progress,
        "expected_grad_year": expected_grad
    }
