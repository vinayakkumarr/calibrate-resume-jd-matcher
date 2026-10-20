<?php
declare(strict_types=1);

echo "=== JD ANALYSER GATEWAY AUTOMATED TEST HARNESS ===\n\n";

// Test 1: Database Connection Handler
echo "[TEST 1] Testing config/database.php connection...\n";
require_once __DIR__ . '/../config/database.php';
if (!isset($pdo) || !($pdo instanceof PDO)) {
    echo "❌ FAILED: PDO instance not created.\n";
    exit(1);
}
echo "✅ PASS: PDO connected successfully to database.\n\n";

// Test 2: Status Endpoint - Input Validation
echo "[TEST 2] Testing public/api/status.php validation...\n";

// Function to simulate GET request to status.php via isolated sub-process
function testStatus(string $uuidParam, ?string $tokenParam = null) {
    $script = realpath(__DIR__ . '/../public/api/status.php');
    if ($tokenParam !== null) {
        $cmd = sprintf('php -r "$_GET=[\'uuid\'=>\'%s\']; $_SERVER=[\'HTTP_X_CLIENT_TOKEN\'=>\'%s\']; include \'%s\';"', addslashes($uuidParam), addslashes($tokenParam), addslashes($script));
    } else {
        $cmd = sprintf('php -r "$_GET=[\'uuid\'=>\'%s\']; include \'%s\';"', addslashes($uuidParam), addslashes($script));
    }
    $output = [];
    $ret = 0;
    exec($cmd, $output, $ret);
    $raw = implode("\n", $output);
    $body = json_decode($raw, true);
    return ['code' => $ret, 'body' => $body, 'raw' => $raw];
}

$testToken = bin2hex(random_bytes(16));
$otherToken = bin2hex(random_bytes(16));

// 2a. Invalid UUID format
$resInvalid = testStatus('invalid-uuid', $testToken);
if (isset($resInvalid['body']['error']) && str_contains($resInvalid['body']['error'], 'Invalid or missing scan UUID')) {
    echo "✅ PASS: Invalid UUID rejected with expected error message.\n";
} else {
    echo "❌ FAILED: Invalid UUID did not return expected error. Output: {$resInvalid['raw']}\n";
    exit(1);
}

// 2b. Missing client token (REM-01 Authorization Guard)
$fakeUuid = bin2hex(random_bytes(16));
$resNoToken = testStatus($fakeUuid, null);
if (isset($resNoToken['body']['error']) && str_contains($resNoToken['body']['error'], 'Missing or invalid client token')) {
    echo "✅ PASS: Missing client token correctly rejected with 403 error.\n";
} else {
    echo "❌ FAILED: Missing client token did not return expected error. Output: {$resNoToken['raw']}\n";
    exit(1);
}

// 2c. Non-existent UUID with valid token format
$res404 = testStatus($fakeUuid, $testToken);
if (isset($res404['body']['error']) && str_contains($res404['body']['error'], 'Scan ticket not found or unauthorized')) {
    echo "✅ PASS: Non-existent UUID returns expected error.\n";
} else {
    echo "❌ FAILED: Non-existent UUID did not return expected error. Output: {$res404['raw']}\n";
    exit(1);
}

// 2d. Valid Pending UUID with Wrong Token (Mismatched Token Rejection)
$testUuid = bin2hex(random_bytes(16));
$pdo->prepare("INSERT INTO scans (uuid, client_token, ip_subnet, resume_original_name, resume_relative_path, job_description, status) VALUES (?, ?, 'sub_test', 'test.pdf', 'uploads/test.pdf', 'Sample JD text exceeding minimum length requirement...', 'pending')")->execute([$testUuid, $testToken]);

$resWrongToken = testStatus($testUuid, $otherToken);
if (isset($resWrongToken['body']['error']) && str_contains($resWrongToken['body']['error'], 'Scan ticket not found or unauthorized')) {
    echo "✅ PASS: Mismatched client token correctly rejected without leaking scan existence.\n";
} else {
    echo "❌ FAILED: Mismatched client token check failed. Output: {$resWrongToken['raw']}\n";
    exit(1);
}

// 2e. Valid Pending UUID & Token - Authorized Access
$resPending = testStatus($testUuid, $testToken);
if (isset($resPending['body']['status']) && $resPending['body']['status'] === 'pending' && str_contains($resPending['body']['progress_message'], '1/3')) {
    echo "✅ PASS: Pending ticket returns unified envelope with progress_message for authorized client.\n";
} else {
    echo "❌ FAILED: Pending ticket check failed. Output: {$resPending['raw']}\n";
    exit(1);
}

// 2f. 90-Second Watchdog Auto-Fail (Authorized)
$staleUuid = bin2hex(random_bytes(16));
$pdo->prepare("INSERT INTO scans (uuid, client_token, ip_subnet, resume_original_name, resume_relative_path, job_description, status, created_at) VALUES (?, ?, 'sub_test', 'test.pdf', 'uploads/test.pdf', 'Sample JD text exceeding minimum length...', 'processing', NOW() - INTERVAL 95 SECOND)")->execute([$staleUuid, $testToken]);

$resWatchdog = testStatus($staleUuid, $testToken);
if (isset($resWatchdog['body']['status']) && $resWatchdog['body']['status'] === 'failed' && str_contains($resWatchdog['body']['error_message'], '90 seconds')) {
    echo "✅ PASS: Watchdog auto-failed stale processing scan (>90s).\n";
} else {
    echo "❌ FAILED: Watchdog check failed. Body: " . json_encode($resWatchdog['body']) . "\n";
    exit(1);
}

// Clean up temporary test scan rows
$pdo->prepare("DELETE FROM scans WHERE uuid IN (?, ?)")->execute([$testUuid, $staleUuid]);
echo "✅ PASS: Cleaned up test database fixtures.\n\n";

echo "=== ALL GATEWAY ENDPOINT TESTS PASSED SUCCESSFULLY! ===\n";
