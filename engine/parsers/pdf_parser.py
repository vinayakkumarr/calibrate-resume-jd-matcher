import os
import sys

# Ensure UTF-8 output encoding across Windows PowerShell and Unix
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import pdfplumber


# Ensure engine directory is in sys.path for direct imports
engine_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if engine_dir not in sys.path:
    sys.path.insert(0, engine_dir)

from cleaner import clean_and_normalize_text

def extract_layout_aware_text(pdf_path: str) -> dict:
    """
    Extracts text blocks using bounding-box spatial sorting (layout=True).
    Detects scanned or image-only PDFs via word count threshold (<50 words).
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")

    extracted_pages = []
    total_words = 0
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                raise ValueError("PDF has 0 pages.")

            for page in pdf.pages:
                # layout=True sorts words by vertical (top) then horizontal (x0) coordinates
                text = page.extract_text(layout=True)
                if text:
                    cleaned_page = clean_and_normalize_text(text)
                    if cleaned_page:
                        extracted_pages.append(cleaned_page)
                        total_words += len(cleaned_page.split())
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"PDF extraction error: {str(e)}")

    full_text = "\n\n".join(extracted_pages).strip()
    
    # Reject scanned or image-only PDFs that lack machine-readable text
    if total_words < 50:
        raise ValueError("PDF contains no readable text. Scanned or image-only PDFs are not supported.")
        
    return {
        "text": full_text,
        "word_count": total_words,
        "page_count": len(extracted_pages)
    }

if __name__ == "__main__":
    import json
    if len(sys.argv) > 1:
        pdf_file = None
        as_json = False
        for arg in sys.argv[1:]:
            if arg == "--json":
                as_json = True
            elif not pdf_file and not arg.startswith("--"):
                pdf_file = arg

        if not pdf_file:
            sys.stderr.write("Usage: python pdf_parser.py <pdf_path> [--json]\n")
            sys.exit(1)

        try:
            result = extract_layout_aware_text(pdf_file)
            if as_json:
                print(json.dumps(result, ensure_ascii=False))
            else:
                print(result["text"])
        except Exception as e:
            sys.stderr.write(f"Extraction Error: {str(e)}\n")
            sys.exit(1)
    else:
        sys.stderr.write("Usage: python pdf_parser.py <pdf_path> [--json]\n")
        sys.exit(1)
