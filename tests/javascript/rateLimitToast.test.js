import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('rateLimitToast', () => {
  let showRateLimitToast, hideRateLimitToast, _setRateLimited;

  beforeEach(async () => {
    vi.useFakeTimers();

    // Clean DOM
    document.body.innerHTML = '';

    const mod =
      await import('../../src/smplfrm/smplfrm/static/resilientFetch.js');
    showRateLimitToast = mod.showRateLimitToast;
    hideRateLimitToast = mod.hideRateLimitToast;
    _setRateLimited = mod._setRateLimited;

    _setRateLimited(false);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.resetModules();
  });

  describe('showRateLimitToast', () => {
    it('makes toast element visible with opacity 1', () => {
      showRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      expect(toast).not.toBeNull();
      expect(toast.style.opacity).toBe('1');
      expect(toast.classList.contains('show')).toBe(true);
    });

    it('sets pointer-events to auto when shown', () => {
      showRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      expect(toast.style.pointerEvents).toBe('auto');
    });

    it('creates the toast element if it does not exist', () => {
      expect(document.getElementById('rate-limit-toast')).toBeNull();

      showRateLimitToast();

      expect(document.getElementById('rate-limit-toast')).not.toBeNull();
    });

    it('reuses existing toast element on subsequent calls', () => {
      showRateLimitToast();
      showRateLimitToast();

      const toasts = document.querySelectorAll('#rate-limit-toast');
      expect(toasts.length).toBe(1);
    });

    it('renders an hourglass glyph, the message, and the rate-limit link', () => {
      showRateLimitToast();

      const text = document.getElementById('rate-limit-toast-text');
      expect(text.firstElementChild.tagName).toBe('I');
      expect(text.firstElementChild.className).toBe('iconoir-hourglass');
      expect(text.textContent).toBe(
        ' Requests are temporarily rate-limited. Increase the rate limit',
      );

      const link = text.querySelector('a');
      expect(link.getAttribute('href')).toBe(
        'https://github.com/rickyphewitt/smplFrm/wiki/Environment-Variables#security',
      );
      expect(link.target).toBe('_blank');
      expect(link.rel).toBe('noopener noreferrer');
    });

    it('leaves colors, radius, and type to the stylesheets', () => {
      showRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      const link = toast.querySelector('a');
      for (const prop of [
        'background',
        'color',
        'borderRadius',
        'fontSize',
        'position',
      ]) {
        expect(toast.style[prop]).toBe('');
      }
      expect(link.getAttribute('style')).toBeNull();
    });
  });

  describe('hideRateLimitToast', () => {
    it('triggers opacity fade-out after 10 second delay', async () => {
      showRateLimitToast();
      hideRateLimitToast();

      // Toast should still be visible immediately after calling hide
      const toast = document.getElementById('rate-limit-toast');
      expect(toast.style.opacity).toBe('1');

      // After 10 seconds, it should fade out
      await vi.advanceTimersByTimeAsync(10000);
      expect(toast.style.opacity).toBe('0');
    });

    it('removes the show class after 10 second delay', async () => {
      showRateLimitToast();
      hideRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      expect(toast.classList.contains('show')).toBe(true);

      await vi.advanceTimersByTimeAsync(10000);
      expect(toast.classList.contains('show')).toBe(false);
    });

    it('sets pointer-events to none after 10 second delay', async () => {
      showRateLimitToast();
      hideRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      expect(toast.style.pointerEvents).toBe('auto');

      await vi.advanceTimersByTimeAsync(10000);
      expect(toast.style.pointerEvents).toBe('none');
    });

    it('does not throw if toast element does not exist', () => {
      expect(() => hideRateLimitToast()).not.toThrow();
    });

    it('resets the hide timer if showRateLimitToast is called again', async () => {
      showRateLimitToast();
      hideRateLimitToast();

      // Advance 5 seconds (halfway through the 10s delay)
      await vi.advanceTimersByTimeAsync(5000);

      // Re-trigger the toast (simulates another 429)
      showRateLimitToast();

      // The original 10s timer should be cancelled — toast stays visible
      await vi.advanceTimersByTimeAsync(5000);
      const toast = document.getElementById('rate-limit-toast');
      expect(toast.style.opacity).toBe('1');
      expect(toast.classList.contains('show')).toBe(true);
    });
  });

  describe('toast visibility while rate-limited', () => {
    it('toast remains visible while _rateLimited is true', () => {
      _setRateLimited(true);
      showRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      expect(toast.style.opacity).toBe('1');
      expect(toast.classList.contains('show')).toBe(true);

      // Call show again to simulate continued rate-limited state
      showRateLimitToast();
      expect(toast.style.opacity).toBe('1');
      expect(toast.classList.contains('show')).toBe(true);
    });
  });

  describe('informational styling', () => {
    it('uses informational styling with no error or warning CSS classes', () => {
      showRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      expect(toast.classList.contains('error')).toBe(false);
      expect(toast.classList.contains('warning')).toBe(false);
      expect(toast.classList.contains('danger')).toBe(false);
      expect(toast.classList.contains('alert')).toBe(false);
    });

    it('takes its colors from the active theme, not inline styles', () => {
      showRateLimitToast();

      // The muted informational palette is declared in the theme stylesheet
      // (`.rate-limit-toast` in theme-classic.css), so any theme can restyle it.
      const toast = document.getElementById('rate-limit-toast');
      expect(toast.className).toBe('rate-limit-toast show');
      expect(toast.style.background).toBe('');
      expect(toast.style.color).toBe('');
    });
  });

  describe('wiki hyperlink', () => {
    it('contains a hyperlink to the Environment Variables wiki page', () => {
      showRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      const link = toast.querySelector('a');
      expect(link).not.toBeNull();
      expect(link.href).toBe(
        'https://github.com/rickyphewitt/smplFrm/wiki/Environment-Variables#security',
      );
    });

    it('link opens in a new tab', () => {
      showRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      const link = toast.querySelector('a');
      expect(link.target).toBe('_blank');
    });
  });

  describe('DOM separation from task toast', () => {
    it('is a separate DOM element from the task toast', () => {
      // Add a task toast to the DOM
      const taskToast = document.createElement('div');
      taskToast.id = 'task-toast';
      taskToast.className = 'task-toast';
      taskToast.style.position = 'fixed';
      taskToast.style.bottom = '20px';
      document.body.appendChild(taskToast);

      showRateLimitToast();

      const rateLimitToast = document.getElementById('rate-limit-toast');
      expect(rateLimitToast).not.toBe(taskToast);
      expect(rateLimitToast.id).not.toBe('task-toast');
    });

    it('is placed by its own class rather than by inline offsets', () => {
      const taskToast = document.createElement('div');
      taskToast.id = 'task-toast';
      taskToast.className = 'task-toast';
      document.body.appendChild(taskToast);

      showRateLimitToast();

      // base.css stacks `.rate-limit-toast` above `.task-toast`; its
      // contract test checks the offsets. No inline offset may override it.
      const rateLimitToast = document.getElementById('rate-limit-toast');
      expect(rateLimitToast.classList.contains('rate-limit-toast')).toBe(true);
      expect(rateLimitToast.classList.contains('task-toast')).toBe(false);
      expect(rateLimitToast.style.bottom).toBe('');
    });
  });
});
