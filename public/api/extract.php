<?php
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    ini_set('display_errors', '0');
}

header('Content-Type: application/json');
header('Cache-Control: no-store, private, max-age=0');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');

// Load environment configuration
require_once __DIR__ . '/../../config/database.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'success' => false,
        'error' => 'Method not allowed. Use POST.'
    ]);
    exit;
}

// Fair-use extraction rate limiting
$rawIp = $_SERVER['REMOTE_ADDR'] ?? '127.0.0.1';
$isLocalhost = in_array($rawIp, ['127.0.0.1', '::1', 'localhost'], true);
$appEnv = strtolower(trim((string)($_ENV['APP_ENV'] ?? 'development')));
$forceRateLimit = filter_var($_ENV['FORCE_RATE_LIMIT'] ?? false, FILTER_VALIDATE_BOOLEAN);
$isDev = ($appEnv === 'development' || $isLocalhost) && !$forceRateLimit;

$clientToken = trim($_POST['client_token'] ?? $_SERVER['HTTP_X_CLIENT_TOKEN'] ?? '');
if (empty($clientToken) || !preg_match('/^[a-f0-9]{32}$/', $clientToken)) {
    $clientToken = 'anonymous';
}

if (filter_var($rawIp, FILTER_VALIDATE_IP, FILTER_FLAG_IPV6)) {
    $packed = inet_pton($rawIp);
    if ($packed !== false && strlen($packed) === 16) {
        $subnet = inet_ntop(substr($packed, 0, 8) . str_repeat("\0", 8));
    } else {
        $subnet = $rawIp;
    }
} else {
    $subnet = preg_replace('/\.\d+$/', '.0', $rawIp);
}
$ipSubnetHash = hash('sha256', (string)$subnet);

$maxDailyExtractions = (int)($_ENV['MAX_DAILY_SCANS_PER_USER'] ?? 20) * 2;
if (!$isDev && isset($pdo)) {
    $rateStmt = $pdo->prepare("SELECT COUNT(*) FROM scans WHERE (client_token = ? OR ip_subnet = ?) AND created_at > NOW() - INTERVAL 1 DAY");
    $rateStmt->execute([$clientToken, $ipSubnetHash]);
    if ((int)$rateStmt->fetchColumn() >= $maxDailyExtractions) {
        http_response_code(429);
        echo json_encode([
            'success' => false,
            'error' => 'Daily document extraction limit reached. Please try again tomorrow.'
        ]);
        exit;
    }
}

// Verify upload presence
if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
    http_response_code(422);
    echo json_encode([
        'success' => false,
        'error' => 'No file was provided or upload encountered a transport error.'
    ]);
    exit;
}

$uploadedFile = $_FILES['file'];
$maxSizeBytes = (int)($_ENV['MAX_FILE_SIZE_BYTES'] ?? (10 * 1024 * 1024));

// Validate file size
if ($uploadedFile['size'] > $maxSizeBytes) {
    http_response_code(413);
    echo json_encode([
        'success' => false,
        'error' => sprintf('File exceeds maximum allowed size of %dMB.', (int)($maxSizeBytes / (1024 * 1024)))
    ]);
    exit;
}

$origName = basename($uploadedFile['name']);
$lowerName = strtolower($origName);
$tmpPath = $uploadedFile['tmp_name'];

// Resolve Python executable
$pythonBin = $_ENV['PYTHON_BIN'] ?? 'python';
if ($pythonBin === 'python') {
    $winVenv = realpath(__DIR__ . '/../../engine/venv/Scripts/python.exe');
    $linVenv = realpath(__DIR__ . '/../../engine/venv/bin/python');
    if ($winVenv && file_exists($winVenv)) {
        $pythonBin = $winVenv;
    } elseif ($linVenv && file_exists($linVenv)) {
        $pythonBin = $linVenv;
    }
}

$extractedText = '';
$wordCount = 0;
$pageCount = 1;

try {
    if (str_ends_with($lowerName, '.pdf')) {
        // Inspect magic bytes for PDF signature
        $fh = fopen($tmpPath, 'rb');
        $header = fread($fh, 5);
        fclose($fh);
        if ($header !== '%PDF-') {
            http_response_code(400);
            echo json_encode([
                'success' => false,
                'error' => 'Security Error: File does not match valid PDF document signatures.'
            ]);
            exit;
        }

        // Execute layout-aware extraction engine with process timeout
        $parserScript = realpath(__DIR__ . '/../../engine/parsers/pdf_parser.py');
        if (!$parserScript || !file_exists($parserScript)) {
            throw new RuntimeException('PDF parser script is not accessible on the server.');
        }

        $cmd = sprintf('%s %s %s --json', escapeshellarg($pythonBin), escapeshellarg($parserScript), escapeshellarg($tmpPath));
        $descriptors = [
            0 => ['pipe', 'r'],
            1 => ['pipe', 'w'],
            2 => ['pipe', 'w']
        ];
        $process = proc_open($cmd, $descriptors, $pipes);
        $rawOutput = '';
        $rawError = '';
        $retCode = -1;

        if (is_resource($process)) {
            fclose($pipes[0]);
            stream_set_blocking($pipes[1], false);
            stream_set_blocking($pipes[2], false);

            $timeoutSeconds = 20;
            $startTime = microtime(true);

            while (true) {
                $status = proc_get_status($process);
                $rawOutput .= stream_get_contents($pipes[1]);
                $rawError  .= stream_get_contents($pipes[2]);

                if (!$status['running']) {
                    $retCode = $status['exitcode'];
                    break;
                }

                if ((microtime(true) - $startTime) > $timeoutSeconds) {
                    proc_terminate($process, 9);
                    fclose($pipes[1]);
                    fclose($pipes[2]);
                    proc_close($process);
                    http_response_code(504);
                    echo json_encode([
                        'success' => false,
                        'error' => 'Document parsing timed out (exceeded 20 seconds limit). Please ensure the file is not corrupted.'
                    ]);
                    exit;
                }
                usleep(30000); // 30ms polling interval
            }
            fclose($pipes[1]);
            fclose($pipes[2]);
            proc_close($process);
            $rawOutput = trim($rawOutput);
        } else {
            throw new RuntimeException('Failed to launch PDF parser subprocess.');
        }

        if ($retCode !== 0) {
            http_response_code(422);
            $cleanErr = 'We could not detect selectable text in your PDF. Scanned or image-only PDFs are not supported.';
            if (!empty($rawOutput) && !str_contains(strtolower($rawOutput), 'scanned or image-only')) {
                $cleanErr = 'PDF extraction error: ' . $rawOutput;
            }
            echo json_encode([
                'success' => false,
                'error' => $cleanErr
            ]);
            exit;
        }

        $parsedJson = json_decode($rawOutput, true);
        if (!is_array($parsedJson) || !isset($parsedJson['text'])) {
            http_response_code(422);
            echo json_encode([
                'success' => false,
                'error' => 'Parser returned invalid structure for the uploaded PDF.'
            ]);
            exit;
        }

        $extractedText = trim((string)$parsedJson['text']);
        $wordCount = (int)($parsedJson['word_count'] ?? count(preg_split('/\s+/', $extractedText, -1, PREG_SPLIT_NO_EMPTY)));
        $pageCount = (int)($parsedJson['page_count'] ?? 1);

    } elseif (str_ends_with($lowerName, '.txt') || str_ends_with($lowerName, '.md')) {
        // Process plaintext or markdown input
        $rawText = (string)file_get_contents($tmpPath);
        // Strip UTF-8 BOM if present
        $rawText = preg_replace('/^\xEF\xBB\xBF/', '', $rawText);
        if (!mb_check_encoding($rawText, 'UTF-8')) {
            $converted = mb_convert_encoding($rawText, 'UTF-8', 'auto');
            if ($converted !== false) {
                $rawText = $converted;
            }
        }

        $extractedText = trim($rawText);
        $words = preg_split('/\s+/', $extractedText, -1, PREG_SPLIT_NO_EMPTY);
        $wordCount = count($words);
        $pageCount = 1;

        if ($wordCount < 50) {
            http_response_code(422);
            echo json_encode([
                'success' => false,
                'error' => 'Document contains too little readable text (minimum 50 words required).'
            ]);
            exit;
        }
    } else {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'Unsupported file format. Please upload a PDF, TXT, or Markdown document.'
        ]);
        exit;
    }

    $characterCount = mb_strlen($extractedText);

    // Return extraction result payload
    http_response_code(200);
    echo json_encode([
        'success'         => true,
        'filename'        => $origName,
        'file_size'       => (int)$uploadedFile['size'],
        'page_count'      => $pageCount,
        'word_count'      => $wordCount,
        'character_count' => $characterCount,
        'extracted_text'  => $extractedText
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

} catch (\Throwable $e) {
    error_log(sprintf('[EXTRACT_EXCEPTION] %s in %s:%d', $e->getMessage(), $e->getFile(), $e->getLine()));
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'An unexpected error occurred during document extraction. Please ensure the file is a valid digital document.'
    ]);
}
