/**
 * JD Analyser — Alpine.js Reactive State Controller & Telemetry Engine
 * Features:
 * - "Never Erase Input" preservation rule across all error and retry states.
 * - Dynamic Metric Lock (MetricGuardCard) enforcing candidate metric verification before copy.
 * - Dynamic contextual placeholder hints adapted to metric types.
 * - 2-second resilient polling with 90-second timeout guard.
 * - Plain-English error translation mapping raw backend traces to friendly guidance.
 * - Dual-mode secure clipboard handler (navigator.clipboard with execCommand fallback).
 */

function translateErrorMessage(rawError) {
  if (!rawError) {
    return 'An unexpected processing error occurred. Your inputs have been preserved.';
  }
  const lower = String(rawError).toLowerCase();

  if (lower.includes('resume text is too short') || lower.includes('resume text file is too short')) {
    return 'Your resume text is too short. Please provide at least 80 characters of work experience, technical skills, and achievements.';
  }
  if (lower.includes('unsupported resume file format')) {
    return 'Unsupported file format. Please upload a PDF, TXT, or Markdown document for your resume.';
  }
  if (lower.includes('could not extract text from job description pdf')) {
    return 'We could not extract readable text from the Job Description PDF. Please upload a selectable digital PDF or paste the text directly.';
  }
  if (lower.includes('unsupported job description file format')) {
    return 'Unsupported file format. Please upload a PDF, TXT, or Markdown document for the job description.';
  }
  if (lower.includes('security error: job description file is not a valid pdf')) {
    return 'Security verification failed: The uploaded job description does not match standard PDF document signatures.';
  }
  if (lower.includes('both a resume') && lower.includes('required')) {
    return 'Both a candidate resume (document or text) and a job description (document or text) are required.';
  }
  if (lower.includes('no readable text') || lower.includes('scanned or image')) {
    return 'We could not detect selectable text in your PDF. Please upload a selectable digital PDF exported directly from Word, Docs, or LaTeX rather than a scanned photo or Canva image.';
  }
  if (lower.includes('90 seconds') || lower.includes('timeout') || lower.includes('timed out')) {
    return 'Analysis took longer than expected due to temporary server load. Your inputs have been preserved—click Analyze to retry.';
  }
  if (lower.includes('daily free limit') || lower.includes('scans per 24 hours')) {
    const match = rawError.match(/\((\d+)\/(\d+)\s+scans\)/i);
    const limitCount = match ? match[2] : '20';
    return `You have reached your daily community limit (${limitCount} scans per 24 hours). Your quota resets 24 hours after your first scan.`;
  }
  if (lower.includes('community capacity') || lower.includes('1,400')) {
    return 'Daily system community capacity reached (1,400 scans). Please try again tomorrow.';
  }
  if (lower.includes('magic-byte') || lower.includes('not a valid pdf') || lower.includes('pdf signature')) {
    return 'Security verification failed: The selected file does not match standard PDF document signatures.';
  }
  if (lower.includes('minimum 200 characters') || lower.includes('minimum 80 characters') || lower.includes('job description is too short')) {
    return 'The target job description is too short. Please provide at least 80 characters of responsibilities and requirements.';
  }

  if (lower.includes('exceeds maximum allowed size')) {
    return 'The uploaded file exceeds the maximum allowed file size of 10MB.';
  }

  if (lower.includes('429') || lower.includes('resource_exhausted') || lower.includes('quota') || lower.includes('rate limit') || lower.includes('rate-limit')) {
    return 'The AI intelligence service is currently experiencing peak capacity or temporary rate limits. Your inputs have been preserved—please try again in a few moments.';
  }

  return rawError;
}

function analyserApp() {
  return {
    view: 'upload', // 'upload' | 'results'
    resumeMode: 'file', // 'file' | 'text'
    file: null,
    resumeText: '',
    jdMode: 'text', // 'text' | 'file'
    jdFile: null,
    jobDescription: '',
    loading: false,
    progressPercent: 15,
    progressMessage: 'Initializing document processing...',
    errorMessage: null,
    scanUuid: null,
    pollTimer: null,
    filterTab: 'all', // 'all' | 'matched' | 'weak' | 'missing'
    selectedDomain: 'all', // 'all' | specific technical domain
    showPrivacyNotice: false,

    // Verbatim Layout Extraction Inspector State
    resumeExtractedText: '',
    resumeEditedText: '',
    resumeExtractionLoading: false,
    resumeExtractionError: null,
    resumeInspectorOpen: false,
    resumeExtractionMeta: { wordCount: 0, pageCount: 0, charCount: 0 },

    jdExtractedText: '',
    jdEditedText: '',
    jdExtractionLoading: false,
    jdExtractionError: null,
    jdInspectorOpen: false,
    jdExtractionMeta: { wordCount: 0, pageCount: 0, charCount: 0 },

    // Box Height Adjustment Presets ('compact' | 'comfortable' | 'expanded' | 'autofit')
    resumeHeightPreset: 'compact',
    jdHeightPreset: 'compact',

    scores: {
      overall_score: 0,
      must_have_score: 0,
      bonus_score: 0,
      experience_score: 0
    },

    report: {
      job_title_detected: '',
      must_haves: [],
      bonus_skills: [],
      experience_years: { required_years: 0, candidate_years: 0 },
      actionable_rewrites: [],
      evidence_ledger: null
    },

    init() {
      if (typeof window !== 'undefined' && window.location.search && window.location.search.includes('preview=results')) {
        this.view = 'results';
        this.report = {
          job_title_detected: 'Junior Full Stack Developer (PHP / JS / React)',
          must_haves: [
            { requirement: 'PHP Backend Framework Architecture', domain: 'Languages & Frameworks', status: 'MATCHED', evidence_quote: 'Built full-stack platforms using PHP & MySQL with optimized query plans.', defense_tip: 'Highlight your experience with PDO prepared statements and modular MVC architecture.' },
            { requirement: 'JavaScript (ES6+) Fundamentals', domain: 'Languages & Frameworks', status: 'MATCHED', evidence_quote: 'Web Development: JavaScript, HTML5, CSS3, Bootstrap, PHP', defense_tip: 'Discuss closures, asynchronous promises, and modern ES6+ array manipulation methods.' },
            { requirement: 'HTML5 & CSS3 Responsive UI Design', domain: 'Languages & Frameworks', status: 'MATCHED', evidence_quote: 'Built responsive web interfaces with Bootstrap, HTML5, and CSS3.', defense_tip: 'Explain CSS flexbox, grid, and mobile-first responsive design breakpoints.' },
            { requirement: 'React Client-Side Component Architecture', domain: 'Languages & Frameworks', status: 'MATCHED', evidence_quote: 'Algorithm Visualizer — React, CSS3', defense_tip: 'Detail useState/useEffect hooks and how you prevented unnecessary DOM re-renders during animations.' },
            { requirement: 'Relational Database Schema Design (3NF Normalization)', domain: 'Databases, Data Platforms & Storage', status: 'MATCHED', evidence_quote: 'Architected a normalised MySQL schema managing core entities with foreign key constraints.', defense_tip: 'Explain primary vs foreign key constraints, 3NF normalization rules, and entity-relationship models.' },
            { requirement: 'Structured Query Indexing & Optimization', domain: 'Databases, Data Platforms & Storage', status: 'MATCHED', evidence_quote: 'Optimized indexed queries throughout relational expense settlement system.', defense_tip: 'Be ready to discuss EXPLAIN plans and how composite B-Tree indexes reduce disk I/O.' },
            { requirement: 'Data Structures & Algorithms (DSA)', domain: 'Computer Science Fundamentals & System Design', status: 'MATCHED', evidence_quote: 'Core Competencies: DSA; Top 20 Rank at GeeksforGeeks; HackerRank 4★ in Java', defense_tip: 'Be prepared for whiteboard coding on hash maps, two pointers, and time/space complexity tradeoffs.' },
            { requirement: 'Computer Networking (Protocols, TCP/IP, REST)', domain: 'Computer Science Fundamentals & System Design', status: 'MATCHED', evidence_quote: 'Networking Basics — Cisco Certified', defense_tip: 'Emphasize your Cisco certification when discussing TCP/IP handshakes, DNS resolution, and HTTP status codes.' },
            { requirement: 'Operating Systems & System Architecture', domain: 'Computer Science Fundamentals & System Design', status: 'MATCHED', evidence_quote: 'Core Competencies: OS, Computer Networking, Computer Architecture', defense_tip: 'Discuss process vs thread lifecycles, memory management, and file systems.' },
            { requirement: 'Git & GitHub Version Control Workflows', domain: 'Quality Engineering, Tooling & Workflows', status: 'MATCHED', evidence_quote: 'Tools: Git, GitHub, VS Code', defense_tip: 'Explain branch strategies, rebasing vs merging, and pull request code review workflows.' },
            { requirement: 'Third-Party REST API Integration', domain: 'Quality Engineering, Tooling & Workflows', status: 'MATCHED', evidence_quote: 'Integrated Gemini API into an interactive dashboard for skill analysis.', defense_tip: 'Detail how you handle API authentication, rate limits, error status handling, and async data ingestion.' }
          ],
          bonus_skills: [
            { skill: 'TypeScript for Type-Safe Development', domain: 'Languages & Frameworks', status: 'MISSING', gap_reason: 'TypeScript is not listed on resume.', defense_tip: 'Pivot from strongly-typed Java and C background to demonstrate fast ramp-up on TS interfaces and generics.' },
            { skill: 'Docker Containerization', domain: 'Cloud, Infrastructure & DevOps', status: 'MISSING', gap_reason: 'Containerization tools like Docker are not present in the resume.', defense_tip: 'Explain the purpose of Dockerfiles, multi-stage builds, and port mapping.' },
            { skill: 'CI/CD Pipelines & Automated Unit Testing', domain: 'Quality Engineering, Tooling & Workflows', status: 'MISSING', gap_reason: 'No automated CI/CD pipeline or Jest/PHPUnit testing mentioned.', defense_tip: 'Describe how GitHub Actions automate linting and test runs before pull request merges.' },
            { skill: 'Cloud Deployment (AWS/GCP) & Redis Caching', domain: 'Cloud, Infrastructure & DevOps', status: 'MISSING', gap_reason: 'No cloud deployment or Redis caching listed.', defense_tip: 'Explain Cache-Aside caching patterns and how in-memory key-value stores reduce database load.' },
            { skill: 'Smart India Hackathon (SIH) & Competitive Coding', domain: 'Education, Certifications & Professional Proof', status: 'MATCHED', evidence_quote: 'Participant — Smart India Hackathon (SIH) 2025; 4 Star in SQL, Java at HackerRank', defense_tip: 'Showcase your ability to innovate under intense deadlines and collaborate in cross-functional hackathon teams.' }
          ],
          experience_years: { required_years: 0, candidate_years: 1 },
          actionable_rewrites: [
            {
              target_skill: 'Relational Schemas / Databases',
              original_bullet: 'Built an expense app using debt-settlement optimization logic to track shared costs & minimize transactions.',
              upgraded_xyz_bullet: 'Architected a 3NF normalized MySQL database schema with foreign key constraints, eliminating data redundancy and resolving multi-user balances in [under 5 transactions - e.g., 3-5 transactions].',
              interview_defense_tip: 'Interviewer will ask how you modeled the expense transaction ledger and what SQL joins or indexes you implemented to prevent race conditions during concurrent settlements.'
            },
            {
              target_skill: 'PHP / MySQL API Integration',
              original_bullet: 'Built a platform using text similarity & keyword extraction to match resumes, score skills, & identify gaps.',
              upgraded_xyz_bullet: 'Engineered a full-stack resume evaluation engine in PHP and MySQL, optimizing database indexing to parse and score candidate skill alignments in [sub-250ms - e.g., 150-300ms].',
              interview_defense_tip: 'Be ready to explain your MySQL indexing strategy, foreign key constraints, and how your PHP backend calculated text similarity vectors.'
            }
          ],
          evidence_ledger: {
            status: 'COMPLETE',
            extracted_bullets_count: 14,
            included_bullets_count: 14,
            evaluated_bullets_count: 14,
            omitted_bullets_count: 0,
            ceiling: 60,
            audit_note: 'All 14 extracted candidate bullets included in rewrite anchor ledger.',
            scoring_evidence: {
              status: 'COMPLETE',
              character_count: 3200,
              character_limit: 25000,
              audit_note: 'Complete candidate resume text provided for skill classification.'
            },
            rewrite_ledger: {
              status: 'COMPLETE',
              extracted_bullets_count: 14,
              included_bullets_count: 14,
              evaluated_bullets_count: 14,
              omitted_bullets_count: 0,
              ceiling: 60,
              audit_note: 'All 14 extracted candidate bullets included in rewrite anchor ledger.'
            }
          }
        };
        this.scores = {
          overall_score: 82.5,
          must_have_score: 90.9,
          bonus_score: 20.0,
          experience_score: 100
        };
        if (typeof window !== 'undefined') {
          const urlParams = new URLSearchParams(window.location.search);
          if (urlParams.get('tab')) {
            this.filterTab = urlParams.get('tab');
          } else if (window.location.hash && window.location.hash.includes('missing')) {
            this.filterTab = 'missing';
          }
          if (urlParams.get('domain')) {
            this.selectedDomain = urlParams.get('domain');
          }
        }
      }
    },

    handleDrop(e) {
      if (e.dataTransfer && e.dataTransfer.files.length > 0) {
        this.processResumeFile(e.dataTransfer.files[0]);
      }
    },

    handleFileSelect(e) {
      if (e.target.files && e.target.files.length > 0) {
        this.processResumeFile(e.target.files[0]);
      }
    },

    processResumeFile(dropped) {
      if (!dropped) return;
      if (dropped.size > 10 * 1024 * 1024) {
        this.errorMessage = 'Resume file exceeds the 10MB limit.';
        return;
      }
      const name = dropped.name.toLowerCase();
      if (dropped.type === 'application/pdf' || name.endsWith('.pdf')) {
        this.file = dropped;
        this.errorMessage = null;
        this.extractDocument(dropped, 'resume');
      } else if (dropped.type.startsWith('text/') || name.endsWith('.txt') || name.endsWith('.md')) {
        const reader = new FileReader();
        reader.onload = (event) => {
          this.resumeText = event.target.result || '';
          this.file = null;
          this.resumeMode = 'text'; // Switch mode and populate text editor
          this.errorMessage = null;
        };
        reader.readAsText(dropped);
      } else {
        this.errorMessage = 'Please upload a PDF or plain text (.txt, .md) file for your resume.';
      }
    },

    async extractDocument(file, type) {
      if (typeof fetch === 'undefined') return;
      const isResume = (type === 'resume');
      if (isResume) {
        this.resumeExtractionLoading = true;
        this.resumeExtractionError = null;
        this.resumeExtractedText = '';
        this.resumeEditedText = '';
        this.resumeExtractionMeta = { wordCount: 0, pageCount: 0, charCount: 0 };
      } else {
        this.jdExtractionLoading = true;
        this.jdExtractionError = null;
        this.jdExtractedText = '';
        this.jdEditedText = '';
        this.jdExtractionMeta = { wordCount: 0, pageCount: 0, charCount: 0 };
      }

      try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch('api/extract.php', {
          method: 'POST',
          body: formData
        });
        let data = {};
        try {
          data = await res.json();
        } catch (_) {
          data = {};
        }
        if (!res.ok || !data.success) {
          throw new Error(data.error || `Document extraction failed (HTTP ${res.status}).`);
        }

        if (isResume) {
          this.resumeExtractedText = data.extracted_text;
          this.resumeEditedText = data.extracted_text;
          this.resumeExtractionMeta = {
            wordCount: data.word_count,
            pageCount: data.page_count,
            charCount: data.character_count
          };
          this.resumeExtractionLoading = false;
        } else {
          this.jdExtractedText = data.extracted_text;
          this.jdEditedText = data.extracted_text;
          this.jdExtractionMeta = {
            wordCount: data.word_count,
            pageCount: data.page_count,
            charCount: data.character_count
          };
          this.jdExtractionLoading = false;
        }
      } catch (err) {
        const friendly = translateErrorMessage(err.message);
        if (isResume) {
          this.resumeExtractionLoading = false;
          this.resumeExtractionError = friendly;
        } else {
          this.jdExtractionLoading = false;
          this.jdExtractionError = friendly;
        }
      }
    },

    revertResumeExtractedText() {
      this.resumeEditedText = this.resumeExtractedText;
    },

    revertJdExtractedText() {
      this.jdEditedText = this.jdExtractedText;
    },

    adjustBoxHeight(target, size) {
      // Synchronize preset state across both panes so layout remains level
      this.resumeHeightPreset = size;
      this.jdHeightPreset = size;

      if (typeof document === 'undefined') return;

      const elements = [];
      if (this.$refs) {
        if (this.$refs.resumeTextarea) elements.push(this.$refs.resumeTextarea);
        if (this.$refs.jdTextarea) elements.push(this.$refs.jdTextarea);
        if (this.$refs.resumeDropzone) elements.push(this.$refs.resumeDropzone);
        if (this.$refs.jdDropzone) elements.push(this.$refs.jdDropzone);
      }
      if (typeof document.getElementById === 'function') {
        ['resume_textarea', 'jd_textarea', 'resume_dropzone', 'jd_dropzone'].forEach(id => {
          const el = document.getElementById(id);
          if (el && !elements.includes(el)) {
            elements.push(el);
          }
        });
      }

      elements.forEach(el => {
        if (!el) return;
        if (el.classList) {
          el.classList.add('box-adjust-smooth');
        }

        if (size === 'compact') {
          el.style.height = '240px';
        } else if (size === 'comfortable') {
          el.style.height = '380px';
        } else if (size === 'expanded') {
          el.style.height = '520px';
        } else if (size === 'autofit') {
          if (el.tagName === 'TEXTAREA') {
            el.style.height = 'auto';
            const computedHeight = Math.min(680, Math.max(240, (el.scrollHeight || 240) + 12));
            el.style.height = computedHeight + 'px';
          } else {
            el.style.height = '240px';
          }
        }

        setTimeout(() => {
          if (el && el.classList) el.classList.remove('box-adjust-smooth');
        }, 320);
      });
    },

    removeFile() {
      this.file = null;
      this.resumeExtractedText = '';
      this.resumeEditedText = '';
      this.resumeExtractionLoading = false;
      this.resumeExtractionError = null;
      this.resumeInspectorOpen = false;
      this.resumeExtractionMeta = { wordCount: 0, pageCount: 0, charCount: 0 };
      const input = document.getElementById('resume');
      if (input) input.value = '';
      const inputLegacy = document.getElementById('resume_file');
      if (inputLegacy) inputLegacy.value = '';
    },

    removeJdFile() {
      this.jdFile = null;
      this.jdExtractedText = '';
      this.jdEditedText = '';
      this.jdExtractionLoading = false;
      this.jdExtractionError = null;
      this.jdInspectorOpen = false;
      this.jdExtractionMeta = { wordCount: 0, pageCount: 0, charCount: 0 };
      const input = document.getElementById('jd_file_input');
      if (input) input.value = '';
    },

    handleJdDrop(e) {
      if (e.dataTransfer && e.dataTransfer.files.length > 0) {
        this.processJdFile(e.dataTransfer.files[0]);
      }
    },

    handleJdFileSelect(e) {
      if (e.target.files && e.target.files.length > 0) {
        this.processJdFile(e.target.files[0]);
      }
    },

    processJdFile(dropped) {
      if (!dropped) return;
      if (dropped.size > 10 * 1024 * 1024) {
        this.errorMessage = 'Job description file exceeds the 10MB limit.';
        return;
      }
      const name = dropped.name.toLowerCase();
      if (dropped.type === 'application/pdf' || name.endsWith('.pdf')) {
        this.jdFile = dropped;
        this.errorMessage = null;
        this.extractDocument(dropped, 'jd');
      } else if (dropped.type.startsWith('text/') || name.endsWith('.txt') || name.endsWith('.md')) {
        const reader = new FileReader();
        reader.onload = (event) => {
          this.jobDescription = event.target.result || '';
          this.jdFile = null;
          this.jdMode = 'text'; // Switch mode and populate text editor
          this.errorMessage = null;
        };
        reader.readAsText(dropped);
      } else {
        this.errorMessage = 'Please upload a PDF or plain text (.txt, .md) file for the job description.';
      }
    },

    getClientToken() {
      try {
        let token = (typeof localStorage !== 'undefined') ? localStorage.getItem('jda_client_token') : null;
        if (!token || !/^[a-f0-9]{32}$/.test(token)) {
          const array = new Uint8Array(16);
          if (typeof window !== 'undefined' && window.crypto && typeof window.crypto.getRandomValues === 'function') {
            window.crypto.getRandomValues(array);
          } else {
            for (let i = 0; i < 16; i++) array[i] = Math.floor(Math.random() * 256);
          }
          token = Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
          if (typeof localStorage !== 'undefined') {
            localStorage.setItem('jda_client_token', token);
          }
        }
        return token;
      } catch (e) {
        // Fallback token if localStorage or crypto is restricted
        const array = new Uint8Array(16);
        for (let i = 0; i < 16; i++) array[i] = Math.floor(Math.random() * 256);
        return Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
      }
    },

    isSubmitDisabled() {
      if (this.loading) return true;
      if (this.resumeExtractionLoading || this.jdExtractionLoading) return true;

      // Resume check
      if (this.resumeMode === 'file') {
        if (!this.file) return true;
        if (this.resumeEditedText && this.resumeEditedText !== this.resumeExtractedText && this.resumeEditedText.trim().length < 80) {
          return true;
        }
      } else {
        if (this.resumeText.trim().length < 80) return true;
      }

      // JD check
      if (this.jdMode === 'file') {
        if (!this.jdFile) return true;
        if (this.jdEditedText && this.jdEditedText !== this.jdExtractedText && this.jdEditedText.trim().length < 80) {
          return true;
        }
      } else {
        if (this.jobDescription.trim().length < 80) return true;
      }

      return false;
    },

    async submitScan() {
      try {
        // 1. Check if background extraction is in progress
        if (this.resumeExtractionLoading || this.jdExtractionLoading) {
          this.errorMessage = 'Document text extraction is currently in progress. Please wait a moment.';
          return;
        }

        // 2. Validate presence and length of both inputs
        const isResumeFile = this.resumeMode === 'file' && Boolean(this.file);
        const isResumeText = this.resumeMode === 'text' && this.resumeText.trim().length >= 80;
        const isJdFile = this.jdMode === 'file' && Boolean(this.jdFile);
        const isJdText = this.jdMode === 'text' && this.jobDescription.trim().length >= 80;

        // Check for inspector edited text minimum length
        if (this.resumeMode === 'file' && this.file && this.resumeEditedText && this.resumeEditedText !== this.resumeExtractedText && this.resumeEditedText.trim().length < 80) {
          this.errorMessage = 'The edited resume text in the inspector is too short. Please provide at least 80 characters.';
          return;
        }
        if (this.jdMode === 'file' && this.jdFile && this.jdEditedText && this.jdEditedText !== this.jdExtractedText && this.jdEditedText.trim().length < 80) {
          this.errorMessage = 'The edited job description text in the inspector is too short. Please provide at least 80 characters.';
          return;
        }

        if (!isResumeFile && !isResumeText && !isJdFile && !isJdText) {
          this.errorMessage = 'Both a candidate resume and a job description (at least 80 characters each) are required before calibrating alignment.';
          return;
        }

        if (!isResumeFile && !isResumeText) {
          if (this.resumeMode === 'file') {
            this.errorMessage = 'Please attach your resume document (PDF, TXT, or MD) or switch to "Paste Text" to paste your resume.';
          } else {
            const charLen = this.resumeText.trim().length;
            const needed = 80 - charLen;
            this.errorMessage = `Your resume text needs at least 80 characters (currently ${charLen} characters, needs ${needed} more).`;
          }
          return;
        }

        if (!isJdFile && !isJdText) {
          if (this.jdMode === 'file') {
            this.errorMessage = 'Please attach your job description document (PDF, TXT, or MD) or switch to "Paste Text" to paste the job description.';
          } else {
            const charLen = this.jobDescription.trim().length;
            const needed = 80 - charLen;
            this.errorMessage = `Your job description needs at least 80 characters (currently ${charLen} characters, needs ${needed} more).`;
          }
          return;
        }

        this.loading = true;
        this.errorMessage = null;
        this.progressPercent = 20;
        this.progressMessage = '1/3 Normalizing layout geometry & decomposing ligatures...';

        const formData = new FormData();

        // If the candidate edited extracted text in the inspector, submit as text
        const isResumeEdited = this.resumeMode === 'file' && this.resumeEditedText && this.resumeEditedText !== this.resumeExtractedText;
        if (isResumeEdited) {
          formData.append('resume_mode', 'text');
          formData.append('resume_text', this.resumeEditedText.trim());
        } else {
          formData.append('resume_mode', this.resumeMode);
          if (this.resumeMode === 'file' && this.file) {
            formData.append('resume', this.file);
          } else {
            formData.append('resume_text', this.resumeText.trim());
          }
        }

        // If the candidate edited extracted JD text in the inspector, submit as text
        const isJdEdited = this.jdMode === 'file' && this.jdEditedText && this.jdEditedText !== this.jdExtractedText;
        if (isJdEdited) {
          formData.append('jd_mode', 'text');
          formData.append('job_description', this.jdEditedText.trim());
        } else {
          formData.append('jd_mode', this.jdMode);
          if (this.jdMode === 'file' && this.jdFile) {
            formData.append('job_description_file', this.jdFile);
          } else {
            formData.append('job_description', this.jobDescription.trim());
          }
        }
        formData.append('client_token', this.getClientToken());

        const res = await fetch('api/scan.php', {
          method: 'POST',
          body: formData
        });

        let data = {};
        try {
          data = await res.json();
        } catch (_) {
          data = {};
        }

        if (!res.ok) {
          throw new Error(data.error || `Server rejected scan request (HTTP ${res.status}). Your inputs were preserved.`);
        }

        this.scanUuid = data.uuid;
        this.startPolling();
      } catch (err) {
        // Retain user input in the form on submission errors
        this.loading = false;
        this.errorMessage = translateErrorMessage(err.message);
      }
    },

    startPolling() {
      let pollCount = 0;
      let consecutiveNetworkErrors = 0;
      const maxNetworkRetries = 3;
      const maxPollAttempts = 50; // 50 * 2000ms = 100s (>90s watchdog timer)

      if (this.pollTimer) {
        clearInterval(this.pollTimer);
      }

      this.pollTimer = setInterval(async () => {
        pollCount++;
        if (pollCount > maxPollAttempts) {
          clearInterval(this.pollTimer);
          this.loading = false;
          // Retain form inputs on polling timeout
          this.errorMessage = translateErrorMessage('Analysis timed out (exceeded 90 seconds limit).');
          return;
        }

        try {
          const res = await fetch(`api/status.php?uuid=${encodeURIComponent(this.scanUuid)}`, {
            headers: {
              'X-Client-Token': this.getClientToken()
            }
          });
          let data = {};
          try {
            data = await res.json();
          } catch (_) {
            data = {};
          }

          if (!res.ok) {
            throw new Error(data.error || `Status check failed (HTTP ${res.status}).`);
          }

          // Reset network retry counter on successful poll response
          consecutiveNetworkErrors = 0;

          if (data.status === 'processing') {
            this.progressPercent = 65;
            this.progressMessage = data.progress_message || '2/3 Auditing qualification evidence against role requirements...';
          } else if (data.status === 'completed') {
            clearInterval(this.pollTimer);
            this.progressPercent = 100;
            this.progressMessage = '3/3 Calculating deterministic math rubric... Complete!';
            this.scores = data.scores || this.scores;
            this.report = data.report || this.report;
            if (this.report && this.report.experience_years) {
              const rStatus = this.report.experience_years.requirement_status;
              if (rStatus === 'NOT_SPECIFIED' || rStatus === 'EXTRACTION_FAILED') {
                this.scores.experience_score = null;
              }
            }
            this.loading = false;
            this.view = 'results';
          } else if (data.status === 'failed') {
            clearInterval(this.pollTimer);
            this.loading = false;
            // Retain form inputs on worker failure
            this.errorMessage = translateErrorMessage(data.error_message);
          }
        } catch (err) {
          consecutiveNetworkErrors++;
          if (consecutiveNetworkErrors < maxNetworkRetries) {
            console.warn(`Transient polling network error (${consecutiveNetworkErrors}/${maxNetworkRetries}), retrying...`, err);
            this.progressMessage = 'Reconnecting to analysis worker...';
          } else {
            clearInterval(this.pollTimer);
            this.loading = false;
            this.errorMessage = translateErrorMessage(err.message);
          }
        }
      }, 2000); // 2-second polling cadence
    },

    resetScan(keepInputs = true) {
      if (this.pollTimer) {
        clearInterval(this.pollTimer);
      }
      this.view = 'upload';
      if (!keepInputs) {
        this.removeFile();
        this.resumeText = '';
        this.resumeMode = 'file';
        this.jobDescription = '';
        this.removeJdFile();
        this.jdMode = 'text';
      }
      this.scanUuid = null;
      this.loading = false;
      this.errorMessage = null;
      this.progressPercent = 15;
    },

    get allRequirements() {
      if (!this.report) return [];
      const core = (this.report.must_haves || []).map(item => ({
        requirement: item.requirement || '',
        domain: item.domain || 'Languages & Frameworks',
        status: item.status || 'MISSING',
        evidence_quote: item.evidence_quote || '',
        gap_reason: item.gap_reason || '',
        defense_tip: item.defense_tip || '',
        category: 'core',
        categoryLabel: 'Core Requirement'
      }));
      const bonus = (this.report.bonus_skills || []).map(item => ({
        requirement: item.skill || item.requirement || '',
        domain: item.domain || 'Cloud, Infrastructure & DevOps',
        status: item.status || 'MISSING',
        evidence_quote: item.evidence_quote || '',
        gap_reason: item.gap_reason || '',
        defense_tip: item.defense_tip || '',
        category: 'bonus',
        categoryLabel: 'Bonus Qualification'
      }));
      return [...core, ...bonus];
    },

    get availableDomains() {
      const domains = new Set();
      this.allRequirements.forEach(item => {
        if (item.domain) domains.add(item.domain);
      });
      return Array.from(domains);
    },

    get filteredRequirements() {
      let items = this.allRequirements;
      if (this.selectedDomain && this.selectedDomain !== 'all') {
        items = items.filter(item => item.domain === this.selectedDomain);
      }
      if (this.filterTab !== 'all') {
        items = items.filter(item => (item.status || '').toLowerCase() === this.filterTab.toLowerCase());
      }
      return items;
    },

    // Backwards-compatible alias for existing templates
    get filteredMustHaves() {
      return this.filteredRequirements;
    },

    get requirementsCounts() {
      let items = this.allRequirements;
      if (this.selectedDomain && this.selectedDomain !== 'all') {
        items = items.filter(i => i.domain === this.selectedDomain);
      }
      return {
        total: items.length,
        core: items.filter(i => i.category === 'core').length,
        bonus: items.filter(i => i.category === 'bonus').length,
        matched: items.filter(i => (i.status || '').toUpperCase() === 'MATCHED').length,
        weak: items.filter(i => (i.status || '').toUpperCase() === 'WEAK').length,
        missing: items.filter(i => (i.status || '').toUpperCase() === 'MISSING').length
      };
    },

    get coreSkillsSummary() {
      const core = (this.report && this.report.must_haves) ? this.report.must_haves : [];
      if (!core || core.length === 0) return 'No core requirements';
      const matched = core.filter(i => (i.status || '').toUpperCase() === 'MATCHED').length;
      return `${matched} of ${core.length} skills met`;
    },

    get bonusSkillsSummary() {
      const bonus = (this.report && this.report.bonus_skills) ? this.report.bonus_skills : [];
      if (!bonus || bonus.length === 0) return 'No bonus requirements';
      const matched = bonus.filter(i => (i.status || '').toUpperCase() === 'MATCHED').length;
      return `${matched} of ${bonus.length} skills met`;
    },

    get experienceSummary() {
      if (this.scores.experience_score === null) {
        if (this.report && this.report.experience_years && this.report.experience_years.requirement_status === 'EXTRACTION_FAILED') {
          return 'Unverified in resume';
        }
        return 'Not specified in JD';
      }
      const exp = (this.report && this.report.experience_years) ? this.report.experience_years : {};
      const cand = exp.candidate_years !== undefined ? exp.candidate_years : 0;
      const req = exp.required_years !== undefined ? exp.required_years : 0;
      const totalWf = exp.general_workforce_years !== undefined ? exp.general_workforce_years : cand;

      if (cand === 0 && totalWf > 0) {
        return `0 of ${req}+ tech yrs met (${totalWf} yrs non-tech)`;
      }
      if (cand > 0 && totalWf > cand) {
        return `${cand} of ${req}+ tech yrs met (${totalWf} yrs total)`;
      }
      return `${cand} of ${req}+ yrs met`;
    },

    get formattedScores() {
      const roundVal = (v) => (v !== null && v !== undefined && !isNaN(v)) ? Math.round(Number(v)) : 0;
      const isGated = Boolean(this.scores.is_gated);
      const rawVal = (this.scores.raw_score !== undefined && this.scores.raw_score !== null)
        ? roundVal(this.scores.raw_score)
        : roundVal(this.scores.overall_score);

      return {
        overall: roundVal(this.scores.overall_score),
        raw: rawVal,
        is_gated: isGated,
        must_have: roundVal(this.scores.must_have_score),
        bonus: (this.scores.bonus_score !== null && this.scores.bonus_score !== undefined)
          ? roundVal(this.scores.bonus_score)
          : null,
        experience: (this.scores.experience_score !== null && this.scores.experience_score !== undefined)
          ? roundVal(this.scores.experience_score)
          : null
      };
    }
  };
}

function extractContextualPlaceholder(template) {
  return 'Enter your authentic verified metric (e.g., 20%, 5 projects, 50ms)';
}

function rewriteCard(rw) {
  const template = rw.upgraded_xyz_bullet || '';
  const initialBracketMatch = template.match(/\[(.*?)\]/);
  const initiallyUnverified = Boolean(rw.requires_candidate_verification || initialBracketMatch || (rw.unverified_metrics && rw.unverified_metrics.length > 0));
  
  return {
    rawTemplate: template,
    currentBullet: template,
    hasBrackets: Boolean(initialBracketMatch),
    hasUnverifiedMetrics: initiallyUnverified,
    placeholderHint: 'Enter your authentic verified metric (e.g., 20%, 5 projects)',
    bracketLabel: '[ENTER YOUR VERIFIED METRIC]',
    metricInput: '',
    confirmedMetric: false,
    confirmedMetricValue: null,
    confirmedBulletText: null,
    copied: false,
    copyBlockedReason: null,
    viewFullRedline: false,

    get placeholderPresent() {
      return Boolean(this.currentBullet && /\[.*?\]/.test(this.currentBullet));
    },

    get isVerified() {
      if (!this.hasUnverifiedMetrics) {
        return true;
      }
      // Candidate must:
      // 1. Provide non-empty metric input without brackets
      // 2. currentBullet must contain no unresolved bracket placeholders
      // 3. currentBullet must demonstrably contain the entered metric
      // 4. Candidate must have explicitly confirmed this exact version of metric and bullet
      const trimmedInput = (this.metricInput || '').trim();
      const hasInput = trimmedInput.length > 0;
      const inputValid = hasInput && !/\[.*?\]/.test(trimmedInput);
      const bulletClean = !this.placeholderPresent;
      const metricInBullet = Boolean(hasInput && this.currentBullet && this.currentBullet.includes(trimmedInput));
      const confirmationValid = Boolean(
        this.confirmedMetric === true &&
        this.confirmedMetricValue === trimmedInput &&
        this.confirmedBulletText === this.currentBullet
      );
      return inputValid && bulletClean && metricInBullet && confirmationValid;
    },

    updateMetric() {
      // Invalidate confirmation whenever metric input changes
      this.confirmedMetric = false;
      this.confirmedMetricValue = null;
      this.confirmedBulletText = null;

      const inputVal = (this.metricInput || '').trim();
      if (inputVal.length > 0 && !inputVal.includes('[') && !inputVal.includes(']')) {
        this.currentBullet = this.rawTemplate.replace(/\[.*?\]/g, inputVal);
      } else {
        this.currentBullet = this.rawTemplate;
      }
    },

    toggleConfirm(e) {
      const trimmedInput = (this.metricInput || '').trim();
      if (this.placeholderPresent || !trimmedInput || !this.currentBullet.includes(trimmedInput)) {
        this.confirmedMetric = false;
        this.confirmedMetricValue = null;
        this.confirmedBulletText = null;
        return;
      }
      if (e && e.target && typeof e.target.checked === 'boolean') {
        this.confirmedMetric = e.target.checked;
      } else {
        this.confirmedMetric = !this.confirmedMetric;
      }
      if (this.confirmedMetric) {
        this.confirmedMetricValue = trimmedInput;
        this.confirmedBulletText = this.currentBullet;
      } else {
        this.confirmedMetricValue = null;
        this.confirmedBulletText = null;
      }
    },

    canCopy() {
      if (this.placeholderPresent) return false;
      if (this.hasUnverifiedMetrics && !this.isVerified) return false;
      return true;
    },

    copyToClipboard(text) {
      if (!this.canCopy()) {
        this.copyBlockedReason = 'Unverified metrics must be replaced and confirmed before copying.';
        setTimeout(() => { this.copyBlockedReason = null; }, 3000);
        return false;
      }

      const textToCopy = this.currentBullet || text;
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(textToCopy).then(() => {
          this.copied = true;
          setTimeout(() => { this.copied = false; }, 2000);
        }).catch(() => {
          this.fallbackCopy(textToCopy);
        });
      } else {
        this.fallbackCopy(textToCopy);
      }
      return true;
    },

    handleCopyEvent(event) {
      if (!this.canCopy()) {
        if (event) {
          event.preventDefault();
          event.stopPropagation();
        }
        this.copyBlockedReason = 'Copy blocked: Enter and confirm your authentic metric first.';
        setTimeout(() => { this.copyBlockedReason = null; }, 3000);
        return false;
      }
      return true;
    },

    fallbackCopy(text) {
      try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        this.copied = true;
        setTimeout(() => { this.copied = false; }, 2000);
      } catch (err) {
        console.error('Fallback copy failed:', err);
      }
    }
  };
}
