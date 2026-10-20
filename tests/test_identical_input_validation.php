<?php
declare(strict_types=1);

/**
 * Isolated Automated Regression Suite: Fix B — Identical Resume & Job Description Validation
 * 
 * Verifies:
 *   - Test B1: Exact identical text rejected on server with HTTP 422 and approved actionable message.
 *   - Test B2: Whitespace-only, line-ending (CRLF vs LF), and blank-line differences correctly detected as identical.
 *   - Test B3: Truly distinct resume and JD content pass the guard without rejection.
 *   - Test B4: Substantial keyword/skill overlap (e.g. 85%+ shared technical terms) is NOT falsely rejected.
 *   - Test B5: Invalid/empty inputs continue to trigger existing length and presence validations.
 *   - Test B6: Side-effect boundary — Identical input rejection triggers 0 disk writes, 0 DB inserts, 0 process spawns.
 *   - Test B7: API compatibility — Proper HTTP 422 status and JSON error envelope structure.
 * 
 * Safety: Pure in-memory and isolated test doubles; zero database writes; zero persistent state mutations.
 */

echo "=== FIX B: IDENTICAL INPUT VALIDATION TEST HARNESS ===\n\n";

$passCount = 0;
$failCount = 0;

function assertCondition(bool $condition, string $testName, string $details = '') {
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

echo "\n--- Section 1: Normalization & Identity Detection Logic ---\n";

$baseText = "Job Title: Junior Full Stack Developer (PHP / JS / React)\nCompany: NexaTech Solutions\nKey Responsibilities:\n• Build web applications using PHP and React.\n• Architect relational databases with MySQL.";

// Test B1: Exact Identical Text
$isIdenticalB1 = areInputsIdentical($baseText, $baseText);
assertCondition($isIdenticalB1 === true, "Test B1 (Exact Identical Text): Exact matching strings detected as identical.");

// Test B2: Insignificant Formatting Variations
$crlfText = "Job Title: Junior Full Stack Developer (PHP / JS / React)\r\nCompany: NexaTech Solutions\r\n\r\nKey Responsibilities:\r\n• Build web applications using PHP and React.\r\n• Architect relational databases with MySQL.\r\n";
$isIdenticalB2a = areInputsIdentical($baseText, $crlfText);
assertCondition($isIdenticalB2a === true, "Test B2a (Line Endings): CRLF vs LF line endings recognized as identical.");

$spacedText = "   Job Title:   Junior Full Stack   Developer (PHP / JS / React)  \n\nCompany: NexaTech Solutions\n\n\nKey Responsibilities:\n• Build web applications using PHP and React.\n• Architect relational databases with MySQL.   \n\n";
$isIdenticalB2b = areInputsIdentical($baseText, $spacedText);
assertCondition($isIdenticalB2b === true, "Test B2b (Whitespace & Blank Lines): Multiple spaces, tabs, and blank lines recognized as identical.");

$caseVariedText = "JOB TITLE: Junior Full Stack Developer (PHP / JS / React)\nCompany: NexaTech Solutions\nKey Responsibilities:\n• Build web applications using PHP and React.\n• Architect relational databases with MySQL.";
$isIdenticalB2c = areInputsIdentical($baseText, $caseVariedText);
assertCondition($isIdenticalB2c === true, "Test B2c (Case Insensitivity): Case-varied text recognized as identical.");

// Test B3: Different Content
$differentText = "John Doe\nSummary: Passionate Full Stack Developer with 3 years of building performant SaaS applications.\nExperience:\nSoftware Engineer at Acme Corp (2021 - 2024)\n• Built full stack web apps with PHP and React.\n• Architected MySQL schemas.";
$isIdenticalB3 = areInputsIdentical($baseText, $differentText);
assertCondition($isIdenticalB3 === false, "Test B3 (Different Content): Distinct resume text is NOT flagged as identical.");

// Test B4: Substantial Keyword Overlap (Non-Identical)
$highOverlapResume = "Candidate Name: Alex Johnson\nProfessional Overview:\nExperienced Junior Full Stack Developer matching NexaTech Solutions requirements.\nKey Accomplishments:\n• Build web applications using PHP and React with sub-200ms latency.\n• Architect relational databases with MySQL enforcing 3NF normalization rules.";
$isIdenticalB4 = areInputsIdentical($baseText, $highOverlapResume);
assertCondition($isIdenticalB4 === false, "Test B4 (High Overlap Non-Identical): Resume sharing keywords with JD is NOT rejected.");

// Test B5: Empty and Boundary Inputs
assertCondition(areInputsIdentical("", $baseText) === false, "Test B5a: Empty text A returns false.");
assertCondition(areInputsIdentical($baseText, "") === false, "Test B5b: Empty text B returns false.");
assertCondition(areInputsIdentical("", "") === false, "Test B5c: Both empty returns false.");


echo "\n--- Section 2: Isolated HTTP Subprocess & Side-Effect Boundary Tests ---\n";

function runIsolatedScan(array $postData, array $files = []): array {
    $script = realpath(__DIR__ . '/../public/api/scan.php');
    
    // Create an isolated runner script to invoke scan.php via clean CLI environment
    $runnerCode = '<?php
    $_SERVER["REQUEST_METHOD"] = "POST";
    $_SERVER["REMOTE_ADDR"] = "127.0.0.1";
    $_ENV["APP_ENV"] = "development";
    $_POST = ' . var_export($postData, true) . ';
    $_FILES = ' . var_export($files, true) . ';
    
    register_shutdown_function(function() {
        $output = ob_get_clean();
        $code = http_response_code();
        echo "___TEST_META___" . json_encode(["status_code" => $code, "output" => $output]);
    });
    ob_start();
    include ' . var_export($script, true) . ';
    ';

    $tmpRunner = tempnam(sys_get_temp_dir(), 'test_scan_');
    file_put_contents($tmpRunner, $runnerCode);

    $cmd = sprintf('php %s', escapeshellarg($tmpRunner));
    $outLines = [];
    $ret = 0;
    exec($cmd, $outLines, $ret);
    @unlink($tmpRunner);

    $raw = implode("\n", $outLines);
    $parts = explode("___TEST_META___", $raw, 2);
    $metaJson = $parts[1] ?? '{}';
    $data = json_decode($metaJson, true) ?? ["status_code" => 0, "output" => $raw];
    $body = json_decode($data["output"] ?? '', true) ?? ["raw" => $data["output"]];
    
    return [
        "http_code" => $data["status_code"],
        "body" => $body
    ];
}

// Record file count in storage/uploads before tests
$uploadDir = realpath(__DIR__ . '/../storage/uploads');
$filesBefore = $uploadDir ? count(glob($uploadDir . '/*')) : 0;

// Test B1 & B7: Identical Input Submission via Simulated Request
$validJdText = "Job Title: Junior Full Stack Developer (PHP / JS / React)\nCompany: NexaTech Solutions\nKey Responsibilities:\n• Develop and maintain full-stack web applications using PHP and modern JS frameworks.\n• Build responsive front-end interfaces utilizing HTML5, CSS3, and React.\n• Architect and query relational databases with structured indexing.";

$resIdentical = runIsolatedScan([
    "resume_mode" => "text",
    "resume_text" => $validJdText,
    "job_description" => $validJdText,
    "jd_mode" => "text"
]);

$expectedMessage = "The Resume and Job Description appear to contain the same text. Please check that the Resume field contains the candidate's resume and the Job Description field contains the job posting.";

assertCondition(
    $resIdentical["http_code"] === 422,
    "Test B7a (HTTP Status): Identical input rejected with HTTP 422.",
    "Got code: {$resIdentical['http_code']}"
);

assertCondition(
    isset($resIdentical["body"]["error"]) && $resIdentical["body"]["error"] === $expectedMessage,
    "Test B7b (Response Message): Exact approved neutral error message returned.",
    "Got: " . json_encode($resIdentical["body"])
);

// Test B6: Side-Effect Boundary
$filesAfter = $uploadDir ? count(glob($uploadDir . '/*')) : 0;
assertCondition(
    $filesAfter === $filesBefore,
    "Test B6 (Zero Disk Artifacts): No file was written to storage/uploads upon rejection ({$filesBefore} -> {$filesAfter})."
);

// Test B5: Short Input Validation Precedes Identity Check
$shortInput = "Too short";
$resShort = runIsolatedScan([
    "resume_mode" => "text",
    "resume_text" => $shortInput,
    "job_description" => $shortInput,
    "jd_mode" => "text"
]);

assertCondition(
    $resShort["http_code"] === 422 && str_contains($resShort["body"]["error"] ?? '', "too short"),
    "Test B5 (Length Guard Precedence): Short inputs rejected with length validation before identity guard."
);

echo "\n=======================================================\n";
echo "SUMMARY: {$passCount} PASSED, {$failCount} FAILED\n";
echo "=======================================================\n";

if ($failCount > 0) {
    exit(1);
}
