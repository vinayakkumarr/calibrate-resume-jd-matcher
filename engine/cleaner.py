import ftfy
import unicodedata

def clean_and_normalize_text(raw_text: str) -> str:
    """
    Fixes broken typography, mojibake, decomposes ligatures, and cleans whitespace.
    Ensures consistent text layout for coordinate parsing and AI analysis.
    """
    if not raw_text:
        return ""
    
    # 1. Fix broken encoding / mojibake via ftfy
    text = ftfy.fix_text(raw_text)
    
    # 2. Decompose typographic ligatures (e.g., '\ufb01' (fi) -> 'f' + 'i')
    text = unicodedata.normalize('NFKD', text)
    
    # 3. Strip non-printable control characters except standard whitespace
    text = "".join(ch for ch in text if ch.isprintable() or ch in ('\n', '\r', '\t'))
    
    # 4. Standardize whitespace
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()
