import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('rateLimitToast', () => {
  let showRateLimitToast, hideRateLimitToast, _setRateLimited;

  beforeEach(async () => {
    vi.useFakeTimers();

    // Clean DOM
    document.body.innerHTML = '';

    const mod = await import(
      '../../src/smplfrm/smplfrm/static/resilientFetch.js'
    );
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

    it('uses muted blue/gray background color', () => {
      showRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      expect(toast.style.background).toBe('rgba(45, 55, 72, 0.92)');
    });

    it('uses light gray text color', () => {
      showRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      // jsdom normalizes hex to rgb
      expect(toast.style.color).toBe('rgb(203, 213, 224)');
    });
  });

  describe('wiki hyperlink', () => {
    it('contains a hyperlink to the Environment Variables wiki page', () => {
      showRateLimitToast();

      const toast = document.getElementById('rate-limit-toast');
      const link = toast.querySelector('a');
      expect(link).not.toBeNull();
      expect(link.href).toBe(
        'https://github.com/rickyphewitt/smplFrm/wiki/Environment-Variables#security'
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

    it('is positioned at a different vertical offset than task toast', () => {
      const taskToast = document.createElement('div');
      taskToast.id = 'task-toast';
      taskToast.style.position = 'fixed';
      taskToast.style.bottom = '20px';
      document.body.appendChild(taskToast);

      showRateLimitToast();

      const rateLimitToast = document.getElementById('rate-limit-toast');
      expect(rateLimitToast.style.bottom).toBe('80px');
      expect(rateLimitToast.style.bottom).not.toBe(taskToast.style.bottom);
    });
  });
});
