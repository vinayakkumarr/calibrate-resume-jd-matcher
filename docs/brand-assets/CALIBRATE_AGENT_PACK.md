# CALIBRATE — AGENT INTEGRATION PACK & ASSET BUNDLE
> **Target Audience:** Coding Agents (LLMs, Cursor, Claude, Copilot, Windsurf) & Web Developers  
> **Framework Constraint:** **NO React, NO Next.js**. Plain HTML5, Modern CSS, and Vanilla JavaScript only.  
> **Design Philosophy:** Strict Flat 2D Minimalism. Pure Black (`#000000`), Pure White (`#FFFFFF`), Champagne Gold (`#D4B483`). Zero 3D, zero gradients, zero shadows, zero blue undertones.

---

## 1. Directive for Coding Agent (Copy-Paste System Prompt)

```text
You are integrating the Calibrate brand identity into this codebase.
Calibrate is an executive career workbench and alignment engine.
CRITICAL DESIGN CONSTRAINTS:
1. Do NOT use React or Next.js. Use plain HTML5, CSS3, and vanilla JavaScript only.
2. The design is strictly flat, 2D, and minimal. Do NOT add gradients, 3D extrusions, drop shadows, bevels, or watch dial rings.
3. Strict palette:
   - Dark Theme Canvas: Pure Solid Black #000000
   - Light Theme Canvas: Pure Solid White #FFFFFF
   - Accent (Dark): Champagne Gold #D4B483
   - Accent (Light): Milled Brass #9A7432
   - Borders / Lines: Neutral Gray #262626 (dark) / #E5E5E5 (light)
   - Zero blue/slate undertones.
4. Follow the HTML snippets and SVG assets defined in this document.
```

---

## 2. Core Color Palette & Design Tokens

Use these exact tokens across all styles. No blue or slate tints.

```css
/* Dark Theme (Default) */
--cal-bg-dark:        #000000;  /* Pure Solid Black */
--cal-card-dark:      #121212;  /* Elevated Neutral Surface */
--cal-border-dark:    #262626;  /* 1px Neutral Framing Hairline */
--cal-text-dark:      #FFFFFF;  /* Primary Pure White Typography */
--cal-muted-dark:     #A3A3A3;  /* Secondary Neutral Gray Text */
--cal-gold:           #D4B483;  /* Champagne Gold (Signature Accent) */

/* Light Theme */
--cal-bg-light:       #FFFFFF;  /* Pure Solid White */
--cal-card-light:     #FFFFFF;  /* Elevated Neutral Card */
--cal-border-light:   #E5E5E5;  /* 1px Light Gray Border */
--cal-text-light:     #000000;  /* Primary Pure Black Typography */
--cal-muted-light:    #737373;  /* Secondary Light Neutral Text */
--cal-gold-light:     #9A7432;  /* Milled Brass (Light Accent) */
```

---

## 3. Recommended Project File Organization

Place the SVG asset files into your static directory (e.g. `/assets/brand/`, `/static/`, or `/public/`):

```text
your-project/
├── index.html
├── assets/
│   ├── css/
│   │   └── calibrate.css                  <-- Drop-in stylesheet (Section 5)
│   ├── js/
│   │   └── theme.js                       <-- Optional 10-line toggle (Section 6)
│   └── brand/
│       ├── calibrate-wordmark-dark.svg     <-- Main Navbar Logo (Dark)
│       ├── calibrate-wordmark-light.svg    <-- Main Navbar Logo (Light)
│       ├── calibrate-symbol-mark-dark.svg  <-- Standalone 'C' Monogram (Dark, High Contrast)
│       ├── calibrate-symbol-mark-light.svg <-- Standalone 'C' Monogram (Light)
│       ├── calibrate-app-icon.svg          <-- Web App Icon (Dark, High Contrast)
│       ├── calibrate-favicon-32.svg        <-- Browser Tab Favicon
│       ├── calibrate-hero-banner.svg       <-- OpenGraph / Social Card (Dark)
│       └── calibrate-hero-banner-light.svg <-- OpenGraph / Social Card (Light)
```

---

## 4. Ready-to-Use HTML Snippets (No React / No Next.js)

### A. `<head>` Favicon & Meta Tags
Paste this directly inside the `<head>` of your HTML document:

```html
<!-- Browser Favicon (SVG scalable) -->
<link rel="icon" type="image/svg+xml" href="/assets/brand/calibrate-favicon-32.svg">
<link rel="alternate icon" href="/assets/brand/calibrate-favicon-32.svg">

<!-- Apple Touch & Mobile PWA Icon -->
<link rel="apple-touch-icon" href="/assets/brand/calibrate-app-icon-512.svg">

<!-- OpenGraph & Twitter Social Preview -->
<meta property="og:title" content="Calibrate — Precision alignment for every job description">
<meta property="og:description" content="Executive career editorial, mathematical gap analysis, and interview defense.">
<meta property="og:image" content="/assets/brand/calibrate-hero-banner.svg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="/assets/brand/calibrate-hero-banner.svg">
```

---

### B. Navbar Logo: Automatic OS Dark/Light Mode (Zero JavaScript)
Use HTML5 `<picture>` so the browser automatically displays the dark or light logo based on the user's system preferences without any JavaScript:

```html
<header class="cal-navbar">
  <div class="cal-nav-container">
    <a href="/" class="cal-brand-link" aria-label="Calibrate Home">
      <picture>
        <!-- Dark Theme Wordmark (Champagne Gold 'C' + White text) -->
        <source srcset="/assets/brand/calibrate-wordmark-dark.svg" media="(prefers-color-scheme: dark)">
        <!-- Light Theme Wordmark (Milled Brass 'C' + Black text) -->
        <img src="/assets/brand/calibrate-wordmark-light.svg" alt="Calibrate Logo" height="32" class="cal-logo">
      </picture>
    </a>
  </div>
</header>
```

---

### C. Navbar Logo: Manual Theme Toggle (Class-based: `.dark`)
If your website toggles dark mode via a CSS class on `<html class="dark">` or `<body class="dark">`:

```html
<header class="cal-navbar">
  <div class="cal-nav-container">
    <a href="/" class="cal-brand-link" aria-label="Calibrate Home">
      <!-- Dark logo shown only when .dark is active -->
      <img src="/assets/brand/calibrate-wordmark-dark.svg" alt="Calibrate Logo" height="32" class="cal-logo cal-logo-dark">
      <!-- Light logo shown when .dark is absent -->
      <img src="/assets/brand/calibrate-wordmark-light.svg" alt="Calibrate Logo" height="32" class="cal-logo cal-logo-light">
    </a>

    <!-- Theme Toggle Button -->
    <button id="themeToggleBtn" class="cal-theme-btn" aria-label="Toggle Theme">
      <span class="theme-icon">◐</span>
    </button>
  </div>
</header>
```

---

### D. Standalone 'C' Monogram (Mobile Header, Avatar, or Icon Button)
For mobile headers where space is limited:

```html
<a href="/" class="cal-symbol-link" aria-label="Calibrate Home">
  <picture>
    <source srcset="/assets/brand/calibrate-symbol-mark-dark.svg" media="(prefers-color-scheme: dark)">
    <img src="/assets/brand/calibrate-symbol-mark-light.svg" alt="Calibrate 'C'" width="36" height="36">
  </picture>
</a>
```

---

### E. Footer Lockup
```html
<footer class="cal-footer">
  <div class="cal-footer-container">
    <img src="/assets/brand/calibrate-wordmark-dark.svg" alt="Calibrate" height="24">
    <p class="cal-footer-meta">PRECISION ALIGNMENT FOR EVERY JOB DESCRIPTION</p>
    <p class="cal-footer-copy">&copy; 2026 Calibrate. All rights reserved.</p>
  </div>
</footer>
```

---

## 5. Universal Vanilla Stylesheet (`calibrate.css`)

Save this file as `calibrate.css` and link it via `<link rel="stylesheet" href="/assets/css/calibrate.css">`:

```css
/* ==========================================================================
   CALIBRATE BRAND STYLESHEET (NO FRAMEWORKS / PURE CSS)
   ========================================================================== */

:root {
  /* Neutral Color Palette (Zero Blue Tint) */
  --cal-bg: #FFFFFF;
  --cal-card: #FFFFFF;
  --cal-border: #E5E5E5;
  --cal-text: #000000;
  --cal-muted: #737373;
  --cal-accent: #9A7432; /* Milled Brass on light */
}

/* System Dark Mode */
@media (prefers-color-scheme: dark) {
  :root {
    --cal-bg: #000000;
    --cal-card: #121212;
    --cal-border: #262626;
    --cal-text: #FFFFFF;
    --cal-muted: #A3A3A3;
    --cal-accent: #D4B483; /* Champagne Gold on dark */
  }
}

/* Manual Dark Class Override: <html class="dark"> or <body class="dark"> */
html.dark, body.dark {
  --cal-bg: #000000;
  --cal-card: #121212;
  --cal-border: #262626;
  --cal-text: #FFFFFF;
  --cal-muted: #A3A3A3;
  --cal-accent: #D4B483;
}

/* Base Page Styling */
body {
  background-color: var(--cal-bg);
  color: var(--cal-text);
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  transition: background-color 0.2s ease, color 0.2s ease;
}

/* Navbar Component */
.cal-navbar {
  background-color: var(--cal-bg);
  border-bottom: 1px solid var(--cal-border);
  padding: 16px 24px;
}

.cal-nav-container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.cal-brand-link {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
}

.cal-logo {
  height: 32px;
  width: auto;
  display: block;
}

/* Class-based Dark/Light Image Switching */
.cal-logo-dark { display: none; }
.cal-logo-light { display: block; }

html.dark .cal-logo-dark, body.dark .cal-logo-dark { display: block; }
html.dark .cal-logo-light, body.dark .cal-logo-light { display: none; }

/* Theme Switcher Button */
.cal-theme-btn {
  background: transparent;
  border: 1px solid var(--cal-border);
  border-radius: 8px;
  color: var(--cal-text);
  padding: 6px 12px;
  cursor: pointer;
  font-size: 14px;
  transition: border-color 0.15s ease;
}

.cal-theme-btn:hover {
  border-color: var(--cal-accent);
}

/* Footer Component */
.cal-footer {
  background-color: var(--cal-bg);
  border-top: 1px solid var(--cal-border);
  padding: 40px 24px;
  text-align: center;
}

.cal-footer-meta {
  font-family: 'JetBrains Mono', monospace, monospace;
  font-size: 11px;
  color: var(--cal-accent);
  letter-spacing: 0.18em;
  margin: 16px 0 8px 0;
}

.cal-footer-copy {
  font-size: 12px;
  color: var(--cal-muted);
  margin: 0;
}
```

---

## 6. Vanilla JavaScript Theme Toggle (`theme.js`)

Save this file as `theme.js` to enable one-click theme toggling with `localStorage` persistence:

```javascript
// Calibrate Minimal Vanilla Theme Switcher (Zero Dependencies)
(function() {
  const savedTheme = localStorage.getItem('cal-theme');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }

  document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('themeToggleBtn');
    if (!btn) return;

    btn.addEventListener('click', function() {
      const isDark = document.documentElement.classList.toggle('dark');
      localStorage.setItem('cal-theme', isDark ? 'dark' : 'light');
    });
  });
})();
```

---

## 7. Raw SVG Code for Direct Inlining

If your agent needs to embed SVGs directly in HTML (for instance, to avoid extra HTTP requests or for inline styling), here is the exact vector code:

### A. Bugenvil 'C' Monogram Dark (120×120) — [`calibrate-symbol-mark.svg`](/assets/brand/calibrate-symbol-mark-dark.svg)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">
  <!-- Plain Black Squircle Background -->
  <rect width="120" height="120" rx="28" fill="#000000"/>
  <rect width="118" height="118" x="1" y="1" rx="27" fill="none" stroke="#262626" stroke-width="1"/>
  
  <!-- Plain Flat Datum Crosshairs -->
  <g stroke="#262626" stroke-width="1.5">
    <line x1="14" y1="20" x2="22" y2="20"/>
    <line x1="20" y1="14" x2="20" y2="22"/>
    <line x1="98" y1="100" x2="106" y2="100"/>
    <line x1="100" y1="98" x2="100" y2="106"/>
  </g>

  <!-- Plain Flat Bugenvil 'C' Monogram -->
  <path d="M91.47 66.57H90.73C90.73 66.57 86.27 77.81 75.59 81.99V43.9C76.05 43.9 76.7 43.9 77.26 43.9C92.12 44 94.82 29.13 93.98 28.11C93.98 28.11 91.75 33.13 84.88 33.13C75.86 33.13 73.08 23 73.08 23C73.08 23 63.04 38.89 41.77 47.53C44.93 34.33 55.61 27.65 60.35 27.65C60.35 27.65 60.16 26.34 55.52 26.34C47.44 26.34 38.61 31.18 32.94 39.82C31.18 37.96 29.23 37.59 27.83 37.59C26.63 37.59 25.88 37.86 25.88 37.86C30.53 40.56 28.58 49.38 28.58 49.38C27.55 53.1 27.09 56.91 27.09 61.28C27.09 73.45 36.1 95 59.79 95C87.57 95 91.47 66.57 91.47 66.57ZM73.91 82.46C72.06 83.2 69.83 83.48 67.69 83.48C61 83.48 55.15 81.53 50.78 78.18C53.47 76.61 60.54 72.15 63.32 65.27C63.32 65.27 64.16 62.76 64.16 59.23V37.86C65.18 39.17 68.34 42.51 73.91 43.53ZM40.93 55.24C40.93 53.1 41.12 51.06 41.4 49.2C44.93 48.18 49.29 46.04 53.01 43.9V72.33C53.01 75.12 51.15 76.61 49.94 77.44C44.28 72.42 40.93 64.81 40.93 55.24Z" fill="#D4B483"/>
</svg>
```

### B. Bugenvil 'C' Monogram Light (120×120) — [`calibrate-symbol-mark-light.svg`](/assets/brand/calibrate-symbol-mark-light.svg)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">
  <rect width="120" height="120" rx="28" fill="#FFFFFF"/>
  <rect width="118" height="118" x="1" y="1" rx="27" fill="none" stroke="#E5E5E5" stroke-width="1"/>
  
  <g stroke="#E5E5E5" stroke-width="1.5">
    <line x1="14" y1="20" x2="22" y2="20"/>
    <line x1="20" y1="14" x2="20" y2="22"/>
    <line x1="98" y1="100" x2="106" y2="100"/>
    <line x1="100" y1="98" x2="100" y2="106"/>
  </g>

  <path d="M91.47 66.57H90.73C90.73 66.57 86.27 77.81 75.59 81.99V43.9C76.05 43.9 76.7 43.9 77.26 43.9C92.12 44 94.82 29.13 93.98 28.11C93.98 28.11 91.75 33.13 84.88 33.13C75.86 33.13 73.08 23 73.08 23C73.08 23 63.04 38.89 41.77 47.53C44.93 34.33 55.61 27.65 60.35 27.65C60.35 27.65 60.16 26.34 55.52 26.34C47.44 26.34 38.61 31.18 32.94 39.82C31.18 37.96 29.23 37.59 27.83 37.59C26.63 37.59 25.88 37.86 25.88 37.86C30.53 40.56 28.58 49.38 28.58 49.38C27.55 53.1 27.09 56.91 27.09 61.28C27.09 73.45 36.1 95 59.79 95C87.57 95 91.47 66.57 91.47 66.57ZM73.91 82.46C72.06 83.2 69.83 83.48 67.69 83.48C61 83.48 55.15 81.53 50.78 78.18C53.47 76.61 60.54 72.15 63.32 65.27C63.32 65.27 64.16 62.76 64.16 59.23V37.86C65.18 39.17 68.34 42.51 73.91 43.53ZM40.93 55.24C40.93 53.1 41.12 51.06 41.4 49.2C44.93 48.18 49.29 46.04 53.01 43.9V72.33C53.01 75.12 51.15 76.61 49.94 77.44C44.28 72.42 40.93 64.81 40.93 55.24Z" fill="#9A7432"/>
</svg>
```

### C. App Icon Squircle Dark (512×512) — [`calibrate-app-icon-512.svg`](/assets/brand/calibrate-app-icon-512.svg)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <!-- Plain Black Squircle Background -->
  <rect width="512" height="512" rx="115" fill="#000000"/>
  <rect width="510" height="510" x="1" y="1" rx="114" fill="none" stroke="#262626" stroke-width="2"/>

  <!-- Plain Flat Bugenvil 'C' Glyph -->
  <path d="M382.76 282.5H379.77C379.77 282.5 361.81 327.77 318.78 344.61V191.19C320.65 191.19 323.27 191.19 325.51 191.19C385.38 191.57 396.23 131.7 392.87 127.58C392.87 127.58 383.89 147.79 356.2 147.79C319.9 147.79 308.67 107 308.67 107C308.67 107 268.26 170.99 182.57 205.79C195.29 152.65 238.32 125.71 257.41 125.71C257.41 125.71 256.66 120.47 237.95 120.47C205.4 120.47 169.85 139.93 147.02 174.73C139.91 167.25 132.05 165.75 126.44 165.75C121.58 165.75 118.58 166.87 118.58 166.87C137.29 177.72 129.43 213.27 129.43 213.27C125.32 228.24 123.45 243.58 123.45 261.17C123.45 310.19 159.74 397 255.16 397C367.05 397 382.76 282.5 382.76 282.5ZM312.04 346.48C304.56 349.48 295.58 350.6 286.97 350.6C260.03 350.6 236.45 342.74 218.87 329.27C229.72 322.91 258.16 304.95 269.38 277.26C269.38 277.26 272.75 267.15 272.75 252.94V166.87C276.87 172.11 289.59 185.58 312.04 189.7ZM179.2 236.85C179.2 228.24 179.95 220.01 181.07 212.52C195.29 208.41 212.88 199.8 227.85 191.19V305.7C227.85 316.92 220.36 322.91 215.5 326.28C192.67 306.07 179.2 275.39 179.2 236.85Z" fill="#D4B483"/>
</svg>
```

### D. App Icon Squircle Light (512×512) — [`calibrate-app-icon-512-light.svg`](/assets/brand/calibrate-app-icon-512.svg)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <rect width="512" height="512" rx="115" fill="#FFFFFF"/>
  <rect width="510" height="510" x="1" y="1" rx="114" fill="none" stroke="#E5E5E5" stroke-width="2"/>

  <path d="M382.76 282.5H379.77C379.77 282.5 361.81 327.77 318.78 344.61V191.19C320.65 191.19 323.27 191.19 325.51 191.19C385.38 191.57 396.23 131.7 392.87 127.58C392.87 127.58 383.89 147.79 356.2 147.79C319.9 147.79 308.67 107 308.67 107C308.67 107 268.26 170.99 182.57 205.79C195.29 152.65 238.32 125.71 257.41 125.71C257.41 125.71 256.66 120.47 237.95 120.47C205.4 120.47 169.85 139.93 147.02 174.73C139.91 167.25 132.05 165.75 126.44 165.75C121.58 165.75 118.58 166.87 118.58 166.87C137.29 177.72 129.43 213.27 129.43 213.27C125.32 228.24 123.45 243.58 123.45 261.17C123.45 310.19 159.74 397 255.16 397C367.05 397 382.76 282.5 382.76 282.5ZM312.04 346.48C304.56 349.48 295.58 350.6 286.97 350.6C260.03 350.6 236.45 342.74 218.87 329.27C229.72 322.91 258.16 304.95 269.38 277.26C269.38 277.26 272.75 267.15 272.75 252.94V166.87C276.87 172.11 289.59 185.58 312.04 189.7ZM179.2 236.85C179.2 228.24 179.95 220.01 181.07 212.52C195.29 208.41 212.88 199.8 227.85 191.19V305.7C227.85 316.92 220.36 322.91 215.5 326.28C192.67 306.07 179.2 275.39 179.2 236.85Z" fill="#9A7432"/>
</svg>
```

### E. Favicon (32×32) — [`calibrate-favicon-32.svg`](/assets/brand/calibrate-favicon-32.svg)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <rect width="32" height="32" rx="7" fill="#FFFFFF"/>
  <rect width="30" height="30" x="1" y="1" rx="6" fill="none" stroke="#E5E5E5" stroke-width="1"/>
  <path d="M24.74 17.6H24.54C24.54 17.6 23.3 20.73 20.33 21.89V11.31C20.46 11.31 20.64 11.31 20.79 11.31C24.92 11.33 25.67 7.2 25.44 6.92C25.44 6.92 24.82 8.31 22.91 8.31C20.41 8.31 19.63 5.5 19.63 5.5C19.63 5.5 16.85 9.91 10.94 12.31C11.81 8.65 14.78 6.79 16.1 6.79C16.1 6.79 16.05 6.43 14.76 6.43C12.51 6.43 10.06 7.77 8.48 10.17C7.99 9.65 7.45 9.55 7.06 9.55C6.73 9.55 6.52 9.63 6.52 9.63C7.81 10.38 7.27 12.83 7.27 12.83C6.99 13.86 6.86 14.92 6.86 16.13C6.86 19.51 9.36 25.5 15.94 25.5C23.66 25.5 24.74 17.6 24.74 17.6ZM19.86 22.02C19.35 22.22 18.73 22.3 18.14 22.3C16.28 22.3 14.65 21.76 13.44 20.83C14.19 20.39 16.15 19.15 16.92 17.24C16.92 17.24 17.16 16.55 17.16 15.56V9.63C17.44 9.99 18.32 10.92 19.86 11.2ZM10.7 14.45C10.7 13.86 10.76 13.29 10.83 12.78C11.81 12.49 13.03 11.9 14.06 11.31V19.2C14.06 19.98 13.54 20.39 13.21 20.62C11.63 19.23 10.7 17.11 10.7 14.45Z" fill="#D4B483"/>
</svg>
```

---

## 8. Verification Checklist for the Agent

When you finish integrating the brand into the website, verify the following:
- [ ] Navbar displays **Champagne Gold (`#D4B483`)** Initial 'C' and **Pure White (`#FFFFFF`)** text on black background.
- [ ] In light mode, the logo cleanly transitions to **Milled Brass (`#9A7432`)** and **Pure Black (`#000000`)**.
- [ ] Browser tab displays [`calibrate-favicon-32.svg`](/assets/brand/calibrate-favicon-32.svg).
- [ ] Backgrounds are strictly `#000000` (dark) and `#FFFFFF` (light) with zero blue or purple skew.
- [ ] No 3D shadows, gradients, or watch bezel dials exist.
