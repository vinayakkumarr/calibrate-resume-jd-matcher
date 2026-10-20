/**
 * JD Analyser — Word-Level Diff Visual Renderer
 * Computes surgical visual diffs comparing candidate original experience bullets
 * against Google XYZ achievements using jsdiff with full XSS escaping.
 */

function escapeHtml(text) {
  if (text === null || text === undefined) {
    return '';
  }
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

/**
 * Computes word-level diff highlighting newly added achievements in emerald.
 */
function renderDiff(originalText, upgradedText) {
  if (!originalText || !upgradedText) {
    return escapeHtml(upgradedText || '');
  }

  // Graceful fallback if jsdiff CDN has not initialized
  if (typeof Diff === 'undefined' || typeof Diff.diffWords !== 'function') {
    return escapeHtml(upgradedText);
  }

  try {
    const diff = Diff.diffWords(originalText, upgradedText);
    let html = '';

    diff.forEach((part) => {
      if (part.added) {
        html += `<span class="diff-added">${escapeHtml(part.value)}</span>`;
      } else if (part.removed) {
        // In the upgraded achievement box, omit removed words for reading clarity
      } else {
        html += `<span class="diff-context">${escapeHtml(part.value)}</span>`;
      }
    });

    return html;
  } catch (err) {
    console.error('Diff computation error:', err);
    return escapeHtml(upgradedText);
  }
}

/**
 * Computes full unified redline diff showing both additions (emerald) and deletions (strikethrough).
 */
function renderFullRedline(originalText, upgradedText) {
  if (!originalText || !upgradedText) {
    return escapeHtml(upgradedText || originalText || '');
  }

  if (typeof Diff === 'undefined' || typeof Diff.diffWords !== 'function') {
    return escapeHtml(upgradedText);
  }

  try {
    const diff = Diff.diffWords(originalText, upgradedText);
    let html = '';

    diff.forEach((part) => {
      if (part.added) {
        html += `<span class="diff-added">${escapeHtml(part.value)}</span>`;
      } else if (part.removed) {
        html += `<span class="diff-removed">${escapeHtml(part.value)}</span>`;
      } else {
        html += `<span class="diff-context">${escapeHtml(part.value)}</span>`;
      }
    });

    return html;
  } catch (err) {
    console.error('Full redline computation error:', err);
    return escapeHtml(upgradedText);
  }
}
