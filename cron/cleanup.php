<?php
declare(strict_types=1);

// Enforce CLI-only execution boundary (fail-closed against web server exposure)
if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    header('Content-Type: application/json; charset=UTF-8');
    header('X-Content-Type-Options: nosniff');
    echo json_encode([
        'success' => false,
        'error'   => 'Forbidden: This script can only be executed via the command line interface (CLI).'
    ], JSON_UNESCAPED_SLASHES);
    exit(1);
}

/**
 * JD Analyser — Automated 2-Hour TTL Zero-Retention Privacy Daemon
 * Enforces local privacy and disk hygiene by permanently destroying uploaded PDFs
 * and operational execution logs older than 2 hours, and purging scans older than 30 days.
 *
 * Usage:
 *   php cron/cleanup.php             # Normal live execution
 *   php cron/cleanup.php --dry-run   # Simulates deletion without modifying disk/DB
 */

if (!function_exists('evaluate_cleanup_database_guard')) {
    /**
     * Evaluates explicit target database and server identity guards against the active PDO connection.
     * Fail-closed security rule: Prevents cleanup operations against an unintended database or server.
     *
     * @param PDO $pdo Active PDO connection
     * @param array $env Configuration/Environment array (typically $_ENV)
     * @param bool $isDryRun Whether cleanup is executing in non-mutating simulation mode
     * @return array{passed: bool, message: string, active_db: ?string, expected_db: ?string, active_server: ?string, expected_server: ?string}
     */
    function evaluate_cleanup_database_guard(PDO $pdo, array $env, bool $isDryRun = false): array
    {
        $expectedDb = trim((string)($env['CLEANUP_TARGET_DATABASE'] ?? ''));
        $expectedServer = trim((string)($env['CLEANUP_TARGET_SERVER_IDENTITY'] ?? ''));

        // Prohibited generic/ambiguous server identities that do not uniquely identify a server instance
        $prohibitedGenericServers = [
            'localhost', '127.0.0.1', '::1', '0.0.0.0', 'local', '(local)',
            'development', 'production', 'staging', 'test', 'dev', 'prod'
        ];

        // Resolve active connected database name
        $activeDb = null;
        try {
            $stmt = $pdo->query("SELECT DATABASE()");
            $val = $stmt ? $stmt->fetchColumn() : null;
            if (is_string($val) && trim($val) !== '') {
                $activeDb = trim($val);
            }
        } catch (Throwable $e) {
            $activeDb = null;
        }

        // Resolve active server identity via @@hostname
        $activeServer = null;
        try {
            $stmt = $pdo->query("SELECT @@hostname");
            $val = $stmt ? $stmt->fetchColumn() : null;
            if (is_string($val) && trim($val) !== '') {
                $activeServer = trim($val);
            }
        } catch (Throwable $e) {
            $activeServer = null;
        }

        // Validate target database name configuration
        if ($expectedDb === '') {
            $msg = "Target database guard is not configured. Set CLEANUP_TARGET_DATABASE in .env to explicitly authorize cleanup on the intended database.";
            if ($isDryRun) {
                return [
                    'passed' => true,
                    'message' => "[DRY RUN GUARD NOTICE] {$msg} Real cleanup will fail closed.",
                    'active_db' => $activeDb,
                    'expected_db' => null,
                    'active_server' => $activeServer,
                    'expected_server' => $expectedServer ?: null,
                ];
            }
            return [
                'passed' => false,
                'message' => "[CLEANUP_GUARD_ERROR] {$msg}",
                'active_db' => $activeDb,
                'expected_db' => null,
                'active_server' => $activeServer,
                'expected_server' => $expectedServer ?: null,
            ];
        }

        // Validate target server identity configuration
        if ($expectedServer === '') {
            $msg = "Target server identity guard is not configured. Set CLEANUP_TARGET_SERVER_IDENTITY in .env to explicitly authorize cleanup on the intended database server.";
            if ($isDryRun) {
                return [
                    'passed' => true,
                    'message' => "[DRY RUN GUARD NOTICE] {$msg} Real cleanup will fail closed.",
                    'active_db' => $activeDb,
                    'expected_db' => $expectedDb,
                    'active_server' => $activeServer,
                    'expected_server' => null,
                ];
            }
            return [
                'passed' => false,
                'message' => "[CLEANUP_GUARD_ERROR] {$msg}",
                'active_db' => $activeDb,
                'expected_db' => $expectedDb,
                'active_server' => $activeServer,
                'expected_server' => null,
            ];
        }

        // Reject ambiguous or generic server identifiers
        if (in_array(strtolower($expectedServer), $prohibitedGenericServers, true)) {
            $msg = "[CLEANUP_GUARD_ERROR] Invalid server identity: generic or ambiguous identifiers ('{$expectedServer}') cannot be used as an authoritative server identity. Specify the unique server hostname (e.g. from SELECT @@hostname).";
            return [
                'passed' => false,
                'message' => $msg,
                'active_db' => $activeDb,
                'expected_db' => $expectedDb,
                'active_server' => $activeServer,
                'expected_server' => $expectedServer,
            ];
        }

        // Verify connection and identity lookup resolution
        if ($activeDb === null) {
            $msg = "[CLEANUP_GUARD_ERROR] Unable to resolve active database from connection (SELECT DATABASE() failed). Target database guard verification failed.";
            return [
                'passed' => false,
                'message' => $msg,
                'active_db' => null,
                'expected_db' => $expectedDb,
                'active_server' => $activeServer,
                'expected_server' => $expectedServer,
            ];
        }

        if ($activeServer === null) {
            $msg = "[CLEANUP_GUARD_ERROR] Unable to resolve server identity from connection (SELECT @@hostname failed). Target server guard verification failed.";
            return [
                'passed' => false,
                'message' => $msg,
                'active_db' => $activeDb,
                'expected_db' => $expectedDb,
                'active_server' => null,
                'expected_server' => $expectedServer,
            ];
        }

        // Verify database name matches target
        if (strcasecmp($activeDb, $expectedDb) !== 0) {
            $msg = "[CLEANUP_GUARD_ERROR] Database identity mismatch: configured target does not match active connection. Cleanup aborted.";
            return [
                'passed' => false,
                'message' => $msg,
                'active_db' => $activeDb,
                'expected_db' => $expectedDb,
                'active_server' => $activeServer,
                'expected_server' => $expectedServer,
            ];
        }

        // Verify server identity matches target
        if (strcasecmp($activeServer, $expectedServer) !== 0) {
            $msg = "[CLEANUP_GUARD_ERROR] Database server identity mismatch: configured target server does not match active connection. Cleanup aborted.";
            return [
                'passed' => false,
                'message' => $msg,
                'active_db' => $activeDb,
                'expected_db' => $expectedDb,
                'active_server' => $activeServer,
                'expected_server' => $expectedServer,
            ];
        }

        // All target identifiers verified
        $prefix = $isDryRun ? "[DRY RUN GUARD]" : "[CLEANUP_GUARD]";
        $action = $isDryRun ? "Proceeding with simulation." : "Proceeding.";
        return [
            'passed' => true,
            'message' => "{$prefix} Verified target database identity: '{$expectedDb}' on server '{$expectedServer}'. {$action}",
            'active_db' => $activeDb,
            'expected_db' => $expectedDb,
            'active_server' => $activeServer,
            'expected_server' => $expectedServer,
        ];
    }
}

// In test mode, allow tests to inspect helper functions without executing cleanup
if (defined('CALIBRATE_TEST_MODE') && CALIBRATE_TEST_MODE) {
    return;
}

require_once __DIR__ . '/../config/database.php';

$isDryRun = in_array('--dry-run', $argv ?? [], true);
if ($isDryRun) {
    echo "[DRY RUN MODE] Simulating 2-hour TTL cleanup without modifying disk or database.\n";
}

$storageBase = realpath(__DIR__ . '/../storage');
if (!$storageBase) {
    $storageBase = __DIR__ . '/../storage';
}

$uploadsDir = $storageBase . DIRECTORY_SEPARATOR . 'uploads';
$logsDir    = $storageBase . DIRECTORY_SEPARATOR . 'logs';

if (!is_dir($logsDir) && !$isDryRun) {
    mkdir($logsDir, 0755, true);
}

// Prevent overlapping cleanup runs using a non-blocking exclusive lock
$lockHandle = null;
if (!$isDryRun) {
    $lockFile = $logsDir . DIRECTORY_SEPARATOR . 'cleanup.lock';
    $lockHandle = fopen($lockFile, 'c+');
    if (!$lockHandle || !flock($lockHandle, LOCK_EX | LOCK_NB)) {
        echo "[NOTICE] Another cleanup process is currently executing. Exiting cleanly.\n";
        if ($lockHandle) {
            fclose($lockHandle);
        }
        exit(0);
    }
}

try {
    // Verify database target guard before modifying state or telemetry
    $guardResult = evaluate_cleanup_database_guard($pdo, $_ENV, $isDryRun);
    echo $guardResult['message'] . "\n";
    if (!$guardResult['passed']) {
        if ($lockHandle) {
            flock($lockHandle, LOCK_UN);
            fclose($lockHandle);
            $lockHandle = null;
        }
        exit(1);
    }

    // Record heartbeat timestamp (skipped in dry-run mode)
    if (!$isDryRun && is_dir($logsDir)) {
        $heartbeatFile = $logsDir . DIRECTORY_SEPARATOR . 'cron_heartbeat.txt';
        file_put_contents($heartbeatFile, (string)time());
    }

    $now = time();
    $purgedFileCount = 0;
    $purgedLogCount = 0;
    $purgedRowCount = 0;
    $handledPaths = [];
    $protectedPaths = [];

    // Protect files belonging to active (pending or processing) scans from deletion
    $activeStmt = $pdo->query("SELECT id, uuid, resume_relative_path FROM scans WHERE status IN ('pending', 'processing')");
    $activeScans = $activeStmt->fetchAll(PDO::FETCH_ASSOC);
    foreach ($activeScans as $active) {
        if (!empty($active['resume_relative_path'])) {
            $actFullPath = $storageBase . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $active['resume_relative_path']);
            $actRealPath = realpath($actFullPath);
            if ($actRealPath) {
                $protectedPaths[$actRealPath] = true;
            }
        }
        if (!empty($active['uuid'])) {
            $actSidecar = $uploadsDir . DIRECTORY_SEPARATOR . $active['uuid'] . '.extracted.txt';
            $actRealSidecar = realpath($actSidecar);
            if ($actRealSidecar) {
                $protectedPaths[$actRealSidecar] = true;
            }
        }
    }

    // Purge uploaded resume files older than 2 hours for completed or failed scans
    $stmt = $pdo->prepare("SELECT id, uuid, resume_relative_path FROM scans WHERE is_purged = 0 AND status NOT IN ('pending', 'processing') AND created_at < NOW() - INTERVAL 2 HOUR");
    $stmt->execute();
    $unpurged = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $updatePurgedStmt = $pdo->prepare("UPDATE scans SET is_purged = 1 WHERE id = ?");

    foreach ($unpurged as $row) {
        $fullPath = $storageBase . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $row['resume_relative_path']);
        $realPath = realpath($fullPath);
        // Ensure target path is strictly contained within storage directory to prevent path traversal
        if ($realPath && str_starts_with($realPath, $storageBase) && file_exists($realPath)) {
            $handledPaths[$realPath] = true;
            if ($isDryRun) {
                echo sprintf("  [WOULD DELETE FILE] %s (scan id: %d)\n", basename($realPath), $row['id']);
                $purgedFileCount++;
            } else {
                if (@unlink($realPath)) {
                    $purgedFileCount++;
                    $updatePurgedStmt->execute([$row['id']]);
                } else {
                    error_log(sprintf('[CLEANUP_WARN] Failed to unlink file %s for scan id %d', $realPath, $row['id']));
                }
            }
        } else {
            // File already absent from disk; mark purged so it is not re-queried indefinitely
            if (!$isDryRun) {
                $updatePurgedStmt->execute([$row['id']]);
            }
        }

        // Also purge sidecar .extracted.txt file if present
        if (!empty($row['uuid'])) {
            $sidecar = $uploadsDir . DIRECTORY_SEPARATOR . $row['uuid'] . '.extracted.txt';
            $realSidecar = realpath($sidecar);
            if ($realSidecar && str_starts_with($realSidecar, $storageBase) && file_exists($realSidecar)) {
                $handledPaths[$realSidecar] = true;
                if ($isDryRun) {
                    echo sprintf("  [WOULD DELETE FILE] %s (sidecar for scan id: %d)\n", basename($realSidecar), $row['id']);
                    $purgedFileCount++;
                } else {
                    if (@unlink($realSidecar)) {
                        $purgedFileCount++;
                    } else {
                        error_log(sprintf('[CLEANUP_WARN] Failed to unlink sidecar %s for scan id %d', $realSidecar, $row['id']));
                    }
                }
            }
        }
    }

    // Sweep orphaned upload files older than 2 hours
    $uploadFiles = array_unique(array_merge(
        glob($uploadsDir . DIRECTORY_SEPARATOR . '*.pdf') ?: [],
        glob($uploadsDir . DIRECTORY_SEPARATOR . '*.txt') ?: []
    ));
    foreach ($uploadFiles as $uploadFile) {
        $realUpload = realpath($uploadFile);
        if (!$realUpload) {
            continue;
        }
        if (isset($handledPaths[$realUpload]) || isset($protectedPaths[$realUpload])) {
            // Skip files already handled or belonging to active scans
            continue;
        }
        if (($now - filemtime($uploadFile)) >= 7200) {
            if ($isDryRun) {
                echo sprintf("  [WOULD DELETE ORPHAN] %s\n", basename($uploadFile));
                $purgedFileCount++;
            } else {
                if (@unlink($uploadFile)) {
                    $purgedFileCount++;
                } else {
                    error_log(sprintf('[CLEANUP_WARN] Failed to unlink orphaned file %s', $uploadFile));
                }
            }
        }
    }

    // Purge execution logs older than 2 hours
    $logFiles = glob($logsDir . DIRECTORY_SEPARATOR . '*.log');
    if ($logFiles) {
        foreach ($logFiles as $logFile) {
            if (($now - filemtime($logFile)) >= 7200) {
                if ($isDryRun) {
                    echo sprintf("  [WOULD DELETE LOG]  %s\n", basename($logFile));
                    $purgedLogCount++;
                } else {
                    if (@unlink($logFile)) {
                        $purgedLogCount++;
                    } else {
                        error_log(sprintf('[CLEANUP_WARN] Failed to unlink log file %s', $logFile));
                    }
                }
            }
        }
    }

    // Purge scan database records older than 30 days
    $countStmt = $pdo->query("SELECT COUNT(*) FROM scans WHERE created_at < NOW() - INTERVAL 30 DAY");
    $eligibleRows = (int)$countStmt->fetchColumn();

    if ($isDryRun) {
        if ($eligibleRows > 0) {
            echo sprintf("  [WOULD PURGE DB]   %d records older than 30 days\n", $eligibleRows);
        }
        $purgedRowCount = $eligibleRows;
    } else {
        $deleteStmt = $pdo->query("DELETE FROM scans WHERE created_at < NOW() - INTERVAL 30 DAY");
        $purgedRowCount = $deleteStmt->rowCount();
    }

    if ($isDryRun) {
        echo sprintf("\n[DRY RUN SUMMARY] %d file(s), %d log(s), %d DB record(s) eligible for purge.\n", $purgedFileCount, $purgedLogCount, $purgedRowCount);
    } else {
        echo sprintf("Cleanup completed: %d files purged, %d logs purged, %d DB records purged.\n", $purgedFileCount, $purgedLogCount, $purgedRowCount);
    }
} finally {
    if ($lockHandle) {
        flock($lockHandle, LOCK_UN);
        fclose($lockHandle);
    }
}
