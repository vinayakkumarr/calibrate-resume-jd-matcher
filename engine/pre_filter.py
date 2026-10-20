import re
from rapidfuzz import fuzz


COMMON_TECH_SYNONYMS = {
    # Core Programming Languages & Runtimes
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "k8s": "kubernetes",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "react": "reactjs",
    "vue": "vuejs",
    "node": "nodejs",
    "docker": "containerization",
    "ci/cd": "continuous integration / github actions",
    "dsa": "data structures & algorithms",
    "os": "operating systems",
    "rdbms": "relational database management system (mysql / postgresql)",

    # Data, Analytics & Machine Learning
    "etl": "extract transform load (etl pipelines)",
    "bi": "business intelligence (bi dashboards / tableau / power bi)",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "dw": "data warehouse (snowflake / bigquery / redshift)",

    # Cloud, SRE, Infrastructure & IT Operations
    "iac": "infrastructure as code (terraform / cloudformation)",
    "sre": "site reliability engineering",
    "ad": "active directory",
    "iam": "identity and access management (iam)",
    "vpn": "virtual private network",
    "dns": "domain name system",

    # Cybersecurity & IT Security
    "siem": "security information and event management (siem)",
    "soc": "security operations center",
    "sso": "single sign-on",
    "mfa": "multi-factor authentication",

    # QA & Software Quality Engineering
    "qa": "quality assurance / software testing",
    "sdlc": "software development life cycle",
    "e2e": "end-to-end testing (cypress / playwright / selenium)"
}

TECH_TAXONOMY_BRIDGES = [
    {"source_terms": ["mysql", "postgresql", "postgres", "sql"], "target_concept": "relational database (rdbms)", "explanation": "Candidate relational SQL experience satisfies relational database requirements."},
    {"source_terms": ["js", "javascript", "es6"], "target_concept": "javascript fundamentals", "explanation": "Candidate JavaScript / JS skills satisfy core JS requirement."},
    {"source_terms": ["react", "react.js", "reactjs"], "target_concept": "react client-side component architecture", "explanation": "Candidate React project work satisfies front-end React requirements."},
    {"source_terms": ["cisco", "networking basics", "networking"], "target_concept": "computer networking (tcp/ip, http, protocols)", "explanation": "Candidate Cisco certification satisfies Computer Networking requirement."},
    {"source_terms": ["github actions", "ci/cd", "continuous integration"], "target_concept": "ci/cd pipelines", "explanation": "Candidate CI/CD workflows satisfy automated pipeline requirements."},
    {"source_terms": ["docker", "container", "dockerfile"], "target_concept": "docker containerization", "explanation": "Candidate container tools satisfy Docker requirements."},
    {"source_terms": ["snowflake", "bigquery", "redshift"], "target_concept": "cloud data warehousing", "explanation": "Candidate cloud warehouse experience satisfies data warehouse requirements."},
    {"source_terms": ["tableau", "power bi", "looker", "metabase"], "target_concept": "business intelligence reporting", "explanation": "Candidate BI tool visualization experience satisfies BI dashboard requirements."},
    {"source_terms": ["datadog", "prometheus", "grafana", "splunk", "dynatrace", "new relic"], "target_concept": "observability and telemetry monitoring", "explanation": "Candidate monitoring and telemetry experience satisfies observability requirements."},
    {"source_terms": ["terraform", "terragrunt", "pulumi", "cloudformation"], "target_concept": "infrastructure as code (iac)", "explanation": "Candidate IaC automation experience satisfies declarative infrastructure requirements."},
    {"source_terms": ["cypress", "selenium", "playwright", "puppeteer", "junit", "pytest"], "target_concept": "automated test suites", "explanation": "Candidate automated testing framework experience satisfies software quality testing requirements."},
    {"source_terms": ["okta", "active directory", "azure ad", "ping identity"], "target_concept": "enterprise identity and access management", "explanation": "Candidate identity management experience satisfies enterprise IAM requirements."}
]

def is_negated_mention(text: str, token: str) -> bool:
    """Checks if a technical token in text is preceded by a negative qualifier."""
    pattern = r'(?:\b(?:never(?:\s+used|\s+worked)?|no(?:\s+prior)?\s+experience(?:\s+in|\s+with)?|not\s+familiar(?:\s+with)?|haven\'?t(?:\s+used)?|zero\s+experience|without|lacks?)\b[^.\n]{0,45})\b' + re.escape(token) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))

def resolve_acronym_matches(resume_text: str, jd_text: str) -> dict:
    """
    Pre-filters high-confidence technical acronym and synonym matches locally
    to anchor ground truth across evaluation stages.
    """
    resume_lower = resume_text.lower()
    jd_lower = jd_text.lower()
    matches = {}
    
    for short, full in COMMON_TECH_SYNONYMS.items():
        short_in_jd = bool(re.search(r'\b' + re.escape(short) + r'\b', jd_lower)) or full in jd_lower
        if short_in_jd:
            token = short if bool(re.search(r'\b' + re.escape(short) + r'\b', resume_lower)) else full if full in resume_lower else None
            if token and not is_negated_mention(resume_lower, token):
                matches[full] = True
                
    return matches


def build_active_synonym_context(resume_text: str, jd_text: str) -> str:
    """
    Constructs an explicit ground-truth prompt envelope connecting candidate resume
    shorthands, acronyms, and technical synonyms to JD requirements while filtering out negated mentions.
    """
    resume_lower = resume_text.lower()
    jd_lower = jd_text.lower()
    context_lines = []

    # 1. Resolve direct acronym matches
    for short, full in COMMON_TECH_SYNONYMS.items():
        short_pattern = r'\b' + re.escape(short) + r'\b'
        has_short_in_resume = bool(re.search(short_pattern, resume_lower))
        has_full_in_resume = full in resume_lower
        has_in_jd = bool(re.search(short_pattern, jd_lower)) or full in jd_lower

        if (has_short_in_resume or has_full_in_resume) and has_in_jd:
            active_token = short if has_short_in_resume else full
            if is_negated_mention(resume_lower, active_token):
                continue
            found_token = short.upper() if has_short_in_resume else full.title()
            context_lines.append(f"• Candidate mentions '{found_token}', which explicitly satisfies '{full.title()}' in the JD.")

    # 2. Resolve taxonomy bridges
    for bridge in TECH_TAXONOMY_BRIDGES:
        valid_terms = [t for t in bridge["source_terms"] if bool(re.search(r'\b' + re.escape(t) + r'\b', resume_lower)) and not is_negated_mention(resume_lower, t)]
        target = bridge["target_concept"]
        has_target_in_jd = any(word in jd_lower for word in target.split() if len(word) > 3)

        if valid_terms and has_target_in_jd:
            context_lines.append(f"• Candidate experience in [{', '.join(valid_terms).upper()}] maps to [{target.title()}]: {bridge['explanation']}")

    if not context_lines:
        return ""

    return "ACTIVE TECHNICAL TAXONOMY & SYNONYM RESOLUTIONS (Grounded Truth):\n" + "\n".join(context_lines)
