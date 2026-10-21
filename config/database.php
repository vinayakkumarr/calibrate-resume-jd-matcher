<?php
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    ini_set('display_errors', '0');
}

/**
 * Resolves runtime configuration values across $_ENV, $_SERVER, and getenv().
 * Normalizes values by trimming whitespace and stripping accidental wrapping quotes.
 */
function env(string $key, ?string $default = null): ?string {
    $val = $_ENV[$key] ?? $_SERVER[$key] ?? getenv($key);
    if ($val === false || $val === null || $val === '') {
        return $default;
    }
    $val = trim((string)$val);
    if (strlen($val) >= 2 && (($val[0] === '"' && substr($val, -1) === '"') || ($val[0] === "'" && substr($val, -1) === "'"))) {
        $val = substr($val, 1, -1);
    }
    return $val;
}

// Ingest local development .env definitions when executing outside containerized runtimes
$envPath = __DIR__ . '/../.env';
if (file_exists($envPath)) {
    $lines = file($envPath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        $trimmed = trim($line);
        if ($trimmed === '' || str_starts_with($trimmed, '#') || !str_contains($trimmed, '=')) {
            continue;
        }
        [$name, $value] = explode('=', $trimmed, 2);
        $cleanVal = trim($value);
        if (strlen($cleanVal) >= 2 && (($cleanVal[0] === '"' && substr($cleanVal, -1) === '"') || ($cleanVal[0] === "'" && substr($cleanVal, -1) === "'"))) {
            $cleanVal = substr($cleanVal, 1, -1);
        }
        $_ENV[trim($name)] = $cleanVal;
    }
}

// Database connection parameters with local development defaults
$host = env('DB_HOST', '127.0.0.1');
$port = env('DB_PORT', '3306');
$db   = env('DB_NAME', 'jd_analyser');
$user = env('DB_USER', 'root');
$pass = env('DB_PASS', '');

$dsn = "mysql:host={$host};port={$port};dbname={$db};charset=utf8mb4";
$options = [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES   => false,
    PDO::ATTR_TIMEOUT            => 5, // 5-second fast-fail threshold preventing worker thread starvation
    PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
];

// TLS encryption configuration for managed cloud database instances
$useSsl = filter_var(env('DB_SSL', 'false'), FILTER_VALIDATE_BOOLEAN);
if ($useSsl) {
    $caPath = env('DB_SSL_CA', '/etc/ssl/certs/ca-certificates.crt');
    if (file_exists($caPath)) {
        $options[PDO::MYSQL_ATTR_SSL_CA] = $caPath;
    }
    $options[PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT] = false;
}

try {
    $pdo = new PDO($dsn, $user, $pass, $options);
} catch (PDOException $e) {
    // Emit structured diagnostic to stderr stream for cloud log ingestion without credential exposure
    error_log(sprintf('[DB_CONNECT_FAIL] Host=%s Port=%s DB=%s Error=%s', $host, $port, $db, $e->getMessage()));
    
    if (PHP_SAPI === 'cli') {
        fwrite(STDERR, "Database connection failed: " . $e->getMessage() . "\n");
    } else {
        http_response_code(500);
        header('Content-Type: application/json');
        echo json_encode(['error' => 'Database connection failed. Please verify cloud database status.']);
    }
    exit(1);
}
