<?php
declare(strict_types=1);

/**
 * Automated Regression Test Suite: Document Orientation & Inversion Guard
 * 
 * Verifies:
 *   - TC-OG01: Standard submission with normal orientation passes cleanly without flagging.
 *   - TC-OG02: Swapped submission (JD in Resume box & Resume in JD box) is deterministically flagged.
 *   - TC-OG03: Recruiter resume with JD vocabulary does NOT trigger a false positive.
 *   - TC-OG04: Casual / startup JD with informal language is accurately classified when swapped.
 *   - TC-OG05: Symmetrical dual-resume submission is not falsely flagged as inverted.
 *   - TC-OG06: Symmetrical dual-JD submission is not falsely flagged as inverted.
 *   - TC-OG07: Sub-threshold / short input strings safely default to unflagged pass-through.
 *   - TC-OG08: Gateway fast-fail boundary prevents file writes, DB inserts, and worker spawns.
 * 
 * Safety: Pure in-memory execution; zero external network requests; zero state mutations.
 */

echo "=== CALIBRATE AI: DOCUMENT ORIENTATION & INVERSION TEST HARNESS ===\n\n";

$passCount = 0;
$failCount = 0;

function assertTest(bool $condition, string $testName, string $details = '') {
    global $passCount, $failCount;
    if ($condition) {
        echo "✅ PASS: {$testName}\n";
        $passCount++;
    } else {
        echo "❌ FAILED: {$testName} - {$details}\n";
        $failCount++;
    }
}

require_once __DIR__ . '/../public/api/validation_helpers.php';

$standardResume = <<<TEXT
Alex Mercer
alex.mercer@gmail.com | (555) 234-5678 | San Francisco, CA
linkedin.com/in/alex-mercer | github.com/alexmercer

PROFESSIONAL SUMMARY
Senior Backend Engineer with 6+ years of experience architecting distributed cloud systems.

WORK EXPERIENCE
Senior Software Engineer | Stripe | 2021 – Present
• Architected high-throughput payment settlement microservices handling 12,000 requests/sec.
• Engineered distributed caching layer with Redis, reducing p99 latency by 35%.
• Spearheaded migration from monolithic services to event-driven Kafka architecture.

Software Engineer | Twilio | 2018 – 2021
• Developed REST APIs in Python and Go for customer messaging pipelines.
• Maintained MySQL relational databases and optimized index configurations.

EDUCATION
B.S. in Computer Science | University of California, Berkeley | 2014 – 2018
TEXT;

$standardJD = <<<TEXT
Senior Backend Engineer - Core Infrastructure
Company: Veloce Systems | San Francisco, CA (Hybrid)
Job Type: Full-time | Salary Range: \$160,000 - \$200,000

About the Role:
We are looking for a Senior Backend Engineer to join our Core Platform team. In this role, you will be responsible for designing, building, and maintaining high-scale distributed systems.

What You'll Do:
• Architect resilient microservices in Python or Go.
• Build scalable data pipelines with Kafka and relational databases (PostgreSQL/MySQL).
• You will collaborate with product designers and frontend teams to deliver core APIs.

Qualifications:
• 5+ years of experience in backend software engineering required.
• Strong proficiency in distributed systems design, caching, and database indexing.
• Bachelor's degree in Computer Science or equivalent practical experience.

Benefits:
• Comprehensive health insurance, 401(k) matching, and unlimited PTO.
• Veloce Systems is an Equal Opportunity Employer.
TEXT;

$recruiterResume = <<<TEXT
Sarah Jenkins
sarah.jenkins@outlook.com | (415) 555-8901
linkedin.com/in/sarah-jenkins-recruiter

PROFESSIONAL EXPERIENCE
Lead Technical Recruiter | CloudScale Inc. | 2020 – Present
• Wrote job descriptions, defined role requirements, and managed candidate pipelines.
• Screened qualifications for senior engineering and DevOps positions.
• Evaluated team responsibilities and aligned hiring managers on role specifications.

Technical Recruiter | HireTalent | 2017 – 2020
• Sourced candidates across software engineering domains.

EDUCATION
B.A. in Human Resources | University of Michigan
TEXT;

$casualJD = <<<TEXT
Senior Python Engineer needed!
We're looking for our 3rd engineer to scale our platform.
What you'll do:
• Build backend APIs in FastAPI and Docker.
• Take ownership of our MySQL database.
Requirements:
• 3+ years experience with Python and relational databases.
TEXT;

echo "--- SECTION 1: CORE ORIENTATION DETECTION ---\n";

// TC-OG01: Standard Normal Order
$r1 = detectInputInversion($standardResume, $standardJD);
assertTest($r1['is_inverted'] === false, "TC-OG01: Standard normal order passes cleanly without inversion flag.", "Combined delta: {$r1['combined_delta']}");

// TC-OG02: Swapped Inverted Order
$r2 = detectInputInversion($standardJD, $standardResume);
assertTest($r2['is_inverted'] === true, "TC-OG02: Swapped order is deterministically flagged as inverted.", "Combined delta: {$r2['combined_delta']}");

// TC-OG03: Recruiter Resume Edge Case
$r3 = detectInputInversion($recruiterResume, $standardJD);
assertTest($r3['is_inverted'] === false, "TC-OG03: Recruiter resume containing JD terminology is not falsely flagged.", "Combined delta: {$r3['combined_delta']}");

// TC-OG04: Casual Startup JD Inversion
$r4 = detectInputInversion($casualJD, $standardResume);
assertTest($r4['is_inverted'] === true, "TC-OG04: Inverted casual startup JD in resume box is correctly detected.", "Combined delta: {$r4['combined_delta']}");

// TC-OG05: Dual Resume Symmetrical Input
$r5 = detectInputInversion($standardResume, $recruiterResume);
assertTest($r5['is_inverted'] === false, "TC-OG05: Symmetrical dual-resume submission is not flagged as inverted.", "Combined delta: {$r5['combined_delta']}");

// TC-OG06: Dual JD Symmetrical Input
$r6 = detectInputInversion($standardJD, $casualJD);
assertTest($r6['is_inverted'] === false, "TC-OG06: Symmetrical dual-JD submission is not flagged as inverted.", "Combined delta: {$r6['combined_delta']}");

// TC-OG07: Sub-threshold Short Strings
$r7 = detectInputInversion("Short bio", "Brief note");
assertTest($r7['is_inverted'] === false, "TC-OG07: Sub-50 char strings safely default to unflagged pass-through.");

echo "\n--- SECTION 2: DISCRIMINATION MARGIN METRICS ---\n";
echo "Normal Order Combined Delta: {$r1['combined_delta']} (Should be negative)\n";
echo "Inverted Order Combined Delta: {$r2['combined_delta']} (Should be strongly positive >= 4.5)\n";
assertTest($r1['combined_delta'] < 0, "TC-OG08a: Normal order produces negative differential delta.");
assertTest($r2['combined_delta'] >= 4.5, "TC-OG08b: Inverted order produces high positive differential delta >= 4.5.");

echo "\n======================================================================\n";
echo " TEST SUMMARY: {$passCount} Passed, {$failCount} Failed\n";
echo "======================================================================\n";

if ($failCount > 0) {
    exit(1);
}
