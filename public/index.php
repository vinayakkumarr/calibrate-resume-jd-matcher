<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') {
    ini_set('display_errors', '0');
}
?>
<!DOCTYPE html>
<html lang="en" class="h-full bg-[#FAF9F6]">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Calibrate — Precision Alignment for Engineering & Tech Roles</title>

  <!-- Brand Favicon & Device Touch Icons (SVG Scalable) -->
  <link rel="icon" type="image/svg+xml" href="assets/brand/calibrate-favicon-32.svg?v=2">
  <link rel="alternate icon" href="assets/brand/calibrate-favicon-16.svg?v=2">
  <link rel="apple-touch-icon" href="assets/brand/calibrate-app-icon-512.svg?v=2">
  <link rel="manifest" href="manifest.json">

  <!-- OpenGraph & Social Preview -->
  <meta property="og:title" content="Calibrate — Precision Alignment for Engineering & Tech Roles">
  <meta property="og:description" content="Precision technical resume alignment, deterministic requirement scoring, and grounded achievement upgrades for Engineering & Tech roles.">
  <meta property="og:image" content="assets/brand/calibrate-hero-banner.svg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="assets/brand/calibrate-hero-banner.svg">

  <!-- Google Fonts: Newsreader (Editorial Serif), Plus Jakarta Sans (Clean Body), JetBrains Mono (Telemetry) -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">

  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: {
            serif: ['Newsreader', 'Georgia', 'Cambria', 'serif'],
            sans: ['"Plus Jakarta Sans"', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
          },
          colors: {
            stone: {
              50:  '#FAF9F6',
              100: '#F5F4F0',
              200: '#E8E6DF',
              300: '#D4D0C5',
              400: '#A8A29E',
              500: '#78716C',
              600: '#57534E',
              700: '#44403C',
              800: '#292524',
              900: '#1C1917',
              950: '#0C0A09',
            }
          }
        }
      }
    }
  </script>

  <!-- jsdiff for Inline Word-Level Diffing -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jsdiff/5.1.0/diff.min.js"></script>
  
  <!-- Alpine.js Reactive Engine -->
  <script src="https://unpkg.com/alpinejs@3.13.5/dist/cdn.min.js" defer></script>
  
  <!-- Custom Archival Stylesheet (Dynamic Cache-Busting) -->
  <link rel="stylesheet" href="assets/css/style.css?v=<?= file_exists(__DIR__ . '/assets/css/style.css') ? filemtime(__DIR__ . '/assets/css/style.css') : '1.3' ?>">
</head>
<body class="min-h-full flex flex-col font-sans antialiased text-stone-900 paper-canvas selection:bg-blue-600 selection:text-white relative" x-data="analyserApp()">

  <!-- Precision Grid Cell Illuminator Canvas (Home Page Only) -->
  <canvas id="gridCanvas" x-show="view === 'upload'" class="fixed inset-0 pointer-events-none z-0 no-print print:hidden" aria-hidden="true"></canvas>

  <!-- Navigation Header -->
  <header class="header-editorial sticky top-0 z-30 no-print print:hidden">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <a href="/" class="flex items-center transition-opacity hover:opacity-90" aria-label="Calibrate Home">
          <img src="assets/brand/calibrate-wordmark-light.svg" alt="Calibrate" width="105" height="32" class="h-7 sm:h-8 w-auto shrink-0 select-none" loading="eager" decoding="async">
        </a>
        <span class="hidden md:inline-block text-stone-300 mx-1 text-xs select-none">/</span>
        <span class="hidden md:inline-block text-[11px] text-stone-500 font-mono tracking-wider">Precision Alignment for Engineering &amp; Tech Roles</span>
      </div>

      <div class="flex items-center gap-5 text-xs">
        <button x-show="view === 'results'" @click="resetScan(false)"
          class="text-xs font-medium text-stone-800 hover:text-stone-950 bg-white border border-[#E8E6DF] hover:border-stone-400 px-3.5 py-1.5 rounded-md transition-all shadow-sm">
          New Analysis
        </button>
      </div>
    </div>
  </header>

  <!-- Main Workstation -->
  <main class="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-8 sm:py-10 flex flex-col justify-center relative z-10">
    
    <!-- Upload and Ingestion View -->
    <div x-show="view === 'upload'" class="space-y-10 max-w-5xl mx-auto w-full">
      
      <!-- Headline & Subtitle -->
      <div class="text-center space-y-4 max-w-3xl mx-auto">
        <h1 class="font-serif text-3xl sm:text-4xl lg:text-5xl text-stone-900 tracking-tight font-normal leading-[1.18]">
          <span class="block">Calibrate your resume for</span>
          <em class="italic font-normal font-serif text-[#9E4F60] text-dusty-rose block sm:whitespace-nowrap">technology &amp; engineering&nbsp;roles</em>
        </h1>
        <p class="max-w-2xl mx-auto text-stone-600 text-sm sm:text-base leading-relaxed">
          Deconstruct any job description to audit your qualifications, uncover critical requirement gaps, and articulate your achievements with verifiable precision.
        </p>
      </div>

      <!-- Ingestion Form -->
      <form @submit.prevent="submitScan" novalidate x-show="!loading" class="space-y-8">
        
        <!-- In-Flight Input Orientation Inversion Helper Pill -->
        <div x-show="isSwappedDetected && !showSwapConfirmationModal" 
             x-transition:enter="transition ease-out duration-200"
             x-transition:enter-start="opacity-0 -translate-y-2"
             x-transition:enter-end="opacity-100 translate-y-0"
             x-transition:leave="transition ease-in duration-150"
             x-transition:leave-start="opacity-100"
             x-transition:leave-end="opacity-0"
             class="flex items-center justify-center -mb-3"
             style="display: none;">
          <div class="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-amber-50/95 border border-amber-200/80 text-stone-800 text-xs shadow-2xs">
            <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
            <span><strong>Orientation Notice:</strong> Inputs appear to be reversed.</span>
            <button type="button" @click="swapPanels()" 
                    class="font-semibold text-amber-900 hover:text-stone-950 underline underline-offset-2 flex items-center gap-1 cursor-pointer transition-colors">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
              </svg>
              <span>Swap Panels</span>
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-7 items-stretch">
          
          <!-- Pane 1: Candidate Resume -->
          <div class="stationery-card stationery-workstation p-5 sm:p-6 rounded-xl flex flex-col justify-between">
            <div>
              <div class="flex flex-wrap sm:flex-nowrap justify-between items-center gap-2 mb-3">
                <div class="flex items-baseline gap-2.5">
                  <label class="block text-base font-semibold text-stone-900 tracking-tight">Resume</label>
                  <span x-show="resumeMode === 'file'" class="text-[11px] text-stone-400 font-mono">PDF, TXT up to 10MB</span>
                  <span x-show="resumeMode === 'text'" class="text-[11px] text-stone-400 font-mono" x-text="resumeText.trim().length + ' / 25,000'"></span>
                </div>
                <div class="flex items-center gap-1.5 sm:gap-2">
                  <!-- Ingestion Mode Toggle -->
                  <div class="flex items-center bg-stone-100 p-0.5 rounded-md border border-[#E8E6DF] text-[11px] font-medium">
                    <button type="button" @click="resumeMode = 'file'" 
                            :class="resumeMode === 'file' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500 hover:text-stone-800'"
                            class="px-2.5 py-1 rounded transition-all">
                      Upload File
                    </button>
                    <button type="button" @click="resumeMode = 'text'" 
                            :class="resumeMode === 'text' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500 hover:text-stone-800'"
                            class="px-2.5 py-1 rounded transition-all">
                      Paste Text
                    </button>
                  </div>
                </div>
              </div>

              <!-- Mode A: File Dropzone (PDF or TXT) -->
              <div x-show="resumeMode === 'file'"
                   x-transition:enter="transition ease-out duration-150"
                   x-transition:enter-start="opacity-0 translate-y-1"
                   x-transition:enter-end="opacity-100 translate-y-0">
                
                <!-- 1. Empty Dropzone -->
                <div x-show="!file" id="resume_dropzone" x-ref="resumeDropzone"
                     class="border-2 border-dashed rounded-xl p-5 text-center cursor-pointer flex flex-col items-center justify-center min-h-[240px] dropzone-canvas border-[#E8E6DF] hover:border-stone-400 bg-stone-50/40"
                     tabindex="0"
                     role="button"
                     aria-label="Upload candidate resume document"
                     @keydown.enter.prevent="$refs.resumeInput.click()"
                     @keydown.space.prevent="$refs.resumeInput.click()"
                     @dragover.prevent="$el.classList.add('dropzone-dragover')"
                     @dragleave.prevent="$el.classList.remove('dropzone-dragover')"
                     @drop.prevent="$el.classList.remove('dropzone-dragover'); handleDrop($event)">
                  
                  <input type="file" id="resume" x-ref="resumeInput" accept=".pdf,.txt,.md" class="hidden" 
                         @change="handleFileSelect($event)">
                  
                  <label for="resume" class="cursor-pointer block w-full">
                    <div class="space-y-2.5">
                      <div class="mx-auto w-11 h-11 rounded-lg bg-white border border-[#E8E6DF] text-stone-600 flex items-center justify-center shadow-xs">
                        <svg class="w-5 h-5 text-stone-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
                        </svg>
                      </div>
                      <div class="space-y-1">
                        <p class="text-sm font-medium text-stone-800">Drop your resume PDF or text file here, or <span class="underline underline-offset-2 text-stone-900">browse</span></p>
                        <p class="text-xs text-stone-400 font-mono">PDF, TXT, or Markdown up to 10MB</p>
                      </div>
                    </div>
                  </label>
                </div>

                <!-- 2. Staged File & Extracted Inspector Container -->
                <div x-show="file" class="space-y-4">
                  <div class="stationery-staged-document p-4 rounded-xl space-y-3">
                    <div class="flex items-start justify-between gap-3">
                      <div class="flex items-center gap-3 min-w-0">
                        <div class="w-10 h-10 rounded-lg bg-stone-100 text-stone-800 flex items-center justify-center flex-shrink-0 border border-stone-200">
                          <svg class="w-5 h-5 text-stone-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                          </svg>
                        </div>
                        <div class="min-w-0">
                          <p class="text-sm font-semibold text-stone-900 truncate" x-text="file ? file.name : ''"></p>
                          <p class="text-[11px] text-stone-500 font-mono mt-0.5">
                            <span x-text="file ? (file.size / 1024).toFixed(1) + ' KB' : ''"></span>
                            <template x-if="resumeExtractionMeta.wordCount > 0">
                              <span> &bull; <span x-text="resumeExtractionMeta.wordCount"></span> words</span>
                            </template>
                            <template x-if="resumeExtractionMeta.pageCount > 0">
                              <span> &bull; <span x-text="resumeExtractionMeta.pageCount"></span> page<span x-show="resumeExtractionMeta.pageCount > 1">s</span></span>
                            </template>
                          </p>
                        </div>
                      </div>

                      <button type="button" @click="removeFile()" class="text-xs text-stone-400 hover:text-stone-900 transition-colors py-1 px-2 rounded hover:bg-stone-50">
                        Remove
                      </button>
                    </div>

                    <!-- Extraction Verification Bar -->
                    <div class="pt-2 border-t border-stone-100 flex flex-wrap items-center justify-between gap-2 text-xs">
                      <div class="flex items-center gap-2">
                        <template x-if="resumeExtractionLoading">
                          <div class="flex items-center gap-1.5 text-stone-500 font-mono text-[11px]">
                            <span class="w-3 h-3 border border-stone-400 border-t-stone-900 rounded-full animate-spin"></span>
                            <span>Extracting layout-aware text...</span>
                          </div>
                        </template>
                        <template x-if="!resumeExtractionLoading && resumeExtractedText">
                          <div class="flex items-center gap-1.5 text-stone-700 text-[11px]">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
                            <span class="font-mono" x-text="(resumeExtractionMeta.wordCount || 0) + ' words extracted'"></span>
                            <span x-show="resumeEditedText !== resumeExtractedText" class="px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 text-[10px] font-mono border border-amber-200">Edited</span>
                          </div>
                        </template>
                        <template x-if="resumeExtractionError">
                          <div class="text-rose-600 text-[11px] font-mono">
                            <span x-text="resumeExtractionError"></span>
                          </div>
                        </template>
                      </div>

                      <!-- Toggle Inspector Pill Button -->
                      <template x-if="resumeExtractedText">
                        <button type="button" @click="resumeInspectorOpen = !resumeInspectorOpen"
                                class="inline-flex items-center gap-1.5 text-[11px] font-medium text-stone-700 hover:text-stone-950 px-2.5 py-1 rounded border border-stone-200 hover:border-stone-400 bg-stone-50 transition-all shadow-2xs">
                          <svg class="w-3.5 h-3.5 text-stone-500 transition-transform duration-200" :class="{ 'rotate-180': resumeInspectorOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                          </svg>
                          <span x-text="resumeInspectorOpen ? 'Hide Extracted Content' : 'Inspect & Edit Extracted Text'"></span>
                        </button>
                      </template>
                    </div>

                    <!-- Extracted Text Inspector Editor Drawer -->
                    <div x-show="resumeInspectorOpen" x-transition class="pt-3 border-t border-[#E8E6DF] space-y-2.5">
                      <div class="flex items-center justify-between text-[11px] text-stone-500">
                        <span class="font-mono uppercase tracking-wider text-stone-600 font-medium">Verbatim Parser Representation</span>
                        <div class="flex items-center gap-3">
                          <span class="font-mono"><span x-text="resumeEditedText.length"></span> characters</span>
                          <button type="button" x-show="resumeEditedText !== resumeExtractedText" @click="revertResumeExtractedText()"
                                  class="text-stone-600 hover:text-stone-950 underline underline-offset-2">
                            Revert to Original
                          </button>
                        </div>
                      </div>
                      <p class="text-[11px] text-stone-500 leading-normal">
                        This is the exact plain text the scoring engine reads from your document. You can fix broken OCR words, adjust formatting, or add missing bullet details before analyzing.
                      </p>
                      <textarea x-model="resumeEditedText" rows="8"
                                class="w-full min-h-[160px] max-h-[680px] text-xs font-mono p-3 bg-[#FAF9F6] border border-[#E8E6DF] rounded-lg textarea-canvas outline-none leading-relaxed text-stone-800 resize-y"
                                placeholder="Extracted resume text..."></textarea>
                    </div>
                  </div>
                </div>

              </div>

              <!-- Mode B: Textarea -->
              <div x-show="resumeMode === 'text'"
                   x-transition:enter="transition ease-out duration-150"
                   x-transition:enter-start="opacity-0 translate-y-1"
                   x-transition:enter-end="opacity-100 translate-y-0">
                <textarea id="resume_textarea" x-ref="resumeTextarea" x-model="resumeText" minlength="80" maxlength="25000"
                  placeholder="Paste your technical resume text here (engineering experience, data pipelines, cloud/systems architecture, technical skills, and projects)..."
                  class="w-full min-h-[240px] max-h-[680px] rounded-lg border border-[#E8E6DF] p-3.5 sm:p-4 text-sm focus:outline-none transition-colors resize-y text-stone-900 placeholder-stone-400 bg-stone-50/30 leading-relaxed textarea-canvas"></textarea>
              </div>
            </div>

            <!-- Footer info & action -->
            <div class="flex flex-wrap items-center justify-between gap-2 text-xs pt-3 mt-1 text-stone-400 border-t border-stone-100">
              <div>
                <span x-show="resumeMode === 'file' && !file">Attach any PDF or text file</span>
                <span x-show="resumeMode === 'file' && file" class="text-emerald-800 font-medium">Document attached</span>
                <span x-show="resumeMode === 'text' && resumeText.trim().length === 0">Minimum 80 characters needed</span>
                <span x-show="resumeMode === 'text' && resumeText.trim().length > 0 && resumeText.trim().length < 80" 
                      class="text-amber-800 font-medium"
                      x-text="'Needs ' + (80 - resumeText.trim().length) + ' more characters'">
                </span>
                <span x-show="resumeMode === 'text' && resumeText.trim().length >= 80 && resumeText.trim().length < 200" 
                      class="text-amber-800 font-medium flex items-center gap-1"
                      title="Tip: Adding more work experience unlocks richer bullet rewrites">
                  <span>Concise input &bull; Ready for analysis</span>
                </span>
                <span x-show="resumeMode === 'text' && resumeText.trim().length >= 200" class="text-emerald-800 font-medium">Ready for comprehensive analysis</span>
              </div>
              
              <div class="flex items-center gap-2">
                <!-- Smooth Box Height Adjustment Settings -->
                <div x-show="resumeMode === 'text' || !file" x-transition:enter="transition ease-out duration-150" class="flex items-center bg-stone-100/80 p-0.5 rounded-md border border-[#E8E6DF] text-[10px] font-mono text-stone-600">
                  <button type="button" @click="adjustBoxHeight('resume', 'compact')" 
                          :class="resumeHeightPreset === 'compact' ? 'bg-white text-stone-900 shadow-2xs font-semibold' : 'text-stone-500 hover:text-stone-800'"
                          title="Compact box height (240px)" class="px-1.5 py-0.5 rounded transition-all">
                    240px
                  </button>
                  <button type="button" @click="adjustBoxHeight('resume', 'comfortable')" 
                          :class="resumeHeightPreset === 'comfortable' ? 'bg-white text-stone-900 shadow-2xs font-semibold' : 'text-stone-500 hover:text-stone-800'"
                          title="Comfortable box height (380px)" class="px-1.5 py-0.5 rounded transition-all">
                    380px
                  </button>
                  <button type="button" @click="adjustBoxHeight('resume', 'expanded')" 
                          :class="resumeHeightPreset === 'expanded' ? 'bg-white text-stone-900 shadow-2xs font-semibold' : 'text-stone-500 hover:text-stone-800'"
                          title="Expanded box height (520px)" class="px-1.5 py-0.5 rounded transition-all">
                    520px
                  </button>
                  <button type="button" @click="adjustBoxHeight('resume', 'autofit')" 
                          :class="resumeHeightPreset === 'autofit' ? 'bg-white text-stone-900 shadow-2xs font-semibold' : 'text-stone-500 hover:text-stone-800'"
                          title="Smoothly auto-fit box height to content" class="px-1.5 py-0.5 rounded transition-all flex items-center gap-0.5">
                    <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/></svg>
                    <span>Fit</span>
                  </button>
                </div>

                <button x-show="resumeMode === 'file' && file" type="button" @click="removeFile()" class="text-xs text-stone-400 hover:text-stone-800 transition-colors">
                  Remove file
                </button>
                <button x-show="resumeMode === 'text' && resumeText.trim().length > 0" type="button" @click="resumeText = ''" class="text-xs text-stone-400 hover:text-stone-800 transition-colors">
                  Clear text
                </button>
              </div>
            </div>
          </div>

          <!-- Pane 2: Target Job Description -->
          <div class="stationery-card stationery-workstation p-5 sm:p-6 rounded-xl flex flex-col justify-between">
            <div>
              <div class="flex flex-wrap sm:flex-nowrap justify-between items-center gap-2 mb-3">
                <div class="flex items-baseline gap-2.5">
                  <label class="block text-base font-semibold text-stone-900 tracking-tight">Job Description</label>
                  <span x-show="jdMode === 'file'" class="text-[11px] text-stone-400 font-mono">PDF, TXT up to 10MB</span>
                  <span x-show="jdMode === 'text'" class="text-[11px] text-stone-400 font-mono" x-text="jobDescription.trim().length + ' / 15,000'"></span>
                </div>
                <div class="flex items-center gap-1.5 sm:gap-2">
                  <!-- Ingestion Mode Toggle -->
                  <div class="flex items-center bg-stone-100 p-0.5 rounded-md border border-[#E8E6DF] text-[11px] font-medium">
                    <button type="button" @click="jdMode = 'file'" 
                            :class="jdMode === 'file' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500 hover:text-stone-800'"
                            class="px-2.5 py-1 rounded transition-all">
                      Upload File
                    </button>
                    <button type="button" @click="jdMode = 'text'" 
                            :class="jdMode === 'text' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500 hover:text-stone-800'"
                            class="px-2.5 py-1 rounded transition-all">
                      Paste Text
                    </button>
                  </div>
                </div>
              </div>
              
              <!-- Mode A: Textarea -->
              <div x-show="jdMode === 'text'"
                   x-transition:enter="transition ease-out duration-150"
                   x-transition:enter-start="opacity-0 translate-y-1"
                   x-transition:enter-end="opacity-100 translate-y-0">
                <textarea id="jd_textarea" x-ref="jdTextarea" x-model="jobDescription" minlength="80" maxlength="15000"
                  placeholder="Paste the target job description here (e.g. Software, Data, DevOps/SRE, Security, Systems, Cloud, or Modern Tech requirements)..."
                  class="w-full min-h-[240px] max-h-[680px] rounded-lg border border-[#E8E6DF] p-3.5 sm:p-4 text-sm focus:outline-none transition-colors resize-y text-stone-900 placeholder-stone-400 bg-stone-50/30 leading-relaxed textarea-canvas"></textarea>
              </div>

              <!-- Mode B: File Dropzone (PDF or TXT) -->
              <div x-show="jdMode === 'file'"
                   x-transition:enter="transition ease-out duration-150"
                   x-transition:enter-start="opacity-0 translate-y-1"
                   x-transition:enter-end="opacity-100 translate-y-0">
                
                <!-- 1. Empty JD Dropzone -->
                <div x-show="!jdFile" id="jd_dropzone" x-ref="jdDropzone"
                     class="border-2 border-dashed rounded-xl p-5 text-center cursor-pointer flex flex-col items-center justify-center min-h-[240px] dropzone-canvas border-[#E8E6DF] hover:border-stone-400 bg-stone-50/40"
                     tabindex="0"
                     role="button"
                     aria-label="Upload target job description document"
                     @keydown.enter.prevent="$refs.jdInput.click()"
                     @keydown.space.prevent="$refs.jdInput.click()"
                     @dragover.prevent="$el.classList.add('dropzone-dragover')"
                     @dragleave.prevent="$el.classList.remove('dropzone-dragover')"
                     @drop.prevent="$el.classList.remove('dropzone-dragover'); handleJdDrop($event)">
                  
                  <input type="file" id="jd_file_input" x-ref="jdInput" accept=".pdf,.txt,.md" class="hidden" 
                         @change="handleJdFileSelect($event)">
                  
                  <label for="jd_file_input" class="cursor-pointer block w-full">
                    <div class="space-y-2.5">
                      <div class="mx-auto w-11 h-11 rounded-lg bg-white border border-[#E8E6DF] text-stone-600 flex items-center justify-center shadow-xs">
                        <svg class="w-5 h-5 text-stone-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                      </div>
                      <div class="space-y-1">
                        <p class="text-sm font-medium text-stone-800">Drop job description PDF or text file here, or <span class="underline underline-offset-2 text-stone-900">browse</span></p>
                        <p class="text-xs text-stone-400 font-mono">PDF, TXT, or Markdown up to 10MB</p>
                      </div>
                    </div>
                  </label>
                </div>

                <!-- 2. Staged JD File & Extracted Inspector Container -->
                <div x-show="jdFile" class="space-y-4">
                  <div class="stationery-staged-document p-4 rounded-xl space-y-3">
                    <div class="flex items-start justify-between gap-3">
                      <div class="flex items-center gap-3 min-w-0">
                        <div class="w-10 h-10 rounded-lg bg-stone-100 text-stone-800 flex items-center justify-center flex-shrink-0 border border-stone-200">
                          <svg class="w-5 h-5 text-stone-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                          </svg>
                        </div>
                        <div class="min-w-0">
                          <p class="text-sm font-semibold text-stone-900 truncate" x-text="jdFile ? jdFile.name : ''"></p>
                          <p class="text-[11px] text-stone-500 font-mono mt-0.5">
                            <span x-text="jdFile ? (jdFile.size / 1024).toFixed(1) + ' KB' : ''"></span>
                            <template x-if="jdExtractionMeta.wordCount > 0">
                              <span> &bull; <span x-text="jdExtractionMeta.wordCount"></span> words</span>
                            </template>
                            <template x-if="jdExtractionMeta.pageCount > 0">
                              <span> &bull; <span x-text="jdExtractionMeta.pageCount"></span> page<span x-show="jdExtractionMeta.pageCount > 1">s</span></span>
                            </template>
                          </p>
                        </div>
                      </div>

                      <button type="button" @click="removeJdFile()" class="text-xs text-stone-400 hover:text-stone-900 transition-colors py-1 px-2 rounded hover:bg-stone-50">
                        Remove
                      </button>
                    </div>

                    <!-- Extraction Verification Bar -->
                    <div class="pt-2 border-t border-stone-100 flex flex-wrap items-center justify-between gap-2 text-xs">
                      <div class="flex items-center gap-2">
                        <template x-if="jdExtractionLoading">
                          <div class="flex items-center gap-1.5 text-stone-500 font-mono text-[11px]">
                            <span class="w-3 h-3 border border-stone-400 border-t-stone-900 rounded-full animate-spin"></span>
                            <span>Extracting layout-aware text...</span>
                          </div>
                        </template>
                        <template x-if="!jdExtractionLoading && jdExtractedText">
                          <div class="flex items-center gap-1.5 text-stone-700 text-[11px]">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
                            <span class="font-mono" x-text="(jdExtractionMeta.wordCount || 0) + ' words extracted'"></span>
                            <span x-show="jdEditedText !== jdExtractedText" class="px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 text-[10px] font-mono border border-amber-200">Edited</span>
                          </div>
                        </template>
                        <template x-if="jdExtractionError">
                          <div class="text-rose-600 text-[11px] font-mono">
                            <span x-text="jdExtractionError"></span>
                          </div>
                        </template>
                      </div>

                      <!-- Toggle Inspector Pill Button -->
                      <template x-if="jdExtractedText">
                        <button type="button" @click="jdInspectorOpen = !jdInspectorOpen"
                                class="inline-flex items-center gap-1.5 text-[11px] font-medium text-stone-700 hover:text-stone-950 px-2.5 py-1 rounded border border-stone-200 hover:border-stone-400 bg-stone-50 transition-all shadow-2xs">
                          <svg class="w-3.5 h-3.5 text-stone-500 transition-transform duration-200" :class="{ 'rotate-180': jdInspectorOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                          </svg>
                          <span x-text="jdInspectorOpen ? 'Hide Extracted Content' : 'Inspect & Edit Extracted Text'"></span>
                        </button>
                      </template>
                    </div>

                    <!-- Extracted Text Inspector Editor Drawer -->
                    <div x-show="jdInspectorOpen" x-transition class="pt-3 border-t border-[#E8E6DF] space-y-2.5">
                      <div class="flex items-center justify-between text-[11px] text-stone-500">
                        <span class="font-mono uppercase tracking-wider text-stone-600 font-medium">Verbatim Parser Representation</span>
                        <div class="flex items-center gap-3">
                          <span class="font-mono"><span x-text="jdEditedText.length"></span> characters</span>
                          <button type="button" x-show="jdEditedText !== jdExtractedText" @click="revertJdExtractedText()"
                                  class="text-stone-600 hover:text-stone-950 underline underline-offset-2">
                            Revert to Original
                          </button>
                        </div>
                      </div>
                      <p class="text-[11px] text-stone-500 leading-normal">
                        This is the exact plain text the scoring engine reads from your job description. You can adjust requirements or add context before analyzing.
                      </p>
                      <textarea x-model="jdEditedText" rows="8"
                                class="w-full min-h-[160px] max-h-[680px] text-xs font-mono p-3 bg-[#FAF9F6] border border-[#E8E6DF] rounded-lg textarea-canvas outline-none leading-relaxed text-stone-800 resize-y"
                                placeholder="Extracted job description text..."></textarea>
                    </div>
                  </div>
                </div>

              </div>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-2 text-xs pt-3 mt-1 text-stone-400 border-t border-stone-100">
              <div>
                <span x-show="jdMode === 'file' && !jdFile">Attach any PDF or text file</span>
                <span x-show="jdMode === 'file' && jdFile" class="text-emerald-800 font-medium">Document attached</span>
                <span x-show="jdMode === 'text' && jobDescription.trim().length === 0">Minimum 80 characters needed</span>
                <span x-show="jdMode === 'text' && jobDescription.trim().length > 0 && jobDescription.trim().length < 80" 
                      class="text-amber-800 font-medium"
                      x-text="'Needs ' + (80 - jobDescription.trim().length) + ' more characters'">
                </span>
                <span x-show="jdMode === 'text' && jobDescription.trim().length >= 80 && jobDescription.trim().length < 200" 
                      class="text-amber-800 font-medium flex items-center gap-1"
                      title="Tip: Adding full responsibilities unlocks richer bullet rewrites">
                  <span>Concise input &bull; Ready for analysis</span>
                </span>
                <span x-show="jdMode === 'text' && jobDescription.trim().length >= 200" class="text-emerald-800 font-medium">Ready for comprehensive analysis</span>
              </div>

              <div class="flex items-center gap-2">
                <!-- Smooth Box Height Adjustment Settings -->
                <div x-show="jdMode === 'text' || !jdFile" x-transition:enter="transition ease-out duration-150" class="flex items-center bg-stone-100/80 p-0.5 rounded-md border border-[#E8E6DF] text-[10px] font-mono text-stone-600">
                  <button type="button" @click="adjustBoxHeight('jd', 'compact')" 
                          :class="jdHeightPreset === 'compact' ? 'bg-white text-stone-900 shadow-2xs font-semibold' : 'text-stone-500 hover:text-stone-800'"
                          title="Compact box height (240px)" class="px-1.5 py-0.5 rounded transition-all">
                    240px
                  </button>
                  <button type="button" @click="adjustBoxHeight('jd', 'comfortable')" 
                          :class="jdHeightPreset === 'comfortable' ? 'bg-white text-stone-900 shadow-2xs font-semibold' : 'text-stone-500 hover:text-stone-800'"
                          title="Comfortable box height (380px)" class="px-1.5 py-0.5 rounded transition-all">
                    380px
                  </button>
                  <button type="button" @click="adjustBoxHeight('jd', 'expanded')" 
                          :class="jdHeightPreset === 'expanded' ? 'bg-white text-stone-900 shadow-2xs font-semibold' : 'text-stone-500 hover:text-stone-800'"
                          title="Expanded box height (520px)" class="px-1.5 py-0.5 rounded transition-all">
                    520px
                  </button>
                  <button type="button" @click="adjustBoxHeight('jd', 'autofit')" 
                          :class="jdHeightPreset === 'autofit' ? 'bg-white text-stone-900 shadow-2xs font-semibold' : 'text-stone-500 hover:text-stone-800'"
                          title="Smoothly auto-fit box height to content" class="px-1.5 py-0.5 rounded transition-all flex items-center gap-0.5">
                    <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/></svg>
                    <span>Fit</span>
                  </button>
                </div>

                <button x-show="jdMode === 'file' && jdFile" type="button" @click="removeJdFile()" class="text-xs text-stone-400 hover:text-stone-800 transition-colors">
                  Remove file
                </button>
                <button x-show="jdMode === 'text' && jobDescription.trim().length > 0" type="button" @click="jobDescription = ''" class="text-xs text-stone-400 hover:text-stone-800 transition-colors">
                  Clear text
                </button>
              </div>
            </div>
          </div>

        </div>

        <!-- In-Line Validation & Error Notification (Always Visible Above Submit Button) -->
        <div x-show="errorMessage" x-transition:enter="transition ease-out duration-150" x-transition:enter-start="opacity-0 translate-y-1" x-transition:enter-end="opacity-100 translate-y-0"
             class="max-w-xl mx-auto p-4 bg-white rounded-xl border border-rose-200 text-stone-900 text-xs space-y-2 shadow-xs" aria-live="assertive">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-1.5 font-semibold text-rose-800">
              <svg class="w-4 h-4 text-rose-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
              <span>Action Required</span>
            </div>
            <button type="button" @click="errorMessage = null" class="text-stone-400 hover:text-stone-700 p-1">Dismiss</button>
          </div>
          <p x-text="errorMessage" class="text-stone-700 leading-relaxed font-sans"></p>
          <p class="text-stone-400 text-[11px]">Your inputs have been preserved in the form above.</p>
        </div>

        <!-- Submit Action & Privacy Disclosure -->
        <div class="flex flex-col items-center justify-center gap-2.5">
          <button type="submit"
            :class="isSubmitDisabled() ? 'btn-calibrate-primary opacity-65 hover:opacity-85 cursor-pointer' : 'btn-calibrate-primary cursor-pointer'"
            class="text-sm font-medium py-3.5 px-8 rounded-lg flex items-center gap-2.5 group transition-all">
            <span>Calibrate Alignment</span>
            <svg class="w-4 h-4 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
            </svg>
          </button>

          <!-- Discreet Privacy Notice Trigger -->
          <button type="button"
                  @click="showPrivacyNotice = true"
                  class="inline-flex items-center gap-1.5 text-xs text-stone-500 hover:text-stone-800 transition-colors focus:outline-none focus:ring-2 focus:ring-stone-400 focus:ring-offset-2 rounded-sm py-1 px-1.5 cursor-pointer"
                  aria-haspopup="dialog"
                  :aria-expanded="showPrivacyNotice ? 'true' : 'false'">
            <svg class="w-3.5 h-3.5 text-stone-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="10" stroke-width="1.8"/>
              <path stroke-linecap="round" stroke-width="1.8" d="M12 16v-4m0-4h.01"/>
            </svg>
            <span class="underline underline-offset-2 decoration-stone-300 hover:decoration-stone-600">How your data is processed</span>
          </button>
        </div>
      </form>

      <!-- Three Core Value Pillars -->
      <div x-show="!loading" class="pt-8 border-t border-[#E8E6DF] grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
        <div class="stationery-card stationery-card-lift p-5 sm:p-5.5 rounded-xl space-y-2.5 border border-[#E8E6DF]">
          <div class="flex items-center gap-2.5">
            <span class="px-1.5 py-0.5 rounded bg-orange-50/90 text-[#EA580C] border border-orange-200/70 font-mono text-[10.5px] font-semibold tracking-wide">01</span>
            <h3 class="font-serif text-[15px] sm:text-base font-medium text-stone-900 tracking-tight">Verbatim Match Audit</h3>
          </div>
          <p class="text-xs text-stone-600 leading-relaxed">
            Objective alignment scored from verbatim citations across your resume, prioritizing proven competencies over keyword density.
          </p>
        </div>

        <div class="stationery-card stationery-card-lift p-5 sm:p-5.5 rounded-xl space-y-2.5 border border-[#E8E6DF]">
          <div class="flex items-center gap-2.5">
            <span class="px-1.5 py-0.5 rounded bg-orange-50/90 text-[#EA580C] border border-orange-200/70 font-mono text-[10.5px] font-semibold tracking-wide">02</span>
            <h3 class="font-serif text-[15px] sm:text-base font-medium text-stone-900 tracking-tight">Requirements Ledger</h3>
          </div>
          <p class="text-xs text-stone-600 leading-relaxed">
            Prioritizes core must-haves versus bonus qualifications so you know your exact competitive standing before applying.
          </p>
        </div>

        <div class="stationery-card stationery-card-lift p-5 sm:p-5.5 rounded-xl space-y-2.5 border border-[#E8E6DF]">
          <div class="flex items-center gap-2.5">
            <span class="px-1.5 py-0.5 rounded bg-orange-50/90 text-[#EA580C] border border-orange-200/70 font-mono text-[10.5px] font-semibold tracking-wide">03</span>
            <h3 class="font-serif text-[15px] sm:text-base font-medium text-stone-900 tracking-tight">XYZ Bullet Upgrades</h3>
          </div>
          <p class="text-xs text-stone-600 leading-relaxed">
            Generates metric-locked accomplishment rewrites with tactical defense strategies for the technical interview.
          </p>
        </div>
      </div>

      <!-- Loading State -->
      <div x-show="loading" class="max-w-md mx-auto my-12 p-8 stationery-card rounded-xl text-center space-y-4" aria-live="polite">
        <div class="w-8 h-8 rounded-full border-2 border-stone-200 border-t-stone-900 animate-spin mx-auto"></div>
        <div class="space-y-1">
          <p class="text-sm font-medium text-stone-900" x-text="progressMessage"></p>
          <p class="text-xs text-stone-400">Verifying verbatim resume citations &amp; calculating domain fit (~10–15s).</p>
        </div>
        <div class="w-full bg-stone-100 rounded-full h-1 overflow-hidden">
          <div class="bg-stone-900 h-1 transition-all duration-300" :style="'width: ' + progressPercent + '%'"></div>
        </div>
      </div>



    </div>

    <!-- Results View -->
    <div x-show="view === 'results'" class="space-y-8 results-view">
      
      <!-- Print-Only Executive Letterhead -->
      <div class="hidden print:flex items-center justify-between pb-3 mb-4 border-b-2 border-stone-800 print-header">
        <div class="flex items-center gap-2.5">
          <img src="assets/brand/calibrate-wordmark-light.svg" alt="Calibrate Logo" height="22" class="h-5.5 w-auto">
          <span class="text-[11px] text-stone-500 font-mono tracking-wider">/ PRECISION ALIGNMENT REPORT</span>
        </div>
        <div class="text-right text-[9.5px] font-mono text-stone-500 leading-tight">
          <span class="font-semibold text-stone-800">Confidential Candidate Evaluation</span>
          <span class="block text-stone-400 text-[8.5px] mt-0.5">Objective Verbatim Evidence &bull; Strategic Interview Defense</span>
        </div>
      </div>

      <!-- Subheader -->
      <div class="flex flex-col sm:flex-row sm:items-baseline justify-between gap-4 pb-5 border-b border-[#E8E6DF]">
        <div>
          <span class="text-xs font-mono uppercase tracking-wider text-stone-400 block mb-1">Calibrate Alignment Report</span>
          <h2 class="font-serif text-3xl font-medium text-stone-900 tracking-tight" x-text="report.job_title_detected || 'Target Role Analysis'"></h2>
        </div>
        <div class="flex items-center gap-3 no-print print:hidden">
          <button @click="resetScan(true)" 
                  class="text-xs font-medium text-stone-700 bg-white border border-[#E8E6DF] hover:border-stone-400 px-3.5 py-1.5 rounded-md transition-all shadow-xs">
            Edit inputs
          </button>
          <button @click="window.print()" 
                  class="text-xs font-medium text-stone-700 bg-white border border-[#E8E6DF] hover:border-stone-400 px-3.5 py-1.5 rounded-md transition-all shadow-xs">
            Print summary
          </button>
        </div>
      </div>

      <!-- Pillar 1: Match Audit Overview -->
      <div class="stationery-card p-4 sm:p-5 rounded-xl border border-[#E8E6DF] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5">
        <!-- Left: Compact Score Badge -->
        <div class="flex items-center gap-4 shrink-0">
          <div class="space-y-0.5">
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-mono text-stone-400 uppercase tracking-wider">
                Pillar 1 &bull; The Match Audit
              </span>
              <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-stone-100 text-stone-600 border border-stone-200">Verbatim Proof</span>
              <span x-show="report && report.evidence_ledger && report.evidence_ledger.scoring_evidence && report.evidence_ledger.scoring_evidence.status === 'CAPPED'"
                    class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-medium">
                Scoring Text Clamped
              </span>
            </div>
            <!-- Un-gated standard single score display -->
            <div x-show="!formattedScores.is_gated" class="flex items-baseline gap-2">
              <span class="font-serif text-3xl sm:text-4xl font-medium text-stone-900 tracking-tight" x-text="formattedScores.overall + '%'"></span>
              <span class="text-xs text-stone-500 font-medium">technical match</span>
            </div>

            <!-- Gated dual-metric proportional lockup (Subtle scale, zero badges) -->
            <div x-show="formattedScores.is_gated" class="space-y-0.5">
              <div class="flex items-baseline flex-wrap gap-x-1.5 gap-y-0.5">
                <span class="font-serif text-3xl font-medium text-stone-900 tracking-tight" x-text="formattedScores.raw + '%'"></span>
                <span class="text-xs text-stone-500 font-normal">technical match</span>
                <span class="text-stone-300 font-light mx-1 select-none">&bull;</span>
                <span class="font-serif text-2xl font-medium text-stone-700 tracking-tight" x-text="formattedScores.overall + '%'"></span>
                <span class="text-xs text-stone-500 font-normal">screening fit</span>
              </div>
              <p class="text-[11px] font-mono text-stone-400">Core requirements below 50% threshold</p>
            </div>
          </div>
        </div>

        <!-- Right: 3-Category Breakdown Meters in a Horizontal Row + Unified Footnote -->
        <div class="flex-1 max-w-2xl pt-3 md:pt-0 border-t md:border-t-0 md:border-l border-[#E8E6DF] md:pl-6 text-xs flex flex-col justify-center">
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            
            <!-- Column 1: Must-Have Skills -->
            <div class="space-y-1.5">
              <div class="flex justify-between items-baseline font-medium text-stone-700">
                <span class="text-[11px]">Must-Have Skills</span>
                <span class="font-mono text-stone-900 text-[11px]" x-text="formattedScores.must_have + '%'"></span>
              </div>
              <div class="w-full bg-stone-100 rounded-full h-1 overflow-hidden">
                <div class="bg-stone-900 h-1 rounded-full transition-all duration-300" :style="'width: ' + (scores.must_have_score || 0) + '%'"></div>
              </div>
              <span class="text-[10.5px] font-mono text-stone-500 block truncate" x-text="coreSkillsSummary"></span>
            </div>

            <!-- Column 2: Experience Tenure -->
            <div class="space-y-1.5">
              <div class="flex justify-between items-baseline font-medium text-stone-700">
                <span class="text-[11px]">Experience Tenure</span>
                <span x-show="scores.experience_score === null" class="font-mono text-stone-500 text-[10.5px]">Excluded</span>
                <span x-show="scores.experience_score !== null" class="font-mono text-stone-900 text-[11px]" x-text="formattedScores.experience + '%'"></span>
              </div>
              <!-- Meter: Solid track if evaluated; clean dashed baseline if excluded -->
              <div x-show="scores.experience_score !== null" class="w-full bg-stone-100 rounded-full h-1 overflow-hidden">
                <div class="bg-stone-900 h-1 rounded-full transition-all duration-300" :style="'width: ' + (scores.experience_score || 0) + '%'"></div>
              </div>
              <div x-show="scores.experience_score === null" class="w-full h-1 flex items-center">
                <div class="w-full border-b border-dashed border-stone-300"></div>
              </div>
              <span class="text-[10.5px] font-mono text-stone-500 block truncate" x-text="experienceSummary"></span>
            </div>

            <!-- Column 3: Bonus Qualifications -->
            <div class="space-y-1.5">
              <div class="flex justify-between items-baseline font-medium text-stone-700">
                <span class="text-[11px]">Bonus Qualifications</span>
                <span x-show="scores.bonus_score === null" class="font-mono text-stone-500 text-[10.5px]">Excluded</span>
                <span x-show="scores.bonus_score !== null" class="font-mono text-stone-900 text-[11px]" x-text="formattedScores.bonus + '%'"></span>
              </div>
              <div x-show="scores.bonus_score !== null" class="w-full bg-stone-100 rounded-full h-1 overflow-hidden">
                <div class="bg-stone-900 h-1 rounded-full transition-all duration-300" :style="'width: ' + (scores.bonus_score || 0) + '%'"></div>
              </div>
              <div x-show="scores.bonus_score === null" class="w-full h-1 flex items-center">
                <div class="w-full border-b border-dashed border-stone-300"></div>
              </div>
              <span class="text-[10.5px] font-mono text-stone-500 block truncate" x-text="bonusSkillsSummary"></span>
            </div>

          </div>

          <!-- Unified Footnote (Spans across all 3 columns without disrupting column geometry) -->
          <div x-show="scores.experience_score === null || scores.bonus_score === null" 
               class="mt-2.5 pt-2 border-t border-[#E8E6DF]/70 text-[10.5px] text-stone-500 flex items-start gap-1.5 leading-tight">
            <svg class="w-3.5 h-3.5 text-stone-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span x-show="report && report.experience_years && report.experience_years.requirement_status === 'EXTRACTION_FAILED'">
              Experience requirement unverified in resume. Component excluded and remaining criteria renormalized to prevent score inflation.
            </span>
            <span x-show="(!report || !report.experience_years || report.experience_years.requirement_status !== 'EXTRACTION_FAILED') && scores.experience_score === null && scores.bonus_score === null">
              No tenure or bonus qualifications specified by role. Alignment evaluated on core technical requirements.
            </span>
            <span x-show="(!report || !report.experience_years || report.experience_years.requirement_status !== 'EXTRACTION_FAILED') && scores.experience_score === null && scores.bonus_score !== null">
              No tenure requirement specified by role. Alignment evaluated on demonstrated technical skills.
            </span>
            <span x-show="(!report || !report.experience_years || report.experience_years.requirement_status !== 'EXTRACTION_FAILED') && scores.experience_score !== null && scores.bonus_score === null">
              No bonus qualifications specified by role. Alignment evaluated on core requirements and verified tenure.
            </span>
          </div>
        </div>
      </div>

      <!-- Non-blocking Scoring Evidence Clamped Banner (Only if resume text exceeded 25,000 chars) -->
      <div x-show="report && report.evidence_ledger && report.evidence_ledger.scoring_evidence && report.evidence_ledger.scoring_evidence.status === 'CAPPED'"
           class="p-4 bg-amber-50/80 border border-amber-200 rounded-xl text-amber-900 text-xs flex items-start gap-3 shadow-xs">
        <svg class="w-4 h-4 text-amber-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div class="space-y-1">
          <p class="font-semibold text-amber-950">Intake Boundary Notice</p>
          <p class="text-amber-800 leading-relaxed" 
             x-text="report.evidence_ledger && report.evidence_ledger.scoring_evidence ? report.evidence_ledger.scoring_evidence.audit_note : ''">
          </p>
        </div>
      </div>

      <!-- Core Findings and Actions -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        
        <!-- Pillar 2: Requirements and Gap Analysis -->
        <div class="space-y-4">
          
          <!-- Pillar 2 Header (Styled identically to Pillar 3) -->
          <div class="pb-2">
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs font-mono text-stone-400 uppercase tracking-wider block">Pillar 2 &bull; The Gap Analysis</span>
              <span class="text-xs text-stone-400 font-mono" 
                    x-text="requirementsCounts.total + ' items (' + requirementsCounts.core + ' Core · ' + requirementsCounts.bonus + ' Bonus)'"></span>
            </div>
            <h3 class="font-serif text-2xl font-medium text-stone-900 tracking-tight">
              Requirements Ledger
            </h3>
            <p class="text-xs text-stone-500 mt-1">
              Pinpoint exactly what mandatory skills, qualifications, or experience years you are missing before you apply.
            </p>
          </div>

          <!-- Pillar 2 Filter Controls Bar -->
          <div class="stationery-card p-3 rounded-xl space-y-2.5 border border-[#E8E6DF] shadow-xs sticky top-20 z-10 bg-[#FAF9F6]/95 backdrop-blur-sm no-print print:hidden">
            <!-- Filter Tabs with Live Dynamic Counts -->
            <div class="flex items-center gap-1 border-b border-[#E8E6DF] pb-2 text-xs font-medium overflow-x-auto no-scrollbar">
              <button @click="filterTab = 'all'" 
                      :class="filterTab === 'all' ? 'bg-stone-900 text-stone-50 px-2.5 py-1 rounded shadow-xs' : 'text-stone-500 hover:text-stone-900 px-2.5 py-1'"
                      class="shrink-0 whitespace-nowrap">
                All (<span x-text="requirementsCounts.total"></span>)
              </button>
              <button @click="filterTab = 'matched'" 
                      :class="filterTab === 'matched' ? 'bg-stone-900 text-stone-50 px-2.5 py-1 rounded shadow-xs' : 'text-stone-500 hover:text-stone-900 px-2.5 py-1'"
                      class="shrink-0 whitespace-nowrap">
                Matched (<span x-text="requirementsCounts.matched"></span>)
              </button>
              <button @click="filterTab = 'weak'" 
                      :class="filterTab === 'weak' ? 'bg-stone-900 text-stone-50 px-2.5 py-1 rounded shadow-xs' : 'text-stone-500 hover:text-stone-900 px-2.5 py-1'"
                      class="shrink-0 whitespace-nowrap">
                Partial (<span x-text="requirementsCounts.weak"></span>)
              </button>
              <button @click="filterTab = 'missing'" 
                      :class="filterTab === 'missing' ? 'bg-stone-900 text-stone-50 px-2.5 py-1 rounded shadow-xs' : 'text-stone-500 hover:text-stone-900 px-2.5 py-1'"
                      class="shrink-0 whitespace-nowrap">
                Missing (<span x-text="requirementsCounts.missing"></span>)
              </button>
            </div>

            <!-- Technical Domain Filter Pills -->
            <div x-show="availableDomains.length > 1" class="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px] font-mono no-scrollbar">
              <button type="button" @click="selectedDomain = 'all'"
                      class="px-2 py-0.5 rounded transition-all shrink-0"
                      :class="selectedDomain === 'all' ? 'bg-stone-800 text-stone-100' : 'bg-stone-100 text-stone-600 hover:bg-stone-200'">
                All Domains
              </button>
              <template x-for="d in availableDomains" :key="d">
                <button type="button" @click="selectedDomain = d"
                        class="px-2 py-0.5 rounded transition-all shrink-0"
                        :class="selectedDomain === d ? 'bg-stone-800 text-stone-100' : 'bg-stone-100 text-stone-600 hover:bg-stone-200'"
                        x-text="d">
                </button>
              </template>
            </div>
          </div>

          <!-- Requirements Stream (Cards matching Pillar 3 styling) -->
          <div class="space-y-4">
            <template x-for="(item, idx) in filteredRequirements" :key="idx">
              <div class="stationery-card p-5 sm:p-6 rounded-xl space-y-3.5 border border-[#E8E6DF] shadow-xs">
                
                <!-- Category, Domain & Status Badges -->
                <div class="flex justify-between items-start gap-2">
                  <div class="space-y-1">
                    <div class="flex flex-wrap items-center gap-1.5">
                      <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono tracking-tight"
                            :class="item.category === 'core' ? 'bg-stone-200/80 text-stone-800 font-medium' : 'bg-stone-100 text-stone-600 border border-stone-200'"
                            x-text="item.categoryLabel">
                      </span>
                      <span x-show="item.domain" class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-stone-100 text-stone-500 border border-stone-200/60"
                            x-text="item.domain">
                      </span>
                    </div>
                    <h4 class="font-semibold text-stone-900 text-sm tracking-tight leading-snug" x-text="item.requirement"></h4>
                  </div>
                  
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium shrink-0"
                        :class="{
                          'text-emerald-900 bg-emerald-50 border border-emerald-200': item.status === 'MATCHED',
                          'text-amber-900 bg-amber-50 border border-amber-200': item.status === 'WEAK',
                          'text-stone-600 bg-stone-100 border border-stone-200': item.status === 'MISSING'
                        }"
                        x-text="item.status === 'MATCHED' ? 'Matched' : item.status === 'WEAK' ? 'Partial' : 'Missing'">
                  </span>
                </div>

                <!-- Resume Quote (Verbatim Evidence) -->
                <div x-show="item.evidence_quote" class="border-l-2 border-stone-400 pl-3.5 py-1.5 bg-[#FAF9F6] text-xs text-stone-700 rounded-r border-t border-r border-b border-[#E8E6DF]/50">
                  <span class="text-[10px] font-mono text-stone-400 uppercase tracking-wider block mb-0.5">Resume Evidence:</span>
                  <p class="italic font-serif leading-relaxed" x-text="'“' + item.evidence_quote + '”'"></p>
                </div>

                <!-- Gap Reason -->
                <div x-show="item.gap_reason" class="text-stone-600 text-xs flex items-start gap-2 bg-stone-50/50 p-2.5 rounded-lg border border-[#E8E6DF]/60">
                  <span class="text-stone-400 font-mono text-[11px] shrink-0">&bull;</span>
                  <span class="leading-relaxed" x-text="item.gap_reason"></span>
                </div>

                <!-- Interview Defense Intel (Styled matching Pillar 3's Interview Note) -->
                <div x-show="item.defense_tip" class="p-3.5 bg-stone-50 border border-[#E8E6DF] rounded-lg text-xs space-y-1">
                  <span class="font-medium text-stone-700 block font-mono text-[11px] uppercase tracking-wider">Defense Intel:</span>
                  <p class="text-stone-600 text-xs leading-relaxed" x-text="item.defense_tip"></p>
                </div>

              </div>
            </template>

            <!-- Empty State Component -->
            <div x-show="filteredRequirements.length === 0" class="py-12 px-6 text-center rounded-xl border border-dashed border-[#E8E6DF] bg-white">
              <p class="text-xs font-mono uppercase tracking-wider text-stone-400">Ledger Empty for this Filter</p>
              <p class="text-xs text-stone-500 mt-1" x-text="filterTab === 'missing' ? 'Zero missing requirements found in this category. All audited criteria have matching or partial evidence.' : filterTab === 'weak' ? 'No partial requirements found. All criteria are either fully matched or missing.' : 'No requirements match the active filter.'"></p>
            </div>
          </div>

        </div>

        <!-- Pillar 3: Actionable Experience Rewrites -->
        <div class="space-y-4">
          
          <!-- Pillar 3 Header (Matching Pillar 2 styling) -->
          <div class="pb-2">
            <div class="flex items-center justify-between mb-1">
              <div class="flex items-center gap-2">
                <span class="text-xs font-mono text-stone-400 uppercase tracking-wider block">Pillar 3 &bull; The Calibrated Action</span>
                <span x-show="report && report.evidence_ledger && ((report.evidence_ledger.rewrite_ledger && report.evidence_ledger.rewrite_ledger.status === 'CAPPED') || (!report.evidence_ledger.rewrite_ledger && report.evidence_ledger.status === 'CAPPED'))"
                      class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-medium">
                  Anchors Capped
                </span>
              </div>
              <span class="text-xs text-stone-400 font-mono" x-show="report.actionable_rewrites"
                    x-text="(report.actionable_rewrites ? report.actionable_rewrites.length : 0) + ' Actionable Bullets'"></span>
            </div>
            <h3 class="font-serif text-2xl font-medium text-stone-900 tracking-tight">
              Role-Specific Achievement Bullets
            </h3>
            <p class="text-xs text-stone-500 mt-1">
              Transform passive experience into role-specific achievement bullets with real numbers and interview defense notes.
            </p>
          </div>

          <!-- Rewrite Ledger Capped Notice (Specific to Pillar 3 Actionable Bullets) -->
          <div x-show="report && report.evidence_ledger && ((report.evidence_ledger.rewrite_ledger && report.evidence_ledger.rewrite_ledger.status === 'CAPPED') || (!report.evidence_ledger.rewrite_ledger && report.evidence_ledger.status === 'CAPPED'))"
               class="p-3 bg-amber-50/80 border border-amber-200 rounded-lg text-amber-900 text-xs flex items-start gap-2 shadow-xs">
            <svg class="w-4 h-4 text-amber-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="leading-relaxed text-amber-800"
               x-text="'Candidate bullets capped for rewrite anchoring (' + (report.evidence_ledger && report.evidence_ledger.rewrite_ledger ? report.evidence_ledger.rewrite_ledger.included_bullets_count : (report.evidence_ledger ? report.evidence_ledger.evaluated_bullets_count : '')) + ' of ' + (report.evidence_ledger ? report.evidence_ledger.extracted_bullets_count : '') + ' included). Full resume text remained available for skill alignment scoring.'">
            </p>
          </div>

          <!-- Rewrite Ledger Unavailable Notice -->
          <div x-show="report && report.evidence_ledger && ((report.evidence_ledger.rewrite_ledger && report.evidence_ledger.rewrite_ledger.status === 'UNAVAILABLE') || (!report.evidence_ledger.rewrite_ledger && report.evidence_ledger.status === 'UNAVAILABLE'))"
               class="p-3 bg-stone-100 border border-stone-300 rounded-lg text-stone-800 text-xs flex items-start gap-2 shadow-xs">
            <svg class="w-4 h-4 text-stone-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="leading-relaxed text-stone-600">
              No structured accomplishment bullets were detected in this resume. Rewrites could not be anchored to existing project bullets, but skill alignment was evaluated against full resume text.
            </p>
          </div>

          <!-- Rewrites Stream -->
          <div class="space-y-4">
            <template x-for="(rw, index) in report.actionable_rewrites" :key="index">
              <div class="stationery-card p-6 rounded-xl space-y-4 border border-[#E8E6DF] shadow-xs" 
                   x-data="rewriteCard(rw)" 
                   @copy="handleCopyEvent($event)">
                
                <div class="flex justify-between items-center">
                  <span class="text-xs font-mono text-stone-500 uppercase tracking-wider" x-text="'Target Skill: ' + rw.target_skill"></span>
                  <button type="button" @click="viewFullRedline = !viewFullRedline"
                          class="text-xs text-stone-500 hover:text-stone-900 underline underline-offset-2 no-print print:hidden">
                    <span x-text="viewFullRedline ? 'Clean version' : 'View full diff'"></span>
                  </button>
                </div>

                <!-- Original Bullet -->
                <div class="text-xs space-y-1">
                  <span class="text-xs font-mono text-stone-400 block">Original bullet</span>
                  <p class="line-through text-stone-400 italic bg-[#FAF9F6] p-3 rounded-lg border border-[#E8E6DF]" x-text="rw.original_bullet"></p>
                </div>

                <!-- Suggested Rewrite with Diffs -->
                <div class="text-xs space-y-1">
                  <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold block" :class="(hasUnverifiedMetrics && !isVerified) ? 'text-amber-900' : 'text-stone-800'"
                          x-text="(hasUnverifiedMetrics && !isVerified) ? 'Suggested achievement (attestation required)' : (hasUnverifiedMetrics && isVerified) ? 'Candidate-attested achievement' : 'Supported achievement'"></span>
                    <span x-show="hasUnverifiedMetrics && !isVerified" class="text-[10px] font-mono text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-200 no-print print:hidden">Candidate metric required</span>
                    <span x-show="hasUnverifiedMetrics && isVerified" class="text-[10px] font-mono text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-200 no-print print:hidden">Attested by candidate</span>
                  </div>
                  <div class="font-mono text-xs text-stone-900 leading-relaxed bg-[#FAF9F6] p-3.5 rounded-lg border border-[#E8E6DF]" 
                       x-html="viewFullRedline ? renderFullRedline(rw.original_bullet, currentBullet) : renderDiff(rw.original_bullet, currentBullet)">
                  </div>
                </div>

                <!-- Metric Input Guard -->
                <div x-show="hasUnverifiedMetrics" class="p-4 bg-amber-50/60 border border-amber-200/80 rounded-lg space-y-2.5 no-print print:hidden">
                  <div class="flex items-center justify-between">
                    <label class="block text-xs font-semibold text-amber-950">
                      Enter your verified metric:
                    </label>
                    <span class="text-[10px] font-mono text-amber-800 bg-amber-100 px-2 py-0.5 rounded">Required for copy</span>
                  </div>
                  <input type="text" x-model="metricInput" @input="updateMetric" :placeholder="placeholderHint"
                         class="w-full bg-white text-stone-900 text-xs px-3 py-2 rounded-md border border-amber-300 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-500/20 font-mono transition-colors">
                  <div class="flex items-center gap-2 pt-1">
                    <input type="checkbox" :id="'confirm-' + index" x-model="confirmedMetric" @change="toggleConfirm" :disabled="placeholderPresent || !metricInput.trim()"
                           class="rounded border-amber-300 text-blue-600 focus:ring-blue-600 h-3.5 w-3.5">
                    <label :for="'confirm-' + index" class="text-xs text-amber-950 font-medium select-none cursor-pointer">
                      I confirm that this metric accurately reflects my work experience
                    </label>
                  </div>
                  <p x-show="copyBlockedReason" class="text-[11px] text-red-700 font-medium" x-text="copyBlockedReason"></p>
                  <p class="text-[11px] text-amber-800" x-show="!copyBlockedReason">
                    Replace placeholder with your authentic metric and confirm above to unlock clipboard copy.
                  </p>
                </div>

                <!-- Interview Strategy Note -->
                <div x-show="rw.interview_defense_tip" class="p-3.5 bg-stone-50 border border-[#E8E6DF] rounded-lg text-xs space-y-1">
                  <span class="font-medium text-stone-700 block font-mono text-[11px] uppercase tracking-wider">Interview Note:</span>
                  <p class="text-stone-600 text-xs leading-relaxed" x-text="rw.interview_defense_tip"></p>
                </div>

                <!-- Copy Action -->
                <button type="button" @click="copyToClipboard(currentBullet)" :disabled="hasUnverifiedMetrics && !isVerified"
                        class="w-full py-2.5 px-4 text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-2 shadow-xs no-print print:hidden"
                        :class="(hasUnverifiedMetrics && !isVerified) ? 'bg-stone-100 text-stone-400 border border-[#E8E6DF] cursor-not-allowed' : copied ? 'bg-emerald-700 text-white' : 'btn-executive'">
                  <span x-text="copied ? 'Copied to clipboard' : (hasUnverifiedMetrics && !isVerified) ? 'Confirm metric above to unlock copy' : 'Copy customized bullet point'"></span>
                </button>

              </div>
            </template>
          </div>

        </div>

      </div>

      <!-- Print-Only Document Footer -->
      <div class="hidden print:block pt-4 mt-6 border-t border-stone-300 text-center text-[9px] font-mono text-stone-500 print-footer">
        <p>Calibrate AI &bull; Verbatim Resume Citation Audit &bull; Documented for Technical Interview Preparation</p>
      </div>

    </div>

    <!-- How Your Data Is Processed — Privacy Disclosure Dialog -->
    <div x-show="showPrivacyNotice"
         x-transition:enter="transition ease-out duration-200"
         x-transition:enter-start="opacity-0"
         x-transition:enter-end="opacity-100"
         x-transition:leave="transition ease-in duration-150"
         x-transition:leave-start="opacity-100"
         x-transition:leave-end="opacity-0"
         class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto bg-stone-900/40 backdrop-blur-xs no-print print:hidden"
         @keydown.escape.window="showPrivacyNotice = false"
         role="dialog"
         aria-modal="true"
         aria-labelledby="privacy-dialog-title"
         aria-describedby="privacy-dialog-desc"
         style="display: none;">
      
      <!-- Backdrop Click to Close -->
      <div class="fixed inset-0" @click="showPrivacyNotice = false" aria-hidden="true"></div>

      <!-- Dialog Card -->
      <div class="relative w-full max-w-lg bg-[#FAF9F6] border border-[#E8E6DF] rounded-2xl shadow-xl p-6 sm:p-7 space-y-5 text-left z-10"
           @click.stop>
        
        <!-- Header -->
        <div class="flex items-start justify-between gap-4 border-b border-[#E8E6DF] pb-4">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-full bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-700 shrink-0">
                <svg class="w-3.5 h-3.5 text-stone-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" stroke-width="1.8"/>
                  <path stroke-linecap="round" stroke-width="1.8" d="M12 16v-4m0-4h.01"/>
                </svg>
              </span>
              <h2 id="privacy-dialog-title" class="font-serif text-lg font-medium text-stone-900 tracking-tight">
                How Your Data Is Processed
              </h2>
            </div>
            <p id="privacy-dialog-desc" class="text-xs text-stone-500">
              Transparency on how documents are analyzed, scrubbed, and handled.
            </p>
          </div>
          <button type="button"
                  @click="showPrivacyNotice = false"
                  class="text-stone-400 hover:text-stone-700 p-1.5 rounded-lg hover:bg-stone-100 transition-colors focus:outline-none focus:ring-2 focus:ring-stone-400 cursor-pointer"
                  aria-label="Close dialog">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Content Sections -->
        <div class="space-y-4 text-xs text-stone-600 leading-relaxed font-sans">
          
          <div class="space-y-1.5">
            <h3 class="font-medium text-stone-900 text-xs flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-stone-400"></span>
              Third-Party AI Analysis
            </h3>
            <p class="text-stone-600">
              To calculate role alignment, requirement matches, and bullet rewrites, extracted resume and job description text is processed by third-party artificial intelligence services.
            </p>
          </div>

          <div class="space-y-1.5">
            <h3 class="font-medium text-stone-900 text-xs flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
              Contact Detail Redaction
            </h3>
            <p class="text-stone-600">
              Direct contact identifiers (such as detected email addresses, phone numbers, and profile links) are automatically redacted before data is transmitted for AI analysis. Professional history, skills, and qualifications remain intact to enable accurate evaluation.
            </p>
          </div>

          <div class="space-y-1.5">
            <h3 class="font-medium text-stone-900 text-xs flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-stone-400"></span>
              Retention &amp; Storage
            </h3>
            <p class="text-stone-600">
              Uploaded documents, processing data, and generated assessments are handled and stored according to the application's configured environment and applicable data-handling procedures.
            </p>
          </div>

        </div>

        <!-- Footer / Dismiss -->
        <div class="pt-4 border-t border-[#E8E6DF] flex items-center justify-end">
          <button type="button"
                  @click="showPrivacyNotice = false"
                  class="btn-calibrate-primary text-xs font-medium py-2 px-4 rounded-lg cursor-pointer">
            Understood
          </button>
        </div>

      </div>
    </div>

    <!-- Document Orientation Confirmation Dialog -->
    <div x-show="showSwapConfirmationModal"
         x-transition:enter="transition ease-out duration-200"
         x-transition:enter-start="opacity-0"
         x-transition:enter-end="opacity-100"
         x-transition:leave="transition ease-in duration-150"
         x-transition:leave-start="opacity-100"
         x-transition:leave-end="opacity-0"
         class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto bg-stone-900/40 backdrop-blur-xs no-print print:hidden"
         @keydown.escape.window="showSwapConfirmationModal = false"
         role="dialog"
         aria-modal="true"
         aria-labelledby="orientation-dialog-title"
         aria-describedby="orientation-dialog-desc"
         style="display: none;">
      
      <!-- Backdrop Click to Close -->
      <div class="fixed inset-0" @click="showSwapConfirmationModal = false" aria-hidden="true"></div>

      <!-- Dialog Card -->
      <div class="relative w-full max-w-lg bg-[#FAF9F6] border border-[#E8E6DF] rounded-2xl shadow-xl p-6 sm:p-7 space-y-5 text-left z-10"
           @click.stop>
        
        <!-- Header -->
        <div class="flex items-start justify-between gap-4 border-b border-[#E8E6DF] pb-4">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-700 shrink-0">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
                </svg>
              </span>
              <h2 id="orientation-dialog-title" class="font-serif text-lg font-medium text-stone-900 tracking-tight">
                Review Document Orientation
              </h2>
            </div>
            <p id="orientation-dialog-desc" class="text-xs text-stone-500">
              Your inputs appear to be placed in reverse order.
            </p>
          </div>
          <button type="button"
                  @click="showSwapConfirmationModal = false"
                  class="text-stone-400 hover:text-stone-700 p-1.5 rounded-lg hover:bg-stone-100 transition-colors focus:outline-none focus:ring-2 focus:ring-stone-400 cursor-pointer"
                  aria-label="Close dialog">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Body / Comparison Card -->
        <div class="space-y-3.5 text-xs text-stone-700 leading-relaxed">
          <div class="bg-stone-50/70 border border-[#E8E6DF] p-3.5 rounded-xl space-y-2">
            <div class="flex items-start gap-2">
              <span class="px-1.5 py-0.5 rounded bg-amber-100/70 text-amber-900 font-mono text-[10px] uppercase font-semibold shrink-0">Left Box</span>
              <span class="text-stone-600">The <strong>Resume</strong> field contains employer requisition phrasing (e.g., responsibilities, requirements, qualifications).</span>
            </div>
            <div class="flex items-start gap-2 pt-2 border-t border-stone-200/60">
              <span class="px-1.5 py-0.5 rounded bg-emerald-100/70 text-emerald-900 font-mono text-[10px] uppercase font-semibold shrink-0">Right Box</span>
              <span class="text-stone-600">The <strong>Job Description</strong> field contains candidate work chronology and contact credentials.</span>
            </div>
          </div>
          <p class="text-[11.5px] text-stone-500">
            For accurate qualification alignment and Google XYZ achievements, the Resume field should contain your candidate background and the Job Description field should contain the target job posting.
          </p>
        </div>

        <!-- Actions -->
        <div class="pt-4 border-t border-[#E8E6DF] flex flex-wrap items-center justify-between gap-3">
          <button type="button"
                  @click="proceedWithoutSwap()"
                  class="text-xs text-stone-500 hover:text-stone-900 underline underline-offset-2 py-2 cursor-pointer transition-colors">
            Calibrate As-Is
          </button>

          <div class="flex items-center gap-2">
            <button type="button"
                    @click="showSwapConfirmationModal = false"
                    class="text-xs font-medium py-2 px-3.5 rounded-lg border border-stone-200 text-stone-700 hover:bg-stone-100 transition-colors cursor-pointer">
              Review Inputs
            </button>
            <button type="button"
                    @click="confirmSwapAndSubmit()"
                    class="btn-calibrate-primary text-xs font-medium py-2 px-4 rounded-lg flex items-center gap-1.5 cursor-pointer shadow-xs">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
              </svg>
              <span>Swap &amp; Calibrate</span>
            </button>
          </div>
        </div>

      </div>
    </div>

  </main>

  <!-- Footer -->
  <footer class="footer-editorial py-10 px-4 sm:px-6 text-center text-xs text-stone-400 space-y-2 relative z-10 no-print print:hidden">
    <div class="flex items-center justify-center mb-1 select-none pointer-events-none" aria-hidden="true">
      <img src="assets/brand/calibrate-wordmark-light.svg" alt="Calibrate Logo" height="24" class="h-6 w-auto opacity-70 mx-auto select-none pointer-events-none" draggable="false">
    </div>
    <p class="text-[11px] text-stone-500 font-medium">Calibrate calculates deterministic requirement and qualification coverage for Engineering &amp; Tech roles. It does not simulate proprietary ATS ranking algorithms or guarantee interview selection.</p>
    <p class="text-[10.5px] text-stone-400">Privacy-conscious architecture: Uploaded documents, processing data, and generated assessments are handled according to configured environment procedures.</p>
  </footer>

  <!-- Scripts -->
  <script src="assets/js/diff-renderer.js?v=<?= file_exists(__DIR__ . '/assets/js/diff-renderer.js') ? filemtime(__DIR__ . '/assets/js/diff-renderer.js') : '1' ?>"></script>
  <script src="assets/js/app.js?v=<?= file_exists(__DIR__ . '/assets/js/app.js') ? filemtime(__DIR__ . '/assets/js/app.js') : '1' ?>"></script>
  <script src="assets/js/grid-effect.js?v=<?= file_exists(__DIR__ . '/assets/js/grid-effect.js') ? filemtime(__DIR__ . '/assets/js/grid-effect.js') : '1' ?>"></script>
</body>
</html>
