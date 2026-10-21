/**
 * Interactive canvas grid cell illuminator.
 * Highlights the grid cell under the pointer and applies cubic attack and
 * quadratic decay easing transitions on enter and exit.
 */

(function () {
  'use strict';

  const GRID_SIZE = 36;
  const ATTACK_DURATION = 200;    // Attack transition duration in milliseconds
  const DECAY_DURATION = 420;     // Fade-out decay duration in milliseconds
  const HOVER_ALPHA_FILL = 0.055;  // Cell background fill opacity
  const HOVER_ALPHA_STROKE = 0.22; // Cell border stroke opacity

  let canvas = null;
  let ctx = null;
  let dpr = 1;
  let width = 0;
  let height = 0;
  let offsetX = 0;
  let offsetY = 0;

  // Track active cells: key -> { col, row, x, y, enterTime, exitTime, exitAlpha }
  const activeCells = new Map();
  let currentKey = null;
  let animationFrameId = null;

  function isHomePage() {
    if (window.Alpine && document.body) {
      try {
        const alpineData = window.Alpine.$data(document.body);
        if (alpineData && alpineData.view !== 'upload') {
          return false;
        }
      } catch (e) {}
    }
    const resultsEl = document.querySelector('[x-show="view === \'results\'"]');
    if (resultsEl && resultsEl.style.display !== 'none' && resultsEl.offsetParent !== null) {
      return false;
    }
    return true;
  }

  function calculateGridOffset() {
    // Synchronize horizontal center with document layout viewport (matches CSS background-position: center on body)
    const clientW = document.documentElement.clientWidth || (document.body ? document.body.clientWidth : width);
    const centerX = clientW / 2;
    const baseOffset = (centerX - (GRID_SIZE / 2)) % GRID_SIZE;
    const scrollX = window.scrollX || window.pageXOffset || 0;
    const scrollY = window.scrollY || window.pageYOffset || 0;

    offsetX = (((baseOffset - scrollX) % GRID_SIZE) + GRID_SIZE) % GRID_SIZE;
    offsetY = (((-scrollY) % GRID_SIZE) + GRID_SIZE) % GRID_SIZE;
  }

  function resizeCanvas() {
    if (!canvas) return;
    dpr = window.devicePixelRatio || 1;
    width = window.innerWidth;
    height = window.innerHeight;

    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';

    ctx = canvas.getContext('2d', { alpha: true });
    ctx.scale(dpr, dpr);

    calculateGridOffset();
  }

  function getCellAlpha(cell, now) {
    if (cell.exitTime === null) {
      // Blooming in or fully active
      const elapsed = Math.max(0, now - cell.enterTime);
      const progress = Math.min(1, elapsed / ATTACK_DURATION);
      // Cubic ease-out attack: 1 - (1 - t)^3
      return 1 - Math.pow(1 - progress, 3);
    } else {
      // Fading out
      const elapsed = Math.max(0, now - cell.exitTime);
      if (elapsed >= DECAY_DURATION) return 0;
      const progress = elapsed / DECAY_DURATION;
      // Quadratic ease-out decay: exitAlpha * (1 - t)^2.2
      return cell.exitAlpha * Math.pow(1 - progress, 2.2);
    }
  }

  function handlePointerMove(e) {
    if (!isHomePage()) {
      clearAll();
      return;
    }

    const x = e.clientX;
    const y = e.clientY;

    const col = Math.floor((x - offsetX) / GRID_SIZE);
    const row = Math.floor((y - offsetY) / GRID_SIZE);
    const key = `${col},${row}`;
    const cellX = offsetX + col * GRID_SIZE;
    const cellY = offsetY + row * GRID_SIZE;

    // Check bounds
    if (cellX + GRID_SIZE < 0 || cellX > width || cellY + GRID_SIZE < 0 || cellY > height) {
      handlePointerLeave();
      return;
    }

    const now = performance.now();

    if (currentKey !== key) {
      // 1. Mark previous cell as exiting
      if (currentKey && activeCells.has(currentKey)) {
        const prev = activeCells.get(currentKey);
        prev.exitTime = now;
        prev.exitAlpha = getCellAlpha(prev, now);
      }

      // 2. Activate new cell with smooth bloom
      if (activeCells.has(key)) {
        // Re-entering a cell that was fading out: reverse direction seamlessly
        const existing = activeCells.get(key);
        const currentAlpha = getCellAlpha(existing, now);
        existing.enterTime = now - (currentAlpha * ATTACK_DURATION);
        existing.exitTime = null;
        existing.exitAlpha = 1;
      } else {
        // Fresh entry
        activeCells.set(key, {
          col,
          row,
          enterTime: now,
          exitTime: null,
          exitAlpha: 1
        });
      }

      currentKey = key;
    }

    if (!animationFrameId) {
      animationFrameId = requestAnimationFrame(renderLoop);
    }
  }

  function handlePointerLeave() {
    if (currentKey && activeCells.has(currentKey)) {
      const now = performance.now();
      const prev = activeCells.get(currentKey);
      prev.exitTime = now;
      prev.exitAlpha = getCellAlpha(prev, now);
      currentKey = null;
      if (!animationFrameId) {
        animationFrameId = requestAnimationFrame(renderLoop);
      }
    }
  }

  function clearAll() {
    if (ctx && width && height) {
      ctx.clearRect(0, 0, width, height);
    }
    activeCells.clear();
    currentKey = null;
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
    }
  }

  function renderLoop(currentTime) {
    if (!isHomePage()) {
      clearAll();
      return;
    }

    ctx.clearRect(0, 0, width, height);

    let hasActive = false;

    activeCells.forEach((cell, key) => {
      const alpha = getCellAlpha(cell, currentTime);

      if (alpha <= 0.001) {
        if (cell.exitTime !== null) {
          activeCells.delete(key);
        }
      } else {
        hasActive = true;
        const fillAlpha = alpha * HOVER_ALPHA_FILL;
        const strokeAlpha = alpha * HOVER_ALPHA_STROKE;

        // Derive dynamic viewport coordinates anchored to active offset
        const drawX = offsetX + cell.col * GRID_SIZE;
        const drawY = offsetY + cell.row * GRID_SIZE;

        // Brand accent fill (#EA580C -> 234, 88, 12)
        ctx.fillStyle = `rgba(234, 88, 12, ${fillAlpha.toFixed(4)})`;
        ctx.fillRect(drawX, drawY, GRID_SIZE, GRID_SIZE);

        // Border stroke highlight snapped to exact 1px grid line boundaries
        ctx.strokeStyle = `rgba(234, 88, 12, ${strokeAlpha.toFixed(4)})`;
        ctx.lineWidth = 1;
        ctx.strokeRect(drawX + 0.5, drawY + 0.5, GRID_SIZE - 1, GRID_SIZE - 1);
      }
    });

    if (hasActive) {
      animationFrameId = requestAnimationFrame(renderLoop);
    } else {
      animationFrameId = null;
    }
  }

  function handleScroll() {
    if (!isHomePage()) return;
    calculateGridOffset();
    if (activeCells.size > 0 && !animationFrameId) {
      animationFrameId = requestAnimationFrame(renderLoop);
    }
  }

  function init() {
    canvas = document.getElementById('gridCanvas');
    if (!canvas) return;

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas, { passive: true });
    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('pointermove', handlePointerMove, { passive: true });
    document.addEventListener('pointerleave', handlePointerLeave, { passive: true });

    window.addEventListener('popstate', clearAll);
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) clearAll();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
