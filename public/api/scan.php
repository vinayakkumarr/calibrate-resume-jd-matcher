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

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed. Use POST.']);
    exit;
}

// Resolve environment and client network
$rawIp = $_SERVER['REMOTE_ADDR'] ?? '127.0.0.1';
$isLocalhost = in_array($rawIp, ['127.0.0.1', '::1', 'localhost'], true);
$appEnv = strtolower(trim((string)env('APP_ENV', 'development')));
$forceRateLimit = filter_var(env('FORCE_RATE_LIMIT', 'false'), FILTER_VALIDATE_BOOLEAN);
$isDev = ($appEnv === 'development' || $isLocalhost) && !$forceRateLimit;

try {
    // Enforce global system daily scan quota (bypassed in local development)
    $systemDailyCap = (int)env('SYSTEM_DAILY_SCAN_CAP', '1400');
    if (!$isDev) {
        $globalStmt = $pdo->query("SELECT COUNT(*) FROM scans WHERE created_at > NOW() - INTERVAL 1 DAY");
        if ((int)$globalStmt->fetchColumn() >= $systemDailyCap) {
            http_response_code(429);
            echo json_encode(['error' => sprintf('Daily community capacity reached (%d/%d). Please try again tomorrow.', $systemDailyCap, $systemDailyCap)]);
            exit;
        }
    }

    // Client token and subnet rate limiting (bypassed in local development)
    $maxDailyPerUser = (int)env('MAX_DAILY_SCANS_PER_USER', '20');
    $clientToken = trim($_POST['client_token'] ?? '');
    if (empty($clientToken)) {
        $clientToken = bin2hex(random_bytes(16));
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

    if (!$isDev) {
        $rateStmt = $pdo->prepare("SELECT COUNT(*) FROM scans WHERE (client_token = ? OR ip_subnet = ?) AND created_at > NOW() - INTERVAL 1 DAY");
        $rateStmt->execute([$clientToken, $ipSubnetHash]);
        if ((int)$rateStmt->fetchColumn() >= $maxDailyPerUser) {
            http_response_code(429);
            echo json_encode(['error' => sprintf('Daily free limit reached (%d/%d scans). Limit resets 24 hours after your first scan.', $maxDailyPerUser, $maxDailyPerUser)]);
            exit;
        }
    }

    // Resolve Python executable for parser and analyzer processes
    $pythonBin = env('PYTHON_BIN', 'python');
    if ($pythonBin === 'python') {
        $baseDir = dirname(__DIR__, 2);
        $winVenv = $baseDir . '/engine/venv/Scripts/python.exe';
        $linVenv = $baseDir . '/engine/venv/bin/python';
        if (file_exists($winVenv)) {
            $pythonBin = $winVenv;
        } elseif (file_exists($linVenv)) {
            $pythonBin = $linVenv;
        }
    }

    require_once __DIR__ . '/validation_helpers.php';

    // Job description ingestion and validation
    $maxSizeBytes = (int)env('MAX_FILE_SIZE_BYTES', (string)(10 * 1024 * 1024));
    $minInputChars = (int)env('MIN_INPUT_CHARS', '80');
    $maxResumeChars = (int)env('MAX_RESUME_CHARS', '25000');
    $maxJdChars = (int)env('MAX_JD_CHARS', '15000');
$jobDescription = '';
$jdMode = trim((string)($_POST['jd_mode'] ?? ''));

$hasJdFile = isset($_FILES['job_description_file']) && $_FILES['job_description_file']['error'] === UPLOAD_ERR_OK;

if (($jdMode === 'file' || empty($_POST['job_description'])) && $hasJdFile) {
    $jdFile = $_FILES['job_description_file'];
    if ($jdFile['size'] > $maxSizeBytes) {
        http_response_code(413);
        echo json_encode(['error' => sprintf('Job description file exceeds maximum allowed size of %dMB.', (int)($maxSizeBytes / (1024 * 1024)))]);
        exit;
    }

    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    $jdMime = finfo_file($finfo, $jdFile['tmp_name']);
    finfo_close($finfo);

    $origName = strtolower($jdFile['name']);
    if (str_ends_with($origName, '.pdf')) {
        $allowedPdfMimes = ['application/pdf', 'application/x-pdf', 'application/octet-stream'];
        if ($jdMime && !in_array($jdMime, $allowedPdfMimes, true)) {
            http_response_code(400);
            echo json_encode(['error' => 'Security Error: Job description file MIME type is invalid. Expected PDF document.']);
            exit;
        }

        $fh = fopen($jdFile['tmp_name'], 'rb');
        $header = fread($fh, 5);
        fclose($fh);
        if ($header !== '%PDF-') {
            http_response_code(400);
            echo json_encode(['error' => 'Security Error: Job description file is not a valid PDF document.']);
            exit;
        }

        $parserScript = realpath(__DIR__ . '/../../engine/parsers/pdf_parser.py');
        $cmd = sprintf('%s %s %s', escapeshellarg($pythonBin), escapeshellarg($parserScript), escapeshellarg($jdFile['tmp_name']));
        $output = [];
        $retCode = 0;
        exec($cmd, $output, $retCode);
        if ($retCode !== 0) {
            http_response_code(422);
            $errLine = trim(implode(' ', $output));
            echo json_encode(['error' => 'Could not extract text from Job Description PDF. ' . ($errLine ?: 'Please upload a selectable digital PDF.')]);
            exit;
        }
        $jobDescription = trim(implode("\n", $output));
    } elseif (str_ends_with($origName, '.txt') || str_ends_with($origName, '.md')) {
        $rawText = (string)file_get_contents($jdFile['tmp_name']);
        // Strip UTF-8 Byte Order Mark (BOM) if present from Windows text editors
        $rawText = preg_replace('/^\xEF\xBB\xBF/', '', $rawText);
        // Ensure valid UTF-8 string encoding
        if (!mb_check_encoding($rawText, 'UTF-8')) {
            $converted = mb_convert_encoding($rawText, 'UTF-8', 'auto');
            if ($converted !== false) {
                $rawText = $converted;
            }
        }
        $jobDescription = trim($rawText);
    } else {
        http_response_code(400);
        echo json_encode(['error' => 'Unsupported job description file format. Please upload a PDF or TXT file.']);
        exit;
    }
} elseif (!empty($_POST['job_description'])) {
    $jobDescription = trim((string)$_POST['job_description']);
}


if (empty($jobDescription)) {
    http_response_code(422);
    echo json_encode(['error' => 'Both a resume (PDF or text) and a job description (text or file) are required.']);
    exit;
}

if (mb_strlen($jobDescription) < $minInputChars) {
    http_response_code(422);
    echo json_encode(['error' => sprintf('Job description is too short (minimum %d characters required).', $minInputChars)]);
    exit;
}
if (mb_strlen($jobDescription) > $maxJdChars) {
    http_response_code(422);
    echo json_encode(['error' => sprintf('Job description exceeds maximum limit of %s characters.', number_format($maxJdChars))]);
    exit;
}

// Resume ingestion and validation
$resumeMode = trim((string)($_POST['resume_mode'] ?? ''));
$hasResumeFile = isset($_FILES['resume']) && $_FILES['resume']['error'] === UPLOAD_ERR_OK;
$hasResumeText = !empty($_POST['resume_text']);

if (!$hasResumeFile && !$hasResumeText) {
    http_response_code(422);
    echo json_encode(['error' => 'Both a resume (PDF or text) and a job description (text or file) are required.']);
    exit;
}

// Extract and validate candidate resume content before creating file artifacts or scan records
$resumeTextContent = null;
$isPdfResume = false;
$resumeOriginalName = '';
$uploadedResumeFile = null;

if (($resumeMode === 'text' || !$hasResumeFile) && $hasResumeText) {
    $resumeText = trim((string)$_POST['resume_text']);
    $resumeText = preg_replace('/^\xEF\xBB\xBF/', '', $resumeText);
    if (!mb_check_encoding($resumeText, 'UTF-8')) {
        $converted = mb_convert_encoding($resumeText, 'UTF-8', 'auto');
        if ($converted !== false) {
            $resumeText = $converted;
        }
    }
    $resumeText = trim($resumeText);
    if (mb_strlen($resumeText) < $minInputChars) {
        http_response_code(422);
        echo json_encode(['error' => sprintf('Resume text is too short (minimum %d characters required).', $minInputChars)]);
        exit;
    }
    if (mb_strlen($resumeText) > $maxResumeChars) {
        http_response_code(422);
        echo json_encode(['error' => sprintf('Resume text exceeds maximum limit of %s characters.', number_format($maxResumeChars))]);
        exit;
    }
    $resumeTextContent = $resumeText;
    $resumeOriginalName = 'Pasted Resume Text';
} elseif ($hasResumeFile) {
    $file = $_FILES['resume'];
    if ($file['size'] > $maxSizeBytes) {
        http_response_code(413);
        echo json_encode(['error' => sprintf('Resume file exceeds maximum allowed size of %dMB.', (int)($maxSizeBytes / (1024 * 1024)))]);
        exit;
    }

    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    $resumeMime = finfo_file($finfo, $file['tmp_name']);
    finfo_close($finfo);

    $origName = strtolower($file['name']);
    if (str_ends_with($origName, '.pdf')) {
        $allowedPdfMimes = ['application/pdf', 'application/x-pdf', 'application/octet-stream'];
        if ($resumeMime && !in_array($resumeMime, $allowedPdfMimes, true)) {
            http_response_code(400);
            echo json_encode(['error' => 'Security Error: File MIME type is invalid. Expected PDF document.']);
            exit;
        }

        $fh = fopen($file['tmp_name'], 'rb');
        $header = fread($fh, 5);
        fclose($fh);
        if ($header !== '%PDF-') {
            http_response_code(400);
            echo json_encode(['error' => 'Security Error: File is not a valid PDF document.']);
            exit;
        }

        // Fast-path duplicate file check: If both resume and JD were uploaded as files with identical SHA-256
        if ($hasJdFile && hash_file('sha256', $file['tmp_name']) === hash_file('sha256', $_FILES['job_description_file']['tmp_name'])) {
            http_response_code(422);
            echo json_encode(['error' => "The Resume and Job Description appear to contain the same text. Please check that the Resume field contains the candidate's resume and the Job Description field contains the job posting."]);
            exit;
        }

        // Extract layout text from PDF to compare against Job Description text
        $parserScript = realpath(__DIR__ . '/../../engine/parsers/pdf_parser.py');
        $cmd = sprintf('%s %s %s', escapeshellarg($pythonBin), escapeshellarg($parserScript), escapeshellarg($file['tmp_name']));
        $pdfOut = [];
        $pdfRet = 0;
        exec($cmd, $pdfOut, $pdfRet);
        if ($pdfRet === 0) {
            $resumeTextContent = trim(implode("\n", $pdfOut));
        }

        $isPdfResume = true;
        $uploadedResumeFile = $file;
        $resumeOriginalName = basename($file['name']);
    } elseif (str_ends_with($origName, '.txt') || str_ends_with($origName, '.md')) {
        $rawText = (string)file_get_contents($file['tmp_name']);
        $rawText = preg_replace('/^\xEF\xBB\xBF/', '', $rawText);
        if (!mb_check_encoding($rawText, 'UTF-8')) {
            $converted = mb_convert_encoding($rawText, 'UTF-8', 'auto');
            if ($converted !== false) {
                $rawText = $converted;
            }
        }
        $rawText = trim($rawText);
        if (mb_strlen($rawText) < $minInputChars) {
            http_response_code(422);
            echo json_encode(['error' => sprintf('Resume text file is too short (minimum %d characters required).', $minInputChars)]);
            exit;
        }
        if (mb_strlen($rawText) > $maxResumeChars) {
            http_response_code(422);
            echo json_encode(['error' => sprintf('Resume text file exceeds maximum limit of %s characters.', number_format($maxResumeChars))]);
            exit;
        }
        $resumeTextContent = $rawText;
        $resumeOriginalName = basename($file['name']);
    } else {
        http_response_code(400);
        echo json_encode(['error' => 'Unsupported resume file format. Please upload a PDF or TXT file.']);
        exit;
    }
}

// Reject identical inputs before scan creation or processing
if ($resumeTextContent !== null && areInputsIdentical($resumeTextContent, $jobDescription)) {
    http_response_code(422);
    echo json_encode(['error' => "The Resume and Job Description appear to contain the same text. Please check that the Resume field contains the candidate's resume and the Job Description field contains the job posting."]);
    exit;
}

// Persist resume artifact to storage
$uuid = bin2hex(random_bytes(16));
$uploadDir = __DIR__ . '/../../storage/uploads/';
$logDir    = __DIR__ . '/../../storage/logs/';
$logFilePath = $logDir . $uuid . '.log';
$relativeFilePath = '';

if ($isPdfResume && $uploadedResumeFile !== null) {
    $relativeFilePath = 'uploads/' . $uuid . '.pdf';
    $absoluteFilePath = $uploadDir . $uuid . '.pdf';
    if (!move_uploaded_file($uploadedResumeFile['tmp_name'], $absoluteFilePath)) {
        http_response_code(500);
        echo json_encode(['error' => 'Failed to store uploaded file on server.']);
        exit;
    }
    if (function_exists('chmod') && strtoupper(substr(PHP_OS, 0, 3)) !== 'WIN') {
        chmod($absoluteFilePath, 0600);
    }
    // Cache pre-extracted text to avoid re-parsing the PDF in the worker process
    if ($resumeTextContent !== null && mb_strlen($resumeTextContent) >= 80) {
        $extractedFilePath = $uploadDir . $uuid . '.extracted.txt';
        file_put_contents($extractedFilePath, $resumeTextContent);
        if (function_exists('chmod') && strtoupper(substr(PHP_OS, 0, 3)) !== 'WIN') {
            chmod($extractedFilePath, 0600);
        }
    }
} else {
    $relativeFilePath = 'uploads/' . $uuid . '.txt';
    $absoluteFilePath = $uploadDir . $uuid . '.txt';
    if (file_put_contents($absoluteFilePath, $resumeTextContent) === false) {
        http_response_code(500);
        echo json_encode(['error' => 'Failed to store resume text on server.']);
        exit;
    }
    if (function_exists('chmod') && strtoupper(substr(PHP_OS, 0, 3)) !== 'WIN') {
        chmod($absoluteFilePath, 0600);
    }
}


// Record pending scan in database
$insertStmt = $pdo->prepare("
    INSERT INTO scans (uuid, client_token, ip_subnet, resume_original_name, resume_relative_path, job_description, status)
    VALUES (?, ?, ?, ?, ?, ?, 'pending')
");
$insertStmt->execute([
    $uuid,
    $clientToken,
    $ipSubnetHash,
    $resumeOriginalName,
    $relativeFilePath,
    $jobDescription
]);

// Launch background analyzer worker
$engineScript = realpath(__DIR__ . '/../../engine/analyzer.py');
if (!$engineScript) {
    // Fallback to relative path if realpath fails
    $engineScript = __DIR__ . '/../../engine/analyzer.py';
}

if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
    // Launch detached process on Windows
    $cmd = sprintf(
        'start "" /B %s %s --uuid %s > %s 2>&1',
        escapeshellarg($pythonBin),
        escapeshellarg($engineScript),
        escapeshellarg($uuid),
        escapeshellarg($logFilePath)
    );
    pclose(popen($cmd, "r"));
} else {
    // Launch detached process on POSIX systems
    $cmd = sprintf(
        '%s %s --uuid %s > %s 2>&1 &',
        escapeshellcmd($pythonBin),
        escapeshellarg($engineScript),
        escapeshellarg($uuid),
        escapeshellarg($logFilePath)
    );
    exec($cmd);
}

// Return accepted status ticket
http_response_code(202);
echo json_encode([
    'uuid'         => $uuid,
    'client_token' => $clientToken,
    'status'       => 'pending',
    'message'      => 'Resume accepted. Processing started in background.'
]);
} catch (\Throwable $e) {
    error_log(sprintf('[SCAN_ERROR] %s in %s:%d', $e->getMessage(), $e->getFile(), $e->getLine()));
    http_response_code(500);
    $debug = filter_var(env('APP_DEBUG', 'false'), FILTER_VALIDATE_BOOLEAN);
    $message = $debug ? $e->getMessage() : 'An unexpected server error occurred during scan processing. Please try again.';
    echo json_encode(['error' => $message]);
    exit;
}
