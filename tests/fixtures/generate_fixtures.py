import os

def create_pdf(filename: str, lines: list):
    stream_content = "BT\n/F1 12 Tf\n72 720 Td\n"
    for i, line in enumerate(lines):
        safe_line = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        if i == 0:
            stream_content += f"({safe_line}) Tj\n"
        else:
            stream_content += f"0 -18 Td\n({safe_line}) Tj\n"
    stream_content += "ET\n"
    
    stream_bytes = stream_content.encode('latin1')
    length = len(stream_bytes)

    header = b"%PDF-1.4\n"
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    obj4_head = f"4 0 obj\n<< /Length {length} >>\nstream\n".encode('latin1')
    obj4_foot = b"\nendstream\nendobj\n"
    obj4 = obj4_head + stream_bytes + obj4_foot
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

    o1 = len(header)
    o2 = o1 + len(obj1)
    o3 = o2 + len(obj2)
    o4 = o3 + len(obj3)
    o5 = o4 + len(obj4)
    xref_offset = o5 + len(obj5)

    xref = f"xref\n0 6\n0000000000 65535 f \n{o1:010d} 00000 n \n{o2:010d} 00000 n \n{o3:010d} 00000 n \n{o4:010d} 00000 n \n{o5:010d} 00000 n \n".encode('latin1')
    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode('latin1')

    pdf_bytes = header + obj1 + obj2 + obj3 + obj4 + obj5 + xref + trailer

    with open(filename, 'wb') as f:
        f.write(pdf_bytes)

def generate_all_fixtures():
    fixtures_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(fixtures_dir, exist_ok=True)

    # 1. Low text PDF (<50 words threshold)
    low_text_lines = [
        "Jane Doe Graphic Designer",
        "Creative portfolio link only.",
        "Scanned visual artwork and illustrations."
    ]
    low_text_path = os.path.join(fixtures_dir, "low_text_resume.pdf")
    create_pdf(low_text_path, low_text_lines)
    print(f"Generated fixture: {low_text_path}")

    # 2. Scanned image Canva PDF (rasterized photo stub with <10 words)
    scanned_lines = [
        "SCANNED_CANVA_IMAGE_ONLY",
        "[No selectable text stream present]"
    ]
    scanned_path = os.path.join(fixtures_dir, "scanned_image_resume.pdf")
    create_pdf(scanned_path, scanned_lines)
    print(f"Generated fixture: {scanned_path}")

    # 3. Valid technical resume (>60 words)
    valid_tech_lines = [
        "Alex Rivera - Senior Software Engineer",
        "Professional Summary: Senior Backend Developer with 5 years of professional experience in software engineering.",
        "Core Competencies: Python, FastAPI, MySQL, Redis, Docker, Kubernetes, AWS, Git, CI/CD pipelines.",
        "Experience: Lead Backend Engineer at CloudScale Solutions from 2021 to 2026.",
        "Architected and deployed 15 microservices using Python and FastAPI, handling 10 million daily requests.",
        "Optimized MySQL relational database indexing and query plans, reducing p95 latency from 450ms to 85ms.",
        "Containerized core infrastructure with Docker and orchestrated deployment clusters on AWS Kubernetes.",
        "Integrated Redis caching layer for session management and rate limiting across distributed APIs.",
        "Education: Bachelor of Science in Computer Science, University of Technology, 2021."
    ]
    valid_tech_path = os.path.join(fixtures_dir, "valid_tech_resume.pdf")
    create_pdf(valid_tech_path, valid_tech_lines)
    print(f"Generated fixture: {valid_tech_path}")

    # 4. Valid target JD (>60 words)
    valid_jd_lines = [
        "Senior Backend Engineer - Cloud Infrastructure Team",
        "Job Summary: Seeking a Senior Backend Engineer to design scalable cloud services and database systems.",
        "Required Qualifications: 5+ years building backend web services with Python, Go, or PHP.",
        "Deep expertise in relational database indexing, schema migrations, and query tuning in MySQL or PostgreSQL.",
        "Hands-on experience with Docker containerization, Kubernetes orchestration, and AWS or GCP cloud architecture.",
        "Experience building high-throughput RESTful APIs, asynchronous message queues, and caching strategies with Redis.",
        "Education: BS in Computer Science, Software Engineering, or equivalent industry experience."
    ]
    valid_jd_path = os.path.join(fixtures_dir, "valid_tech_jd.pdf")
    create_pdf(valid_jd_path, valid_jd_lines)
    print(f"Generated fixture: {valid_jd_path}")

if __name__ == "__main__":
    generate_all_fixtures()
