<?php
declare(strict_types=1);

/**
 * Validation & Normalization Helpers for Calibrate AI Gateway
 */

if (!function_exists('normalizeTextForComparison')) {
    /**
     * Normalizes text for identity comparison:
     * - Strips UTF-8 Byte Order Mark (BOM)
     * - Normalizes Windows/Mac line endings (CRLF, CR) to standard LF
     * - Normalizes horizontal whitespace (tabs, consecutive spaces) to a single space
     * - Trims each line and removes empty lines
     * - Lowercases text (UTF-8) for case-insensitive content equivalence
     */
    function normalizeTextForComparison(string $text): string {
        $text = preg_replace('/^\xEF\xBB\xBF/', '', $text);
        $text = str_replace(["\r\n", "\r"], "\n", $text);
        $text = preg_replace('/[^\S\n]+/', ' ', $text);
        $lines = array_map('trim', explode("\n", $text));
        $nonEmptyLines = array_values(array_filter($lines, fn(string $line): bool => $line !== ''));
        return mb_strtolower(implode("\n", $nonEmptyLines), 'UTF-8');
    }
}

if (!function_exists('areInputsIdentical')) {
    /**
     * Detects if two text inputs represent the identical content despite insignificant formatting differences.
     */
    function areInputsIdentical(string $textA, string $textB): bool {
        if ($textA === '' || $textB === '') {
            return false;
        }
        return normalizeTextForComparison($textA) === normalizeTextForComparison($textB);
    }
}
