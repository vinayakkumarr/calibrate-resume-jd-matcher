CREATE DATABASE IF NOT EXISTS jd_analyser 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE jd_analyser;

-- Scans tracking and lifecycle table
CREATE TABLE IF NOT EXISTS scans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    client_token VARCHAR(64) NOT NULL,
    ip_subnet VARCHAR(64) NOT NULL,
    resume_original_name VARCHAR(255) NOT NULL,
    resume_relative_path VARCHAR(255) NOT NULL,
    job_description MEDIUMTEXT NOT NULL,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    error_message VARCHAR(255) NULL,
    is_purged TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_uuid (uuid),
    INDEX idx_client_lookup (client_token, created_at),
    INDEX idx_status_created (status, created_at),
    INDEX idx_ip_subnet (ip_subnet, created_at)
) ENGINE=InnoDB;

-- Scan results and structured payload storage
CREATE TABLE IF NOT EXISTS scan_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scan_id INT NOT NULL UNIQUE,
    overall_score DECIMAL(5,2) NOT NULL,
    must_have_score DECIMAL(5,2) NOT NULL,
    bonus_score DECIMAL(5,2) NOT NULL,
    experience_score DECIMAL(5,2) NOT NULL,
    analysis_payload JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE,
    CONSTRAINT chk_overall_score CHECK (overall_score BETWEEN 0.00 AND 100.00),
    CONSTRAINT chk_must_have_score CHECK (must_have_score BETWEEN 0.00 AND 100.00),
    CONSTRAINT chk_bonus_score CHECK (bonus_score BETWEEN 0.00 AND 100.00),
    CONSTRAINT chk_experience_score CHECK (experience_score BETWEEN 0.00 AND 100.00)
) ENGINE=InnoDB;

-- Content-addressable cache for parsed job description targets
CREATE TABLE IF NOT EXISTS jd_target_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    jd_hash CHAR(64) NOT NULL UNIQUE,
    prompt_version VARCHAR(32) NOT NULL DEFAULT 'v1.0',
    job_title_detected VARCHAR(255) NOT NULL,
    required_years DECIMAL(4,1) NOT NULL DEFAULT 0.0,
    targets_payload JSON NOT NULL,
    hit_count INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_jd_hash (jd_hash),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;
