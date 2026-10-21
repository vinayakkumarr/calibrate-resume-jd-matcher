<?php
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    ini_set('display_errors', '0');
}

header('Content-Type: application/json');
header('Cache-Control: no-store, private, max-age=0');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
require_once __DIR__ . '/../../config/database.php';

function sanitizePublicErrorMessage(?string $error): ?string {
    if ($error === null || $error === '') {
        return null;
    }
    // Defense-in-depth: if error contains file paths, SQL details, or stack traces, return safe generic error
    if (preg_match('/[A-Za-z]:\\\\|\/(?:var|tmp|home|etc|usr|opt|www|storage|engine)\/|SQLSTATE|PDOException|Table \'|\.php on line|\.py line/i', $error)) {
        return 'An unexpected processing error occurred while analyzing the document. Your inputs were preserved.';
    }
    return $error;
}

$uuid = trim($_GET['uuid'] ?? '');
if (empty($uuid) || !preg_match('/^[a-f0-9]{32}$/', $uuid)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid or missing scan UUID.']);
    exit;
}

// Client token authorization via X-Client-Token HTTP header
$clientToken = trim($_SERVER['HTTP_X_CLIENT_TOKEN'] ?? '');
if (empty($clientToken) || !preg_match('/^[a-f0-9]{32}$/', $clientToken)) {
    http_response_code(403);
    echo json_encode(['error' => 'Unauthorized: Missing or invalid client token. Header X-Client-Token is required.']);
    exit;
}



try {
    $stmt = $pdo->prepare("
        SELECT s.id, s.status, s.error_message, s.created_at,
               TIMESTAMPDIFF(SECOND, s.created_at, NOW()) AS age_seconds,
               r.overall_score, r.must_have_score, r.bonus_score, r.experience_score, r.analysis_payload
        FROM scans s
        LEFT JOIN scan_results r ON s.id = r.scan_id
        WHERE s.uuid = ? AND s.client_token = ?
    ");
    $stmt->execute([$uuid, $clientToken]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$row) {
        http_response_code(404);
        echo json_encode(['error' => 'Scan ticket not found or unauthorized.']);
        exit;
    }

    // Auto-fail stalled scans exceeding the configured watchdog timeout
    if (in_array($row['status'], ['pending', 'processing'], true)) {
        $ageSeconds = isset($row['age_seconds']) ? (int)$row['age_seconds'] : (time() - strtotime($row['created_at']));
        $watchdogTimeout = (int)env('WATCHDOG_TIMEOUT_SECONDS', '90');
        if ($ageSeconds > $watchdogTimeout) {
            $timeoutMsg = sprintf('Analysis timed out (exceeded %d seconds limit).', $watchdogTimeout);
            $failStmt = $pdo->prepare("UPDATE scans SET status = 'failed', error_message = ? WHERE id = ?");
            $failStmt->execute([$timeoutMsg, $row['id']]);
            $row['status'] = 'failed';
            $row['error_message'] = $timeoutMsg;
        }
    }

    // Build status response payload
    $response = [
        'uuid'             => $uuid,
        'status'           => $row['status'],
        'error_message'    => sanitizePublicErrorMessage($row['error_message']),
        'progress_message' => null,
        'scores'           => null,
        'report'           => null
    ];

    if ($row['status'] === 'pending') {
        $response['progress_message'] = '1/3 Queued: Extracting layout & normalizing text...';
    } elseif ($row['status'] === 'processing') {
        $response['progress_message'] = '2/3 Auditing qualification evidence against role requirements...';
    } elseif ($row['status'] === 'completed' && !empty($row['analysis_payload'])) {
        $response['progress_message'] = '3/3 Analysis complete!';
        $report = json_decode($row['analysis_payload'], true);
        $reqStatus = $report['experience_years']['requirement_status'] ?? null;
        $expScore = ($reqStatus === 'NOT_SPECIFIED' || $reqStatus === 'EXTRACTION_FAILED')
            ? null
            : (isset($row['experience_score']) ? (float)$row['experience_score'] : null);

        $bonusExcluded = !empty($report['scores']['bonus_excluded']) 
            || (isset($report['scores']['bonus_score']) && $report['scores']['bonus_score'] === null)
            || (empty($report['bonus_skills']));
        $bonusScore = $bonusExcluded
            ? null
            : (isset($row['bonus_score']) ? (float)$row['bonus_score'] : null);

        $rawScore = isset($report['scores']['raw_score'])
            ? (float)$report['scores']['raw_score']
            : (float)$row['overall_score'];
        $isGated = !empty($report['scores']['is_gated']);

        // Defensive fallback: if is_gated not stored in payload, derive mathematically from scores
        if (!$isGated && isset($row['must_have_score']) && (float)$row['must_have_score'] > 0 && (float)$row['must_have_score'] < 50.0) {
            $gateThreshold = (float)env('ESSENTIAL_SKILL_GATE_THRESHOLD', '50.0');
            $minMult = (float)env('MIN_GATE_MULTIPLIER', '0.15');
            $calcMult = max($minMult, round((float)$row['must_have_score'] / $gateThreshold, 4));
            if ($calcMult < 1.0) {
                $isGated = true;
                if ($calcMult > 0 && $rawScore <= (float)$row['overall_score']) {
                    $rawScore = round((float)$row['overall_score'] / $calcMult, 2);
                }
            }
        }

        $response['scores'] = [
            'overall_score'    => (float)$row['overall_score'],
            'raw_score'        => $rawScore,
            'is_gated'         => $isGated,
            'must_have_score'  => (float)$row['must_have_score'],
            'bonus_score'      => $bonusScore,
            'experience_score' => $expScore
        ];
        $response['report'] = $report;
    }

    echo json_encode($response);
} catch (\Throwable $e) {
    error_log(sprintf('[STATUS_ERROR] %s in %s:%d', $e->getMessage(), $e->getFile(), $e->getLine()));
    http_response_code(500);
    $debug = filter_var(env('APP_DEBUG', 'false'), FILTER_VALIDATE_BOOLEAN);
    $message = $debug ? $e->getMessage() : 'An unexpected error occurred while checking scan status.';
    echo json_encode(['error' => $message]);
    exit;
}
