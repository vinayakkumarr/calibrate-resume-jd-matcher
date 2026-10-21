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

if (!function_exists('evaluateDocumentOrientation')) {
    /**
     * Evaluates structural and pragmatic features across 4 orthogonal dimensions to calculate
     * whether an input text represents a candidate Resume vs an employer Job Description:
     *   Dimension 1: PII & Contact Identity Vector vs Corporate Requisition Channels
     *   Dimension 2: Chronological Career Trajectory vs Role Tenure Constraints
     *   Dimension 3: Pragmatic Voice & Imperatives (1st/3rd past-tense vs 2nd-person prescriptive)
     *   Dimension 4: Institutional Requisition Boilerplate (EOE, 401k, Visa, Salary)
     * 
     * Runs in strict O(N) linear time with bounded, non-backtracking regular expressions.
     */
    function evaluateDocumentOrientation(string $text): array {
        $text = trim($text);
        if (mb_strlen($text) < 50) {
            return ['resume_score' => 0.0, 'jd_score' => 0.0, 'reasons' => []];
        }

        $resumeScore = 0.0;
        $jdScore = 0.0;
        $reasons = [];

        // -----------------------------------------------------------------
        // Dimension 1: PII & Contact Identity Vector vs Corporate Channels
        // -----------------------------------------------------------------
        // Personal candidate email (excluding corporate recruitment inboxes)
        if (preg_match('/[a-zA-Z0-9._%+-]+@(?!careers\.|jobs\.|hr\.|talent\.|info\.|support\.|contact\.|admin\.|recruiting\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b/i', $text)) {
            $resumeScore += 2.5;
            $reasons[] = 'personal_email';
        }
        // Personal telephone / mobile number
        if (preg_match('/(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b/', $text)) {
            $resumeScore += 2.0;
            $reasons[] = 'phone_number';
        }
        // Personal portfolio or social handle
        if (preg_match('/(?:linkedin\.com\/in\/|github\.com\/[a-zA-Z0-9_-]+)/i', $text)) {
            $resumeScore += 2.5;
            $reasons[] = 'personal_profile_url';
        }
        // Corporate ATS, career URLs, or hiring department inboxes
        if (preg_match('/(?:greenhouse\.io|lever\.co|workday\.com|myworkdayjobs|careers\.|jobs\.)/i', $text)
            || preg_match('/(?:jobs|careers|hr|talent|recruiting)@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b/i', $text)) {
            $jdScore += 2.5;
            $reasons[] = 'corporate_hiring_channel';
        }

        // -----------------------------------------------------------------
        // Dimension 2: Chronological Career Trajectory vs Role Constraints
        // -----------------------------------------------------------------
        // Multi-span employment date intervals (e.g., 2021 – Present, Jan 2019 - Aug 2022)
        $dateSpanMatches = preg_match_all('/\b(?:19\d\d|20\d\d)\s*(?:–|-|to)\s*(?:19\d\d|20\d\d|present|current)\b/i', $text);
        if ($dateSpanMatches >= 2) {
            $resumeScore += 3.5;
            $reasons[] = 'multi_span_employment_chronology';
        } elseif ($dateSpanMatches === 1) {
            $resumeScore += 1.5;
            $reasons[] = 'employment_date_span';
        }

        // Candidate academic degree awarded
        if (preg_match('/\b(?:B\.?S\.?|B\.?Tech|B\.?E\.?|M\.?S\.?|M\.?Tech|MCA|BCA|Ph\.?D\.?|Bachelor of|Master of)\s+(?:in|of)\s+[A-Za-z\s]{3,30}\b/i', $text)) {
            $resumeScore += 2.0;
            $reasons[] = 'academic_degree_awarded';
        }

        // Forward-looking requisition experience constraint (e.g., 5+ years of experience required)
        if (preg_match('/\b(?:\d{1,2}\+?|\d{1,2}\s*-\s*\d{1,2})\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp|background|track record)\b/i', $text)
            && preg_match('/\b(?:required|preferred|must have|minimum|qualifications?|ideal candidate)\b/i', $text)) {
            $jdScore += 2.5;
            $reasons[] = 'requisition_experience_requirement';
        }

        // -----------------------------------------------------------------
        // Dimension 3: Pragmatic Voice & Grammatical Tense
        // -----------------------------------------------------------------
        // Second-person employer address (employer directing requirements to prospective applicant)
        $secondPersonCount = preg_match_all('/\b(?:you will|what you(?:[\'’]ll| will) do|what you(?:[\'’]ll| will) bring|you are responsible for|we are looking for|we(?:[\'’]re| are) looking for|the ideal candidate|the role requires|as a [a-z\s]+, you will)\b/i', $text);
        if ($secondPersonCount >= 2) {
            $jdScore += 3.0;
            $reasons[] = 'employer_second_person_address';
        } elseif ($secondPersonCount === 1) {
            $jdScore += 1.5;
            $reasons[] = 'employer_address_marker';
        }

        // Requisition section headers
        if (preg_match('/\b(?:requirements?|qualifications?|responsibilities?|what we(?:[\'’]re| are) looking for|what you(?:[\'’]ll| will) do|who you are|minimum qualifications?|preferred qualifications?|key responsibilities?|nice to have)\s*[:\n]/i', $text)) {
            $jdScore += 2.5;
            $reasons[] = 'requisition_section_headers';
        }

        // Past-tense personal action verbs describing candidate achievements
        $pastTenseMatches = preg_match_all('/\b(?:spearheaded|architected|engineered|orchestrated|co-founded|reduced latency|increased throughput|improved performance by|built and deployed)\b/i', $text);
        if ($pastTenseMatches >= 2) {
            $resumeScore += 2.5;
            $reasons[] = 'past_tense_accomplishment_verbs';
        } elseif ($pastTenseMatches === 1) {
            $resumeScore += 1.0;
            $reasons[] = 'accomplishment_verb';
        }

        // Personal resume section headers
        if (preg_match('/\b(?:work experience|professional experience|employment history|projects?|education|technical skills?|certifications?|awards?)\s*[:\n]/i', $text)) {
            $resumeScore += 2.0;
            $reasons[] = 'resume_section_headers';
        }

        // -----------------------------------------------------------------
        // Dimension 4: Institutional Requisition Boilerplate (Exclusive to JDs)
        // -----------------------------------------------------------------
        if (preg_match('/\b(?:equal opportunity employer|affirmative action|\beoe\b|visa sponsorship|401\s*\(k\)|health insurance|dental and vision|paid time off|\bpto\b|salary range|compensation:?\s*\$|job type:\s*(?:full-time|part-time|contract))\b/i', $text)) {
            $jdScore += 3.5;
            $reasons[] = 'institutional_requisition_boilerplate';
        }

        return [
            'resume_score' => round($resumeScore, 2),
            'jd_score'     => round($jdScore, 2),
            'reasons'      => $reasons
        ];
    }
}

if (!function_exists('detectInputInversion')) {
    /**
     * Determines whether the submitted Resume and Job Description inputs are inverted.
     * Requires both panels to independently exhibit reversed structural characteristics
     * and requires the composite differential margin delta to meet or exceed 4.5.
     */
    function detectInputInversion(?string $resumeText, ?string $jdText): array {
        if ($resumeText === null || $jdText === null || mb_strlen($resumeText) < 50 || mb_strlen($jdText) < 50) {
            return [
                'is_inverted'    => false,
                'combined_delta' => 0.0,
                'resume_box'     => null,
                'jd_box'         => null
            ];
        }

        $resEval = evaluateDocumentOrientation($resumeText);
        $jdEval  = evaluateDocumentOrientation($jdText);

        $resumeBoxNetJd = $resEval['jd_score'] - $resEval['resume_score'];
        $jdBoxNetResume = $jdEval['resume_score'] - $jdEval['jd_score'];

        // Both panels must independently exhibit reversed structural characteristics
        $bothCrossRole = ($resumeBoxNetJd >= 1.5) && ($jdBoxNetResume >= 1.5);
        $combinedDelta = $resumeBoxNetJd + $jdBoxNetResume;

        $isInverted = $bothCrossRole && ($combinedDelta >= 4.5);

        return [
            'is_inverted'    => $isInverted,
            'combined_delta' => round($combinedDelta, 2),
            'resume_box'     => $resEval,
            'jd_box'         => $jdEval
        ];
    }
}
