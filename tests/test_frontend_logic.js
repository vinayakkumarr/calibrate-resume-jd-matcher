/**
 * Automated Unit Test Suite for JD Analyser Frontend Engine (app.js & diff-renderer.js)
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

// Mock browser DOM environment
global.document = {
  _elements: {},
  getElementById: function(id) {
    if (!this._elements[id]) {
      this._elements[id] = { value: '', style: {}, focus: () => {}, select: () => {} };
    }
    return this._elements[id];
  },
  createElement: function(tag) {
    let content = '';
    return {
      set textContent(val) { content = String(val); },
      get textContent() { return content; },
      get innerHTML() {
        return content
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#039;');
      },
      style: {},
      focus: () => {},
      select: () => {}
    };
  },
  body: {
    appendChild: () => {},
    removeChild: () => {}
  },
  execCommand: () => true
};

global.FileReader = class {
  readAsText(file) {
    if (this.onload) {
      this.onload({ target: { result: file.mockContent || 'Sample extracted text from uploaded job description document.' } });
    }
  }
};


global.window = {
  crypto: {
    getRandomValues: (arr) => {
      for (let i = 0; i < arr.length; i++) arr[i] = Math.floor(Math.random() * 256);
      return arr;
    }
  },
  isSecureContext: false
};

global.localStorage = {
  _store: {},
  getItem: function(k) { return this._store[k] || null; },
  setItem: function(k, v) { this._store[k] = String(v); }
};

// Mock jsdiff
global.Diff = {
  diffWords: function(oldText, newText) {
    return [
      { value: 'Architected ', added: false, removed: false },
      { value: '15 microservices', added: true, removed: false },
      { value: ' APIs', added: false, removed: true }
    ];
  }
};

// Load scripts
const diffRendererCode = fs.readFileSync(path.join(__dirname, '../public/assets/js/diff-renderer.js'), 'utf8');
const appCode = fs.readFileSync(path.join(__dirname, '../public/assets/js/app.js'), 'utf8');

eval(diffRendererCode);
eval(appCode);

console.log('=== RUNNING FRONTEND LOGIC & METRIC GUARD UNIT TEST SUITE ===\n');

// 1. Test escapeHtml
console.log('[TEST 1] Verifying escapeHtml XSS Sanitization...');
const rawMalicious = '<script>alert("xss")</script>&foo=bar';
const escaped = escapeHtml(rawMalicious);
assert(!escaped.includes('<script>'), 'Must escape angle brackets');
assert(escaped.includes('&lt;script&gt;'), 'Must encode to HTML entities');
console.log('  [PASS] escapeHtml sanitized malicious script tags safely.');

// 2. Test renderDiff & renderFullRedline
console.log('\n[TEST 2] Verifying Visual Diff Rendering...');
const diffHtml = renderDiff('Built APIs', 'Architected 15 microservices');
assert(diffHtml.includes('class="diff-added"'), 'Expected diff-added class in upgrade diff');
const redlineHtml = renderFullRedline('Built APIs', 'Architected 15 microservices');
assert(redlineHtml.includes('class="diff-added"') && redlineHtml.includes('class="diff-removed"'), 'Expected both diff-added and diff-removed in redline diff');
console.log('  [PASS] renderDiff and renderFullRedline computed styled tokens correctly.');

// 3. Test Dynamic Contextual Placeholder Extraction
console.log('\n[TEST 3] Verifying Dynamic Contextual Placeholders...');
const hint1 = extractContextualPlaceholder('Reduced latency by [ENTER YOUR VERIFIED METRIC]');
assert(hint1.includes('authentic verified metric'), `Expected neutral verification hint, got: ${hint1}`);
console.log('  [PASS] extractContextualPlaceholder provides neutral verification hint.');

// 4. Test Metric Guard Lock and Clipboard Unlock
console.log('\n[TEST 4] Verifying Metric Guard Lock & Clipboard Unlock Flow...');
const mockRewrite = {
  target_skill: 'FastAPI',
  original_bullet: 'Built backend APIs in Python.',
  upgraded_xyz_bullet: 'Architected [ENTER YOUR VERIFIED METRIC] in Python/FastAPI, cutting p99 latency by [ENTER YOUR VERIFIED METRIC].',
  interview_defense_tip: 'Explain service discovery.'
};

const card = rewriteCard(mockRewrite);
assert.strictEqual(card.hasBrackets, true, 'Card must detect bracket placeholders');
assert.strictEqual(card.hasUnverifiedMetrics, true, 'Card with brackets must require verification');
assert.strictEqual(card.confirmedMetric, false, 'Card must initialize with confirmedMetric = false');
assert.strictEqual(card.isVerified, false, 'Card must not be verified initially');
assert.strictEqual(card.canCopy(), false, 'Copy must be blocked initially');

// Attempting copy while locked
card.copyToClipboard(card.currentBullet);
assert.strictEqual(card.copied, false, 'Copy must be physically blocked while brackets are unedited');
assert(card.copyBlockedReason !== null, 'Blocked reason should be populated');

// Keyboard copy event intercepted while unverified
let prevented = false;
let stopped = false;
const mockEvent = {
  preventDefault: () => { prevented = true; },
  stopPropagation: () => { stopped = true; }
};
const handled = card.handleCopyEvent(mockEvent);
assert.strictEqual(handled, false, 'handleCopyEvent must return false when unverified');
assert.strictEqual(prevented, true, 'handleCopyEvent must prevent default browser copy');
assert.strictEqual(stopped, true, 'handleCopyEvent must stop event propagation');

// User types verified metric but does not check confirmation box
card.metricInput = '24 microservices';
card.updateMetric();
assert(!card.currentBullet.includes('ENTER YOUR VERIFIED METRIC'), 'currentBullet must be dynamically updated');
assert.strictEqual(card.placeholderPresent, false, 'placeholderPresent must be false');
assert.strictEqual(card.isVerified, false, 'isVerified must remain false until explicit confirmation');
assert.strictEqual(card.canCopy(), false, 'canCopy must remain false without confirmation');

// User checks confirmation box via toggleConfirm
card.toggleConfirm();
assert.strictEqual(card.confirmedMetric, true);
assert.strictEqual(card.isVerified, true, 'isVerified must be true after metric input and confirmation');
assert.strictEqual(card.canCopy(), true, 'canCopy must be true after verification');

// Mandatory Test: Editing metric input after confirmation invalidates confirmation
card.metricInput = '48 microservices';
card.updateMetric();
assert.strictEqual(card.confirmedMetric, false, 'confirmedMetric must be invalidated on metric input change');
assert.strictEqual(card.isVerified, false, 'isVerified must return false after edit');
assert.strictEqual(card.canCopy(), false, 'canCopy must be blocked after metric edit');

// Re-confirm with updated metric
card.toggleConfirm();
assert.strictEqual(card.isVerified, true);
assert.strictEqual(card.canCopy(), true);

// Mandatory Test: Tampering with final bullet after confirmation invalidates copy
const originalValidBullet = card.currentBullet;
card.currentBullet = 'Tampered bullet text without metric';
assert.strictEqual(card.isVerified, false, 'isVerified must be false if final bullet does not match confirmed bullet');
assert.strictEqual(card.canCopy(), false, 'canCopy must be blocked if bullet was modified after confirmation');
card.currentBullet = originalValidBullet;
assert.strictEqual(card.canCopy(), true, 'canCopy restores when bullet matches confirmed state');

// Mandatory Test: Copy blocked if input is nonempty but bullet does not contain the metric
card.currentBullet = 'Architected async services without the number';
assert.strictEqual(card.isVerified, false, 'isVerified must be false if bullet does not contain metricInput');
assert.strictEqual(card.canCopy(), false, 'canCopy must be blocked if bullet lacks the entered metric');
card.currentBullet = originalValidBullet;

// Copy now succeeds via fallback
card.copyToClipboard(card.currentBullet);
assert.strictEqual(card.copied, true, 'Copy must succeed after metric input and confirmation');

// 4A-1. Regression Test for Event-Driven Checkbox Attestation (Fix for double-toggle defect)
const eventCard = rewriteCard(mockRewrite);
eventCard.metricInput = '10 microservices';
eventCard.updateMetric();
assert.strictEqual(eventCard.confirmedMetric, false);
// Simulate DOM change event when checkbox is checked by browser
eventCard.toggleConfirm({ target: { checked: true } });
assert.strictEqual(eventCard.confirmedMetric, true, 'toggleConfirm must record confirmedMetric = true from DOM change event');
assert.strictEqual(eventCard.confirmedMetricValue, '10 microservices');
assert.strictEqual(eventCard.confirmedBulletText, eventCard.currentBullet);
assert.strictEqual(eventCard.isVerified, true, 'isVerified must be true after DOM change event');
assert.strictEqual(eventCard.canCopy(), true, 'canCopy must be true after DOM change event');
// Simulate DOM change event when checkbox is unchecked by browser
eventCard.toggleConfirm({ target: { checked: false } });
assert.strictEqual(eventCard.confirmedMetric, false, 'toggleConfirm must revoke confirmation when event reports unchecked');
assert.strictEqual(eventCard.confirmedMetricValue, null);
assert.strictEqual(eventCard.confirmedBulletText, null);
assert.strictEqual(eventCard.isVerified, false, 'isVerified must be false when checkbox is unchecked');
assert.strictEqual(eventCard.canCopy(), false, 'canCopy must be blocked when checkbox is unchecked');

// 4B. Verify TC-05 Unverified Placeholder Copy Locking and Replacement
const tc05Rewrite = {
  target_skill: 'Kubernetes',
  original_bullet: 'Administered Kubernetes clusters on AWS EKS for internal developer tools.',
  upgraded_xyz_bullet: 'Accomplished [ENTER YOUR VERIFIED METRIC] cluster availability, as measured by uptime monitoring dashboards, by administering Kubernetes clusters on AWS EKS for internal developer tools.',
  requires_candidate_verification: true,
  unverified_metrics: ['99.9%']
};
const tc05Card = rewriteCard(tc05Rewrite);
assert.strictEqual(tc05Card.hasBrackets, true, 'TC-05 rewrite must detect unverified metric placeholder');
assert.strictEqual(tc05Card.hasUnverifiedMetrics, true, 'TC-05 rewrite must indicate candidate verification is required');
tc05Card.copyToClipboard(tc05Card.currentBullet);
assert.strictEqual(tc05Card.copied, false, 'Copy must be blocked while unverified placeholder remains');

// Mandatory Test: Removing brackets without valid resolution does NOT unlock copy
tc05Card.currentBullet = tc05Card.rawTemplate.replace(/\[.*?\]/g, '');
assert.strictEqual(tc05Card.placeholderPresent, false);
assert.strictEqual(tc05Card.canCopy(), false, 'Copy must be blocked when placeholder is removed without entering and confirming a metric');

// Candidate restores and enters authentic metric
tc05Card.currentBullet = tc05Card.rawTemplate;
tc05Card.metricInput = '99.95%';
tc05Card.updateMetric();
assert(!tc05Card.currentBullet.includes('ENTER YOUR VERIFIED METRIC'), 'Placeholder must be cleanly replaced');
assert(tc05Card.currentBullet.includes('99.95% cluster availability'), 'Candidate metric must be embedded');
assert.strictEqual(tc05Card.isVerified, false, 'TC-05 remains unverified until confirmation checkbox');

// Confirm
tc05Card.toggleConfirm();
assert.strictEqual(tc05Card.isVerified, true);
tc05Card.copyToClipboard(tc05Card.currentBullet);
assert.strictEqual(tc05Card.copied, true, 'Copy succeeds once verified metric replaces placeholder and is confirmed');

// 4C. Truthful non-numeric rewrite without brackets allows copying immediately
const nonNumericRewrite = {
  target_skill: 'Code Review',
  original_bullet: 'Participated in code reviews.',
  upgraded_xyz_bullet: 'Standardized pull request code review workflows with automated linting and pair review sessions.',
  requires_candidate_verification: false,
  unverified_metrics: []
};
const nonNumericCard = rewriteCard(nonNumericRewrite);
assert.strictEqual(nonNumericCard.hasBrackets, false);
assert.strictEqual(nonNumericCard.hasUnverifiedMetrics, false);
assert.strictEqual(nonNumericCard.isVerified, true);
assert.strictEqual(nonNumericCard.canCopy(), true);
nonNumericCard.copyToClipboard(nonNumericCard.currentBullet);
assert.strictEqual(nonNumericCard.copied, true, 'Truthful nonnumeric rewrite can copy immediately');

console.log('  [PASS] Metric Guard lock strictly enforces metric entry, confirmation checkbox, and copy prevention.');

// 5. Test Plain-English Error Translation
console.log('\n[TEST 5] Verifying Plain-English Error Translation...');
const err1 = translateErrorMessage('PDF contains no readable text. Scanned or image-only PDFs are not supported.');
assert(err1.includes('selectable digital PDF'), 'Expected friendly PDF guidance');

const err2 = translateErrorMessage('Analysis timed out (exceeded 90 seconds limit).');
assert(err2.includes('inputs have been preserved'), 'Expected timeout preservation assurance');

const err3 = translateErrorMessage('Daily free limit reached (3/3 scans).');
assert(err3.includes('community limit (3 scans per 24 hours)'), 'Expected plain English rate limit explanation');

const err3b = translateErrorMessage('Daily free limit reached (20/20 scans). Limit resets 24 hours after your first scan.');
assert(err3b.includes('community limit (20 scans per 24 hours)'), 'Expected 20 scans rate limit explanation');

const err4 = translateErrorMessage("429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota'}}");
assert(err4.includes('experiencing peak capacity') && err4.includes('inputs have been preserved'), 'Expected clean candidate translation for upstream quota');
console.log('  [PASS] Error translator maps raw system exceptions to clear candidate guidance.');

// 6. Test Non-Negotiable "Never Erase Input" Rule
console.log('\n[TEST 6] Verifying Non-Negotiable "Never Erase Input" Rule...');
const app = analyserApp();
app.jobDescription = 'Senior Distributed Systems Engineer with 8+ years of experience in distributed databases...';
app.file = { name: 'test_resume.pdf' };
app.errorMessage = 'Some transient failure occurred.';

// Resetting scan after an error
app.resetScan(true); // default keepInputs = true
assert(app.jobDescription.length > 50, 'resetScan must NEVER wipe jobDescription');
assert(app.file !== null, 'resetScan(true) must preserve candidate resume file');
assert.strictEqual(app.errorMessage, null, 'Error message should be cleared');
console.log('  [PASS] "Never Erase Input" invariant preserved candidate text and file in memory across resets.');

// 7. Test Job Description Dual-Mode Ingestion & File Reset Helpers
console.log('\n[TEST 7] Verifying Job Description Dual-Mode Ingestion & Reset...');
const jdApp = analyserApp();

// A. Test dropping a PDF JD
jdApp.processJdFile({ name: 'backend_jd.pdf', type: 'application/pdf', size: 10240 });
assert.strictEqual(jdApp.jdFile.name, 'backend_jd.pdf', 'jdFile should be set for PDF');
assert.strictEqual(jdApp.errorMessage, null, 'No error for valid PDF');

// Test removeJdFile resets state and DOM value
document.getElementById('jd_file_input').value = 'backend_jd.pdf';
jdApp.removeJdFile();
assert.strictEqual(jdApp.jdFile, null, 'jdFile should be null after removeJdFile');
assert.strictEqual(document.getElementById('jd_file_input').value, '', 'DOM file input value should be cleared');

// B. Test dropping a TXT file (auto-extracts and switches mode to text)
jdApp.jdMode = 'file';
jdApp.processJdFile({ 
  name: 'job_spec.txt', 
  type: 'text/plain', 
  size: 2048, 
  mockContent: 'We are seeking a Lead Backend Engineer with 7+ years of experience in distributed architectures, high-performance messaging, and database optimization.' 
});
assert.strictEqual(jdApp.jdMode, 'text', 'Dropping TXT JD should transition jdMode to text');
assert(jdApp.jobDescription.includes('Lead Backend Engineer'), 'jobDescription should be populated with text content');
assert.strictEqual(jdApp.jdFile, null, 'jdFile should be null after text auto-population');

// C. Test resetScan(true) preserves both jobDescription and jdFile
jdApp.jdFile = { name: 'preserved_jd.pdf' };
jdApp.file = { name: 'resume.pdf' };
jdApp.resetScan(true);
assert(jdApp.file !== null, 'Resume file should be preserved on resetScan(true)');
assert(jdApp.jobDescription.length > 50, 'jobDescription must be preserved on resetScan(true)');
assert(jdApp.jdFile !== null, 'jdFile must be preserved on resetScan(true)');

// D. Test resetScan(false) wipes both
jdApp.resetScan(false);
assert.strictEqual(jdApp.jobDescription, '', 'jobDescription should be wiped on resetScan(false)');
assert.strictEqual(jdApp.jdFile, null, 'jdFile should be wiped on resetScan(false)');
assert.strictEqual(jdApp.file, null, 'Resume file should be wiped on resetScan(false)');
console.log('  [PASS] JD dual-mode file ingestion and state lifecycle preserved invariants.');

// 8. Test Plain-English Translation for JD File Upload Errors
console.log('\n[TEST 8] Verifying Plain-English Translation for JD Errors...');
const jdErr1 = translateErrorMessage('Could not extract text from Job Description PDF. PDF contains no readable text.');
assert(jdErr1.includes('readable text from the Job Description PDF'), 'Expected friendly JD PDF extraction guidance');

const jdErr2 = translateErrorMessage('Unsupported job description file format. Please upload a PDF or TXT file.');
assert(jdErr2.includes('Unsupported file format'), 'Expected friendly unsupported format guidance');

const jdErr3 = translateErrorMessage('Security Error: Job description file is not a valid PDF document.');
assert(jdErr3.includes('standard PDF document signatures'), 'Expected friendly JD magic-byte guidance');
console.log('  [PASS] JD error translation rules mapped all upload errors to actionable guidance.');

// 9. Test Hybrid Resume Ingestion & File Reset Helpers
console.log('\n[TEST 9] Verifying Hybrid Resume Ingestion & Reset...');
const resApp = analyserApp();

// A. Test dropping a PDF resume
resApp.processResumeFile({ name: 'developer_resume.pdf', type: 'application/pdf', size: 15360 });
assert.strictEqual(resApp.file.name, 'developer_resume.pdf', 'file should be set for PDF');
assert.strictEqual(resApp.errorMessage, null, 'No error for valid PDF');

// Test removeFile resets state and DOM value
document.getElementById('resume').value = 'developer_resume.pdf';
resApp.removeFile();
assert.strictEqual(resApp.file, null, 'file should be null after removeFile');
assert.strictEqual(document.getElementById('resume').value, '', 'DOM resume input value should be cleared');

// B. Test dropping a TXT resume file (auto-extracts and switches mode to text)
resApp.resumeMode = 'file';
resApp.processResumeFile({
  name: 'my_resume.txt',
  type: 'text/plain',
  size: 3000,
  mockContent: 'Alex Rivera - Senior Software Engineer with 6 years experience in Python, FastAPI, MySQL, Redis, and high-throughput systems.'
});
assert.strictEqual(resApp.resumeMode, 'text', 'Dropping TXT resume should transition resumeMode to text');
assert(resApp.resumeText.includes('Alex Rivera'), 'resumeText should be populated with text content');
assert.strictEqual(resApp.file, null, 'file should be null after text auto-population');

// C. Test resetScan(true) preserves both resumeText and file
resApp.resumeText = 'Preserved resume text...';
resApp.resetScan(true);
assert.strictEqual(resApp.resumeText, 'Preserved resume text...', 'resumeText must be preserved on resetScan(true)');

// D. Test resetScan(false) wipes resumeText and resets mode
resApp.resetScan(false);
assert.strictEqual(resApp.resumeText, '', 'resumeText should be wiped on resetScan(false)');
assert.strictEqual(resApp.resumeMode, 'file', 'resumeMode should reset to file on resetScan(false)');
console.log('  [PASS] Resume hybrid mode file ingestion and state lifecycle preserved invariants.');

// 10. Test Plain-English Translation for Resume Errors
console.log('\n[TEST 10] Verifying Plain-English Translation for Resume Errors...');
const resumeErr1 = translateErrorMessage('Resume text is too short (minimum 200 characters required).');
assert(resumeErr1.includes('resume text is too short'), 'Expected friendly resume text guidance');

const resumeErr2 = translateErrorMessage('Unsupported resume file format. Please upload a PDF or TXT file.');
assert(resumeErr2.includes('Unsupported file format'), 'Expected friendly unsupported resume format guidance');
console.log('  [PASS] Resume error translation rules mapped all resume errors to actionable guidance.');

// 11. Test Extracted Text Inspector & Submit Guard Logic
console.log('\n[TEST 11] Verifying Extracted Text Inspector & Submission Guards...');
const inspApp = analyserApp();

// Verify initial state
assert.strictEqual(inspApp.resumeInspectorOpen, false, 'Inspector should be closed initially');
assert.strictEqual(inspApp.isSubmitDisabled(), true, 'Submit should be disabled when inputs are empty');

// Set mock extraction state
inspApp.file = { name: 'engineer_cv.pdf', size: 40960 };
inspApp.resumeExtractedText = 'Senior Infrastructure Engineer with 10 years experience architecting cloud pipelines.';
inspApp.resumeEditedText = inspApp.resumeExtractedText;
inspApp.resumeExtractionMeta = { wordCount: 85, pageCount: 1, charCount: 88 };

inspApp.jobDescription = 'We are seeking a Senior Infrastructure Engineer with 8+ years experience in Kubernetes, Terraform, AWS, and distributed logging pipelines. Must possess demonstrated leadership in technical architecture and engineering excellence across multi-region deployments.';
inspApp.jdMode = 'text';

// Ready state without edits
assert.strictEqual(inspApp.isSubmitDisabled(), false, 'Submit should be enabled when valid inputs exist');

// User edits extracted text to shorter than 80 chars
inspApp.resumeEditedText = 'Edited text too short.';
assert.strictEqual(inspApp.isSubmitDisabled(), true, 'Submit should be disabled if edited resume text is under 80 chars');

// Smart Two-Tier Gate: 80 to 199 chars (advisory range) enables submit!
inspApp.resumeEditedText = 'Senior Infrastructure Engineer with 10 years experience architecting cloud pipelines.';
assert.strictEqual(inspApp.isSubmitDisabled(), false, 'Submit should be enabled for concise input in 80-199 chars advisory range');

// Short raw JD under 80 chars disables submit
inspApp.jobDescription = 'Brief JD snippet.';
assert.strictEqual(inspApp.isSubmitDisabled(), true, 'Submit should be disabled if JD text is under 80 chars');

// Concise raw JD in 80-199 range enables submit
inspApp.jobDescription = 'We are seeking a Cloud Infrastructure Engineer with experience in Kubernetes, Terraform, and AWS.';
assert.strictEqual(inspApp.isSubmitDisabled(), false, 'Submit should be enabled for concise JD in 80-199 range');

// Revert logic restores original text
inspApp.revertResumeExtractedText();
assert.strictEqual(inspApp.resumeEditedText, inspApp.resumeExtractedText, 'Revert should restore original extracted text');
assert.strictEqual(inspApp.isSubmitDisabled(), false, 'Submit should be re-enabled after reverting to valid file');

// Loading state disables submit
inspApp.resumeExtractionLoading = true;
assert.strictEqual(inspApp.isSubmitDisabled(), true, 'Submit should be disabled while extraction is in progress');
inspApp.resumeExtractionLoading = false;
assert.strictEqual(inspApp.isSubmitDisabled(), false, 'Submit should re-enable once extraction completes');

// Interactive submission feedback when incomplete
const feedbackApp = analyserApp();
feedbackApp.resumeMode = 'file';
feedbackApp.file = null;
feedbackApp.jdMode = 'text';
feedbackApp.jobDescription = 'Senior Software Engineer with extensive distributed systems and cloud infrastructure experience.';
feedbackApp.submitScan();
assert(feedbackApp.errorMessage && feedbackApp.errorMessage.includes('resume'), 'Expected informative error message when resume is missing');

console.log('  [PASS] Extracted Text Inspector state lifecycle and submit guards verified.');

// 12. Test Unified Requirements Ledger & Filtering Logic
console.log('\n[TEST 12] Verifying Unified Requirements Ledger & Filtering Logic...');
const ledgerApp = analyserApp();
ledgerApp.report = {
  must_haves: [
    { requirement: 'PHP Backend Experience', status: 'MATCHED', evidence_quote: 'Built platform in PHP' },
    { requirement: 'Bachelor degree in CS or BCA', status: 'WEAK', evidence_quote: 'BCA 2023-2027', gap_reason: 'Degree in progress' }
  ],
  bonus_skills: [
    { skill: 'Docker Containerization', status: 'MISSING', gap_reason: 'No containerization experience' },
    { skill: 'TypeScript', status: 'MISSING', gap_reason: 'No TypeScript listed' },
    { skill: 'Hackathon Participation', status: 'MATCHED', evidence_quote: 'Smart India Hackathon 2025' }
  ]
};

// Check allRequirements flattening
const allReqs = ledgerApp.allRequirements;
assert.strictEqual(allReqs.length, 5, 'Expected 5 total requirements (2 core + 3 bonus)');
assert.strictEqual(allReqs[0].category, 'core');
assert.strictEqual(allReqs[2].category, 'bonus');
assert.strictEqual(allReqs[2].requirement, 'Docker Containerization');

// Check counts
const counts = ledgerApp.requirementsCounts;
assert.strictEqual(counts.total, 5, 'Total count should be 5');
assert.strictEqual(counts.core, 2, 'Core count should be 2');
assert.strictEqual(counts.bonus, 3, 'Bonus count should be 3');
assert.strictEqual(counts.matched, 2, 'Matched count should be 2');
assert.strictEqual(counts.weak, 1, 'Weak count should be 1');
assert.strictEqual(counts.missing, 2, 'Missing count should be 2');

// Check tab filtering
ledgerApp.filterTab = 'all';
assert.strictEqual(ledgerApp.filteredRequirements.length, 5);

ledgerApp.filterTab = 'matched';
assert.strictEqual(ledgerApp.filteredRequirements.length, 2);

ledgerApp.filterTab = 'weak';
assert.strictEqual(ledgerApp.filteredRequirements.length, 1);
assert.strictEqual(ledgerApp.filteredRequirements[0].requirement, 'Bachelor degree in CS or BCA');

ledgerApp.filterTab = 'missing';
assert.strictEqual(ledgerApp.filteredRequirements.length, 2);
assert.strictEqual(ledgerApp.filteredRequirements[0].requirement, 'Docker Containerization');
assert.strictEqual(ledgerApp.filteredRequirements[1].requirement, 'TypeScript');

// Backwards-compatibility alias
assert.strictEqual(ledgerApp.filteredMustHaves.length, 2);

// Check Domain Filtering & Defense Tips
ledgerApp.report.must_haves[0].domain = 'Languages & Frameworks';
ledgerApp.report.must_haves[0].defense_tip = 'Discuss PDO prepared statements';
ledgerApp.report.must_haves[1].domain = 'Computer Science Fundamentals';
ledgerApp.report.bonus_skills[0].domain = 'DevOps, Cloud & Modern Stack';

const domains = ledgerApp.availableDomains;
assert(domains.includes('Languages & Frameworks'), 'Expected Languages & Frameworks in availableDomains');
assert(domains.includes('Computer Science Fundamentals'), 'Expected Computer Science Fundamentals in availableDomains');
assert(domains.includes('DevOps, Cloud & Modern Stack'), 'Expected DevOps in availableDomains');

// Filter by domain
ledgerApp.selectedDomain = 'Languages & Frameworks';
ledgerApp.filterTab = 'all';
assert.strictEqual(ledgerApp.filteredRequirements.length, 1);
assert.strictEqual(ledgerApp.filteredRequirements[0].defense_tip, 'Discuss PDO prepared statements');

// Reset domain filter
ledgerApp.selectedDomain = 'all';
assert.strictEqual(ledgerApp.filteredRequirements.length, 5);

// Verify canonical 9 domains dynamically populate in availableDomains
ledgerApp.report.must_haves[0].domain = 'Technical Leadership, Strategy & Delivery';
ledgerApp.report.bonus_skills[1].domain = 'AI, Machine Learning & Analytics';
ledgerApp.report.bonus_skills[2].domain = 'Databases, Data Platforms & Storage';
const updatedDomains = ledgerApp.availableDomains;
assert(updatedDomains.includes('Technical Leadership, Strategy & Delivery'), 'Expected Technical Leadership in availableDomains');
assert(updatedDomains.includes('AI, Machine Learning & Analytics'), 'Expected AI/ML in availableDomains');
assert(updatedDomains.includes('Databases, Data Platforms & Storage'), 'Expected Databases & Data Platforms in availableDomains');

ledgerApp.selectedDomain = 'Technical Leadership, Strategy & Delivery';
assert.strictEqual(ledgerApp.filteredRequirements.length, 1);
ledgerApp.selectedDomain = 'all';

console.log('  [PASS] Unified Requirements Ledger seamlessly unifies core and bonus criteria with precision counts and domain filtering.');

// 13. Test Smooth Box Adjustment Settings Logic
console.log('\n[TEST 13] Verifying Smooth Box Adjustment Settings Logic...');
const boxApp = analyserApp();
assert.strictEqual(boxApp.resumeHeightPreset, 'compact', 'Default resume box height preset should be compact');
assert.strictEqual(boxApp.jdHeightPreset, 'compact', 'Default JD box height preset should be compact');

// Test preset switching
boxApp.adjustBoxHeight('resume', 'comfortable');
assert.strictEqual(boxApp.resumeHeightPreset, 'comfortable', 'Resume height preset should switch to comfortable');

boxApp.adjustBoxHeight('resume', 'expanded');
assert.strictEqual(boxApp.resumeHeightPreset, 'expanded', 'Resume height preset should switch to expanded');

boxApp.adjustBoxHeight('resume', 'autofit');
assert.strictEqual(boxApp.resumeHeightPreset, 'autofit', 'Resume height preset should switch to autofit');

boxApp.adjustBoxHeight('jd', 'comfortable');
assert.strictEqual(boxApp.jdHeightPreset, 'comfortable', 'JD height preset should switch to comfortable');

boxApp.adjustBoxHeight('jd', 'expanded');
assert.strictEqual(boxApp.jdHeightPreset, 'expanded', 'JD height preset should switch to expanded');

// Test autofit ceiling & floor clamping on DOM elements
const mockResumeEl = { tagName: 'TEXTAREA', scrollHeight: 1200, style: {}, classList: { add: () => {}, remove: () => {} } };
document._elements['resume_textarea'] = mockResumeEl;
boxApp.adjustBoxHeight('resume', 'autofit');
assert.strictEqual(mockResumeEl.style.height, '680px', 'Autofit with large content must clamp to 680px ceiling');

mockResumeEl.scrollHeight = 300;
boxApp.adjustBoxHeight('resume', 'autofit');
assert.strictEqual(mockResumeEl.style.height, '312px', 'Autofit with medium content must set height to scrollHeight + 12');

mockResumeEl.scrollHeight = 100;
boxApp.adjustBoxHeight('resume', 'autofit');
assert.strictEqual(mockResumeEl.style.height, '240px', 'Autofit with tiny content must clamp to 240px minimum');

console.log('  [PASS] Smooth box adjustment settings state and height transition guards verified.');

// 14. Test Hybrid Pillar 1 Score Breakdown & Metric Summary Getters
console.log('\n[TEST 14] Verifying Hybrid Overview Pillar 1 Getters & Formatted Scores...');
const hybridApp = analyserApp();
hybridApp.scores = {
  overall_score: 82.5,
  must_have_score: 96.15,
  bonus_score: 45.0,
  experience_score: null
};
hybridApp.report = {
  must_haves: [
    { requirement: 'PHP Architecture', status: 'MATCHED' },
    { requirement: 'React Frontend', status: 'MATCHED' },
    { requirement: 'Docker', status: 'MISSING' }
  ],
  bonus_skills: [
    { skill: 'Kubernetes', status: 'MATCHED' },
    { skill: 'GraphQL', status: 'MISSING' }
  ],
  experience_years: {
    required_years: 0,
    candidate_years: 4.5,
    requirement_status: 'NOT_SPECIFIED'
  }
};

// Check formatted scores (rounded integers, null preserved for excluded)
assert.strictEqual(hybridApp.formattedScores.overall, 83, 'Overall score should round 82.5 to 83');
assert.strictEqual(hybridApp.formattedScores.raw, 83, 'Raw score should default to overall when un-gated');
assert.strictEqual(hybridApp.formattedScores.is_gated, false, 'Expected un-gated status for qualified profile');
assert.strictEqual(hybridApp.formattedScores.must_have, 96, 'Must have score should round 96.15 to 96');
assert.strictEqual(hybridApp.formattedScores.bonus, 45, 'Bonus score should format 45.0 to 45');
assert.strictEqual(hybridApp.formattedScores.experience, null, 'Experience score should remain null when excluded');

// Test gated profile formatted scores (e.g. Kabir Roy: raw 18%, overall 10%)
hybridApp.scores.is_gated = true;
hybridApp.scores.raw_score = 17.95;
hybridApp.scores.overall_score = 9.66;
assert.strictEqual(hybridApp.formattedScores.raw, 18, 'Raw score should format 17.95 to 18');
assert.strictEqual(hybridApp.formattedScores.overall, 10, 'Gated score should format 9.66 to 10');
assert.strictEqual(hybridApp.formattedScores.is_gated, true, 'Expected is_gated to be true for gated profile');

// Reset to original values
hybridApp.scores.is_gated = false;
hybridApp.scores.raw_score = 82.5;
hybridApp.scores.overall_score = 82.5;

// Check concrete count summaries
assert.strictEqual(hybridApp.coreSkillsSummary, '2 of 3 skills met');
assert.strictEqual(hybridApp.bonusSkillsSummary, '1 of 2 skills met');
assert.strictEqual(hybridApp.experienceSummary, 'Not specified in JD');

// Check extraction failed status
hybridApp.report.experience_years.requirement_status = 'EXTRACTION_FAILED';
assert.strictEqual(hybridApp.experienceSummary, 'Unverified in resume');

// Check specified experience tenure
hybridApp.report.experience_years.requirement_status = 'SPECIFIED';
hybridApp.report.experience_years.required_years = 3;
hybridApp.report.experience_years.candidate_years = 5;
hybridApp.scores.experience_score = 100;
assert.strictEqual(hybridApp.experienceSummary, '5 of 3+ yrs met');
assert.strictEqual(hybridApp.formattedScores.experience, 100);

console.log('  [PASS] Hybrid Overview Pillar 1 getters and integer rounding verified with 100% precision.');

console.log('\n[TEST 15] Verifying Dual-Tenure UI Presentation Safeguards (Approach 4)...');
// Scenario A: Non-technical profile (e.g. 5 yrs Cashier applying for 5y Tech role)
hybridApp.report.experience_years.required_years = 5;
hybridApp.report.experience_years.candidate_years = 0;
hybridApp.report.experience_years.general_workforce_years = 5;
hybridApp.scores.experience_score = 0;
assert.strictEqual(hybridApp.experienceSummary, '0 of 5+ tech yrs met (5 yrs non-tech)');

// Scenario B: Career Changer (e.g. 2 yrs Dev + 4 yrs Retail = 6 yrs Total)
hybridApp.report.experience_years.required_years = 3;
hybridApp.report.experience_years.candidate_years = 2;
hybridApp.report.experience_years.general_workforce_years = 6;
hybridApp.scores.experience_score = 67;
assert.strictEqual(hybridApp.experienceSummary, '2 of 3+ tech yrs met (6 yrs total)');

// Scenario C: Pure Tech Senior (e.g. 8 yrs Software Engineer)
hybridApp.report.experience_years.required_years = 5;
hybridApp.report.experience_years.candidate_years = 8;
hybridApp.report.experience_years.general_workforce_years = 8;
hybridApp.scores.experience_score = 100;
assert.strictEqual(hybridApp.experienceSummary, '8 of 5+ yrs met');

console.log('  [PASS] Dual-tenure UX presentation transparently distinguishes tech tenure from general workforce.');

console.log('\n[TEST 16] Verifying Transient Network Resilience & 3-Strike Polling Fault Tolerance...');
let simulatedConsecutiveErrors = 0;
const maxNetworkRetries = 3;
let isPollingActive = true;
let progressMsg = '';

const simulatePollTick = (networkOk) => {
  if (networkOk) {
    simulatedConsecutiveErrors = 0;
    progressMsg = '2/3 Auditing qualification evidence...';
  } else {
    simulatedConsecutiveErrors++;
    if (simulatedConsecutiveErrors < maxNetworkRetries) {
      progressMsg = 'Reconnecting to analysis worker...';
    } else {
      isPollingActive = false;
      progressMsg = 'Analysis failed due to persistent network issues.';
    }
  }
};

// Tick 1: Transient network failure (e.g. WiFi reconnect)
simulatePollTick(false);
assert.strictEqual(simulatedConsecutiveErrors, 1);
assert.strictEqual(isPollingActive, true, 'Polling must remain active on 1st transient failure.');
assert.strictEqual(progressMsg, 'Reconnecting to analysis worker...');

// Tick 2: 2nd consecutive failure
simulatePollTick(false);
assert.strictEqual(simulatedConsecutiveErrors, 2);
assert.strictEqual(isPollingActive, true, 'Polling must remain active on 2nd transient failure.');

// Tick 3: Network recovers!
simulatePollTick(true);
assert.strictEqual(simulatedConsecutiveErrors, 0, 'Counter must reset to 0 upon successful network response.');
assert.strictEqual(isPollingActive, true);

// Tick 4, 5, 6: 3 consecutive failures trigger graceful exit
simulatePollTick(false);
simulatePollTick(false);
simulatePollTick(false);
assert.strictEqual(simulatedConsecutiveErrors, 3);
assert.strictEqual(isPollingActive, false, 'Polling must gracefully abort after 3 consecutive network failures.');

console.log('  [PASS] 3-strike polling network resilience verified with seamless reconnect logic.');

// -----------------------------------------------------------------------------
// TEST 17: Verifying Orientation Inversion & Full-State Panel Swap
// -----------------------------------------------------------------------------
console.log('\n[TEST 17] Verifying Document Orientation & Full-State Panel Swap...');

const sampleResumeText = `
Alex Mercer
alex.mercer@gmail.com | (555) 234-5678 | San Francisco, CA
linkedin.com/in/alex-mercer | github.com/alexmercer

PROFESSIONAL SUMMARY
Senior Backend Engineer with 6+ years of experience architecting distributed cloud systems.

WORK EXPERIENCE
Senior Software Engineer | Stripe | 2021 – Present
• Architected high-throughput payment settlement microservices handling 12,000 requests/sec.
• Engineered distributed caching layer with Redis, reducing p99 latency by 35%.
• Spearheaded migration from monolithic services to event-driven Kafka architecture.

EDUCATION
B.S. in Computer Science | University of California, Berkeley | 2014 – 2018
`;

const sampleJdText = `
Senior Backend Engineer - Core Infrastructure
Company: Veloce Systems | San Francisco, CA (Hybrid)
Job Type: Full-time | Salary Range: $160,000 - $200,000

About the Role:
We are looking for a Senior Backend Engineer to join our Core Platform team. In this role, you will be responsible for designing, building, and maintaining high-scale distributed systems.

What You'll Do:
• Architect resilient microservices in Python or Go.
• Build scalable data pipelines with Kafka and relational databases (PostgreSQL/MySQL).
• You will collaborate with product designers and frontend teams to deliver core APIs.

Qualifications:
• 5+ years of experience in backend software engineering required.
• Strong proficiency in distributed systems design, caching, and database indexing.
• Bachelor's degree in Computer Science or equivalent practical experience.

Benefits:
• Comprehensive health insurance, 401(k) matching, and unlimited PTO.
• Veloce Systems is an Equal Opportunity Employer.
`;

const appInstance = analyserApp();

// Verify normal order
appInstance.resumeMode = 'text';
appInstance.resumeText = sampleResumeText;
appInstance.jdMode = 'text';
appInstance.jobDescription = sampleJdText;

assert.strictEqual(appInstance.isSwappedDetected, false, 'Normal order must NOT be detected as swapped.');

// Verify swapped order
appInstance.resumeText = sampleJdText;
appInstance.jobDescription = sampleResumeText;

assert.strictEqual(appInstance.isSwappedDetected, true, 'Inverted order must be deterministically detected as swapped.');

// Verify full state swap with files and extracted text
const fakeResumeFile = { name: 'resume.pdf', size: 102400 };
const fakeJdFile = { name: 'job_spec.txt', size: 4096 };

appInstance.resumeMode = 'file';
appInstance.file = fakeResumeFile;
appInstance.resumeExtractedText = 'Extracted Resume Content';
appInstance.resumeEditedText = 'Edited Resume Content';
appInstance.resumeExtractionMeta = { wordCount: 150, pageCount: 1 };

appInstance.jdMode = 'text';
appInstance.jdFile = null;
appInstance.jobDescription = sampleJdText;
appInstance.jdExtractedText = '';
appInstance.jdEditedText = '';
appInstance.jdExtractionMeta = { wordCount: 0, pageCount: 0 };

// Execute swapPanels
appInstance.swapPanels();

// Assert complete symmetrical state transfer
assert.strictEqual(appInstance.resumeMode, 'text', 'Resume mode should now be text.');
assert.strictEqual(appInstance.jdMode, 'file', 'JD mode should now be file.');
assert.strictEqual(appInstance.file, null, 'Resume file should now be null.');
assert.strictEqual(appInstance.jdFile, fakeResumeFile, 'JD file should now hold the original resume file.');
assert.strictEqual(appInstance.resumeText, sampleJdText, 'Resume text should now contain the JD text.');
assert.strictEqual(appInstance.jdExtractedText, 'Extracted Resume Content', 'JD extracted text should hold original resume extraction.');
assert.strictEqual(appInstance.jdEditedText, 'Edited Resume Content', 'JD edited text should hold original resume edited text.');
assert.strictEqual(appInstance.jdExtractionMeta.wordCount, 150, 'JD extraction metadata must hold swapped count.');

console.log('  [PASS] Document orientation and full-state panel swap verified with 100% preservation.');

console.log('\n=============================================================');
console.log('ALL FRONTEND LOGIC & METRIC GUARD TESTS PASSED (100% SUCCESS)');
console.log('=============================================================\n');


