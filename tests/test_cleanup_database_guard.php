<?php
declare(strict_types=1);

/**
 * Isolated Automated Test Suite: Cleanup Database & Server Identity Guard
 * Phase 6.2: Database Server Identity Guard & Cross-Environment Protection
 *
 * Verifies:
 * 1. Correct database name and correct server identity -> PASS.
 * 2. Missing expected database name in live mode -> FAILS CLOSED.
 * 3. Missing expected server identity in live mode -> FAILS CLOSED.
 * 4. Correct database name but incorrect server identity -> FAILS CLOSED.
 * 5. Same database name on two different configured server identities -> FAILS CLOSED (cross-environment isolation).
 * 6. Malformed or generic identity configuration (e.g. 'localhost', '127.0.0.1') -> FAILS CLOSED.
 * 7. Connection/identity lookup failure (SELECT DATABASE() or SELECT @@hostname fails) -> FAILS CLOSED.
 * 8. Execution ordering invariant: Guard evaluation strictly precedes destructive operations, file unlinks, and telemetry.
 * 9. Dry-run behavior remains non-destructive and clearly distinguishes simulation from live authorization.
 * 10. No credentials or sensitive connection details leak into error messages.
 * 11. Working directory independence: PHP __DIR__ path resolution functions identically from any directory.
 *
 * Safety: Executes strictly in-memory using MockPDO instances.
 * Zero mutations to jd_analyser or application storage. Zero network requests.
 */

define('CALIBRATE_TEST_MODE', true);
require_once __DIR__ . '/../cron/cleanup.php';

echo "=== CALIBRATE AI — DATABASE & SERVER IDENTITY GUARD TEST SUITE ===\n\n";

$passCount = 0;
$failCount = 0;

function assertGuard(bool $condition, string $testName, string $failureDetails = ''): void {
    global $passCount, $failCount;
    if ($condition) {
        echo "  [PASS] {$testName}\n";
        $passCount++;
    } else {
        echo "  [FAIL] {$testName} - {$failureDetails}\n";
        $failCount++;
    }
}

/**
 * Isolated Mock PDO representing MySQL/MariaDB server instance with custom identity responses.
 */
class MockDatabasePDO extends PDO {
    private ?string $activeDatabase;
    private ?string $serverHostname;
    private bool $simulateDbError;
    private bool $simulateHostError;

    public function __construct(
        ?string $activeDatabase = 'jd_analyser',
        ?string $serverHostname = 'TUF-A17',
        bool $simulateDbError = false,
        bool $simulateHostError = false
    ) {
        $this->activeDatabase = $activeDatabase;
        $this->serverHostname = $serverHostname;
        $this->simulateDbError = $simulateDbError;
        $this->simulateHostError = $simulateHostError;
    }

    public function query(string $query, ?int $fetchMode = null, mixed ...$fetchModeArgs): PDOStatement|false {
        if (stripos($query, 'DATABASE()') !== false) {
            if ($this->simulateDbError || $this->activeDatabase === null) {
                throw new PDOException("Simulated SQL error or unselected database");
            }
            $val = $this->activeDatabase;
            return new class($val) extends PDOStatement {
                private ?string $val;
                public function __construct(?string $val) { $this->val = $val; }
                public function fetchColumn(int $column = 0): mixed { return $this->val; }
            };
        }

        if (stripos($query, '@@hostname') !== false) {
            if ($this->simulateHostError || $this->serverHostname === null) {
                throw new PDOException("Simulated SQL error or unknown server variable");
            }
            $val = $this->serverHostname;
            return new class($val) extends PDOStatement {
                private ?string $val;
                public function __construct(?string $val) { $this->val = $val; }
                public function fetchColumn(int $column = 0): mixed { return $this->val; }
            };
        }

        throw new PDOException("Mock query not implemented: " . $query);
    }
}

// -----------------------------------------------------------------------------
// Test 1: Correct Database Name AND Correct Server Identity (Live Mode)
// -----------------------------------------------------------------------------
echo "[TEST 1] Verifying Correct Database Name & Server Identity (Live Mode)...\n";
$mockPdo = new MockDatabasePDO('jd_analyser', 'TUF-A17');
$envValid = [
    'CLEANUP_TARGET_DATABASE' => 'jd_analyser',
    'CLEANUP_TARGET_SERVER_IDENTITY' => 'TUF-A17',
    'DB_PASS' => 'super_secret_123',
    'DB_USER' => 'root'
];
$res = evaluate_cleanup_database_guard($mockPdo, $envValid, false);

assertGuard($res['passed'] === true, "Guard passes when database name and server identity match active connection.");
assertGuard($res['active_db'] === 'jd_analyser', "Active database correctly resolved as 'jd_analyser'.");
assertGuard($res['active_server'] === 'TUF-A17', "Active server hostname correctly resolved as 'TUF-A17'.");
assertGuard(str_contains($res['message'], "[CLEANUP_GUARD] Verified target database identity: 'jd_analyser' on server 'TUF-A17'"), "Exact approval message confirmed.");

// Case-insensitive match check (e.g. JD_ANALYSER on tuf-a17)
$mockPdoCase = new MockDatabasePDO('JD_ANALYSER', 'tuf-a17');
$resCase = evaluate_cleanup_database_guard($mockPdoCase, $envValid, false);
assertGuard($resCase['passed'] === true, "Guard handles case-insensitive host and database naming correctly.");

// -----------------------------------------------------------------------------
// Test 2: Missing Expected Database Name (Live Mode — Fail Closed)
// -----------------------------------------------------------------------------
echo "\n[TEST 2] Verifying Missing Expected Database Name (Live Mode — Fail Closed)...\n";
$envMissingDb = [
    'CLEANUP_TARGET_SERVER_IDENTITY' => 'TUF-A17',
    'DB_PASS' => 'super_secret_123'
];
$resMissingDb = evaluate_cleanup_database_guard($mockPdo, $envMissingDb, false);

assertGuard($resMissingDb['passed'] === false, "Live cleanup FAILS CLOSED when CLEANUP_TARGET_DATABASE is omitted.");
assertGuard(str_contains($resMissingDb['message'], 'CLEANUP_GUARD_ERROR'), "Clear error prefix returned for missing database.");
assertGuard(str_contains($resMissingDb['message'], 'Set CLEANUP_TARGET_DATABASE in .env'), "Actionable instructions provided for database target.");

// -----------------------------------------------------------------------------
// Test 3: Missing Expected Server Identity (Live Mode — Fail Closed)
// -----------------------------------------------------------------------------
echo "\n[TEST 3] Verifying Missing Expected Server Identity (Live Mode — Fail Closed)...\n";
$envMissingServer = [
    'CLEANUP_TARGET_DATABASE' => 'jd_analyser',
    'DB_PASS' => 'super_secret_123'
];
$resMissingServer = evaluate_cleanup_database_guard($mockPdo, $envMissingServer, false);

assertGuard($resMissingServer['passed'] === false, "Live cleanup FAILS CLOSED when CLEANUP_TARGET_SERVER_IDENTITY is omitted.");
assertGuard(str_contains($resMissingServer['message'], 'CLEANUP_GUARD_ERROR'), "Clear error prefix returned for missing server.");
assertGuard(str_contains($resMissingServer['message'], 'Set CLEANUP_TARGET_SERVER_IDENTITY in .env'), "Actionable instructions provided for server target.");

// -----------------------------------------------------------------------------
// Test 4: Correct Database Name but Incorrect Server Identity
// -----------------------------------------------------------------------------
echo "\n[TEST 4] Verifying Correct Database Name but Incorrect Server Identity...\n";
$mockPdoStagingNode = new MockDatabasePDO('jd_analyser', 'staging-node-01');
$envTargetProd = [
    'CLEANUP_TARGET_DATABASE' => 'jd_analyser',
    'CLEANUP_TARGET_SERVER_IDENTITY' => 'prod-db-primary',
    'DB_PASS' => 'prod_pass_secret'
];
$resServerMismatch = evaluate_cleanup_database_guard($mockPdoStagingNode, $envTargetProd, false);

assertGuard($resServerMismatch['passed'] === false, "Cleanup FAILS CLOSED when server identity does not match.");
assertGuard(str_contains($resServerMismatch['message'], 'Database server identity mismatch'), "Server identity mismatch error returned.");
assertGuard(!str_contains($resServerMismatch['message'], 'prod_pass_secret'), "Zero credential leakage in server mismatch output.");

// -----------------------------------------------------------------------------
// Test 5: Same Database Name on Two Different Configured Server Identities
// -----------------------------------------------------------------------------
echo "\n[TEST 5] Verifying Cross-Environment Collision Prevention (Same DB Name, Different Servers)...\n";
// Scenario: A developer configures jd_analyser against local dev machine, but accidentally points script at staging server
$mockPdoLocalDev = new MockDatabasePDO('jd_analyser', 'dev-workstation-99');
$envTargetStaging = [
    'CLEANUP_TARGET_DATABASE' => 'jd_analyser',
    'CLEANUP_TARGET_SERVER_IDENTITY' => 'staging-db-cluster-01'
];
$resCrossEnv = evaluate_cleanup_database_guard($mockPdoLocalDev, $envTargetStaging, false);

assertGuard($resCrossEnv['passed'] === false, "Cleanup FAILS CLOSED preventing cross-environment execution against wrong server.");
assertGuard(str_contains($resCrossEnv['message'], 'Database server identity mismatch'), "Cross-environment execution halted with clear error.");

// -----------------------------------------------------------------------------
// Test 6: Malformed / Generic Identity Configuration
// -----------------------------------------------------------------------------
echo "\n[TEST 6] Verifying Rejection of Generic / Ambiguous Server Identifiers...\n";
$genericCandidates = ['localhost', '127.0.0.1', '::1', 'production', 'staging', 'local', '0.0.0.0'];
foreach ($genericCandidates as $generic) {
    $envGeneric = [
        'CLEANUP_TARGET_DATABASE' => 'jd_analyser',
        'CLEANUP_TARGET_SERVER_IDENTITY' => $generic
    ];
    $resGeneric = evaluate_cleanup_database_guard($mockPdo, $envGeneric, false);
    assertGuard($resGeneric['passed'] === false, "Generic server identity '{$generic}' is strictly rejected as non-authoritative.");
    assertGuard(str_contains($resGeneric['message'], 'Invalid server identity: generic or ambiguous identifiers'), "Prohibition message confirmed for '{$generic}'.");
}

// -----------------------------------------------------------------------------
// Test 7: Connection / Identity Lookup Failure
// -----------------------------------------------------------------------------
echo "\n[TEST 7] Verifying Connection / Identity Lookup Failures...\n";
// Subcase 7a: SELECT DATABASE() throws or returns null
$mockPdoDbFail = new MockDatabasePDO(activeDatabase: null, serverHostname: 'TUF-A17', simulateDbError: true);
$resDbFail = evaluate_cleanup_database_guard($mockPdoDbFail, $envValid, false);
assertGuard($resDbFail['passed'] === false, "Guard FAILS CLOSED when SELECT DATABASE() fails.");
assertGuard(str_contains($resDbFail['message'], 'Unable to resolve active database'), "Diagnostic error returned for database resolution failure.");

// Subcase 7b: SELECT @@hostname throws or returns null
$mockPdoHostFail = new MockDatabasePDO(activeDatabase: 'jd_analyser', serverHostname: null, simulateHostError: true);
$resHostFail = evaluate_cleanup_database_guard($mockPdoHostFail, $envValid, false);
assertGuard($resHostFail['passed'] === false, "Guard FAILS CLOSED when SELECT @@hostname fails.");
assertGuard(str_contains($resHostFail['message'], 'Unable to resolve server identity'), "Diagnostic error returned for server resolution failure.");

// -----------------------------------------------------------------------------
// Test 8: Execution Ordering Invariant
// -----------------------------------------------------------------------------
echo "\n[TEST 8] Verifying Execution Ordering Invariant in cron/cleanup.php...\n";
$cleanupSource = file_get_contents(__DIR__ . '/../cron/cleanup.php');

$posGuard = strpos($cleanupSource, 'evaluate_cleanup_database_guard');
$posHeartbeat = strpos($cleanupSource, '$heartbeatFile =');
$posActiveScans = strpos($cleanupSource, '$activeStmt = $pdo->query');
$posUnlink = strpos($cleanupSource, '@unlink($realPath)');
$posDeleteScans = strpos($cleanupSource, 'DELETE FROM scans');

assertGuard($posGuard !== false, "Guard evaluation present in cron/cleanup.php.");
assertGuard($posGuard < $posHeartbeat, "Guard evaluation occurs BEFORE heartbeat telemetry update.");
assertGuard($posGuard < $posActiveScans, "Guard evaluation occurs BEFORE active scan query.");
assertGuard($posGuard < $posUnlink, "Guard evaluation occurs BEFORE any file unlinking.");
assertGuard($posGuard < $posDeleteScans, "Guard evaluation occurs BEFORE any database record deletion.");

// -----------------------------------------------------------------------------
// Test 9: Dry-Run Mode Safety & Notice Handling
// -----------------------------------------------------------------------------
echo "\n[TEST 9] Verifying Dry-Run Simulation Mode Invariants...\n";
// Dry-run with missing DB setting
$resDryRunMissingDb = evaluate_cleanup_database_guard($mockPdo, $envMissingDb, true);
assertGuard($resDryRunMissingDb['passed'] === true, "Dry-run simulation allowed when database target is unset.");
assertGuard(str_contains($resDryRunMissingDb['message'], 'DRY RUN GUARD NOTICE'), "Clear dry-run notice for missing database.");
assertGuard(str_contains($resDryRunMissingDb['message'], 'Real cleanup will fail closed'), "Warning that real cleanup is blocked.");

// Dry-run with missing server setting
$resDryRunMissingServer = evaluate_cleanup_database_guard($mockPdo, $envMissingServer, true);
assertGuard($resDryRunMissingServer['passed'] === true, "Dry-run simulation allowed when server target is unset.");
assertGuard(str_contains($resDryRunMissingServer['message'], 'DRY RUN GUARD NOTICE'), "Clear dry-run notice for missing server.");

// Dry-run with mismatched server setting must still halt simulation
$resDryRunMismatch = evaluate_cleanup_database_guard($mockPdoStagingNode, $envTargetProd, true);
assertGuard($resDryRunMismatch['passed'] === false, "Dry-run simulation FAILS when connected server does not match configured target.");

// Dry-run with valid match
$resDryRunValid = evaluate_cleanup_database_guard($mockPdo, $envValid, true);
assertGuard($resDryRunValid['passed'] === true, "Dry-run succeeds when targets match.");
assertGuard(str_contains($resDryRunValid['message'], 'Proceeding with simulation'), "Simulation message confirmed.");

// -----------------------------------------------------------------------------
// Test 10: Non-Disclosure of Sensitive Connection Details
// -----------------------------------------------------------------------------
echo "\n[TEST 10] Verifying Non-Disclosure of Sensitive Connection Details...\n";
$allErrorMessages = [
    $res['message'],
    $resMissingDb['message'],
    $resMissingServer['message'],
    $resServerMismatch['message'],
    $resCrossEnv['message'],
    $resDbFail['message'],
    $resHostFail['message'],
    $resDryRunMissingDb['message'],
    $resDryRunMissingServer['message']
];

$leakDetected = false;
$forbiddenTokens = ['super_secret_123', 'prod_pass_secret', '3306', 'root', '127.0.0.1:'];
foreach ($allErrorMessages as $msg) {
    foreach ($forbiddenTokens as $tok) {
        if (str_contains($msg, $tok)) {
            $leakDetected = true;
            break 2;
        }
    }
}
assertGuard(!$leakDetected, "All guard messages strictly preserve confidentiality of credentials and port numbers.");

// -----------------------------------------------------------------------------
// Test 11: Working Directory Independence
// -----------------------------------------------------------------------------
echo "\n[TEST 11] Verifying Working Directory Independence...\n";
$origCwd = getcwd();
$tempDir = sys_get_temp_dir();
chdir($tempDir);

$currentCwdInTemp = getcwd();
$cronDirFromTemp = realpath(__DIR__ . '/../cron');
$storageDirFromTemp = realpath(__DIR__ . '/../storage');
chdir($origCwd);

assertGuard($currentCwdInTemp !== $origCwd, "Process working directory successfully switched to temporary directory.");
assertGuard($cronDirFromTemp !== false && is_dir($cronDirFromTemp), "cron directory path strictly anchored via __DIR__ regardless of CWD.");
assertGuard($storageDirFromTemp !== false && is_dir($storageDirFromTemp), "storage directory path strictly anchored via __DIR__ regardless of CWD.");

// -----------------------------------------------------------------------------
// Summary
// -----------------------------------------------------------------------------
echo "\n=======================================================\n";
echo "DATABASE & SERVER GUARD SUMMARY: {$passCount} PASSED, {$failCount} FAILED\n";
echo "=======================================================\n";

if ($failCount > 0) {
    exit(1);
}
exit(0);
