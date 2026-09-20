import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const MODULE_PATH = '../../src/smplfrm/smplfrm/static/uiErrors.js';
const CLIENT_PATH = '../../src/smplfrm/smplfrm/static/jsonApiClient.js';
const FETCH_PATH = '../../src/smplfrm/smplfrm/static/resilientFetch.js';

describe('uiErrors', () => {
  let uiErrors, JsonApiError;

  beforeEach(async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '';
    vi.resetModules();

    uiErrors = await import(MODULE_PATH);
    ({ JsonApiError } = await import(CLIENT_PATH));

    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    // The module is re-imported per test against a persistent jsdom window, so
    // the global listener must be detached or listeners accumulate across cases.
    uiErrors._resetGlobalRejectionHandler();
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.resetModules();
  });

  // ---------------------------------------------------------------------
  // Message derivation and suppression
  // ---------------------------------------------------------------------

  describe('deriveErrorMessage', () => {
    it('returns errors[0].detail for a 4xx JsonApiError', () => {
      const error = new JsonApiError(400, [{ detail: 'Invalid coordinates' }]);

      expect(uiErrors.deriveErrorMessage(error, 'Fallback')).toBe(
        'Invalid coordinates',
      );
    });

    it('returns the fallback for a 5xx JsonApiError', () => {
      const error = new JsonApiError(500, [{ detail: 'Internal error' }]);

      expect(uiErrors.deriveErrorMessage(error, 'Fallback')).toBe('Fallback');
    });

    it('returns errors[0].detail for a 403 JsonApiError', () => {
      // Detail endpoints return 403 rather than 404 for a nonexistent
      // resource, so a 403 is an ordinary client-visible outcome here and
      // not an auth-specific signal.
      const error = new JsonApiError(403, [{ detail: 'Preset not found' }]);

      expect(uiErrors.deriveErrorMessage(error, 'Fallback')).toBe(
        'Preset not found',
      );
    });

    it('returns the fallback for a bare TypeError', () => {
      const error = new TypeError('Failed to fetch');

      expect(uiErrors.deriveErrorMessage(error, 'Fallback')).toBe('Fallback');
    });

    it('returns the fallback for a JsonApiError with an empty errors array', () => {
      const error = new JsonApiError(422, []);

      expect(uiErrors.deriveErrorMessage(error, 'Fallback')).toBe('Fallback');
    });

    it('returns the fallback when the 4xx detail is absent or blank', () => {
      expect(
        uiErrors.deriveErrorMessage(new JsonApiError(409, [{}]), 'Fallback'),
      ).toBe('Fallback');
      expect(
        uiErrors.deriveErrorMessage(
          new JsonApiError(409, [{ detail: '   ' }]),
          'Fallback',
        ),
      ).toBe('Fallback');
    });

    it('returns the fallback for a null or undefined error', () => {
      expect(uiErrors.deriveErrorMessage(null, 'Fallback')).toBe('Fallback');
      expect(uiErrors.deriveErrorMessage(undefined, 'Fallback')).toBe(
        'Fallback',
      );
    });

    it('never returns raw exception text or a stack for a non-JsonApiError', () => {
      const error = new Error('ReferenceError at main.js:42 secretToken=abc');

      const message = uiErrors.deriveErrorMessage(error, 'Fallback');

      expect(message).toBe('Fallback');
      expect(message).not.toContain('secretToken');
    });
  });

  describe('isSuppressed', () => {
    it('returns true for status 429', () => {
      expect(uiErrors.isSuppressed(new JsonApiError(429, [{}]))).toBe(true);
    });

    it('returns false for other statuses and non-JsonApiError values', () => {
      expect(uiErrors.isSuppressed(new JsonApiError(400, [{}]))).toBe(false);
      expect(uiErrors.isSuppressed(new JsonApiError(500, [{}]))).toBe(false);
      expect(uiErrors.isSuppressed(new TypeError('Failed to fetch'))).toBe(
        false,
      );
      expect(uiErrors.isSuppressed(null)).toBe(false);
    });
  });

  describe('reportError with a 429', () => {
    it('performs no DOM mutation, shows no toast, and logs nothing', () => {
      document.body.innerHTML = '<div id="error-message"></div>';
      const before = document.body.innerHTML;
      const error = new JsonApiError(429, [{ detail: 'Too many requests' }]);

      uiErrors.reportError(error, { channel: 'action', fallback: 'Fallback' });
      uiErrors.reportError(error, { channel: 'form', fallback: 'Fallback' });

      expect(document.getElementById('app-toast')).toBeNull();
      expect(document.body.innerHTML).toBe(before);
      expect(console.error).not.toHaveBeenCalled();
      expect(console.debug).not.toHaveBeenCalled();
    });

    it('does not invoke the indicator degrade callback', () => {
      const onDegrade = vi.fn();

      uiErrors.reportError(new JsonApiError(429, [{}]), {
        channel: 'indicator',
        fallback: 'Fallback',
        onDegrade,
      });

      expect(onDegrade).not.toHaveBeenCalled();
    });
  });

  // ---------------------------------------------------------------------
  // Renderers and the global handler
  // ---------------------------------------------------------------------

  describe('showActionToast', () => {
    it('creates #app-toast on first use and reuses it thereafter', () => {
      expect(document.getElementById('app-toast')).toBeNull();

      uiErrors.showActionToast('First');
      const toast = document.getElementById('app-toast');
      expect(toast).not.toBeNull();
      expect(toast.textContent).toBe('First');

      uiErrors.showActionToast('Second');

      expect(document.querySelectorAll('#app-toast').length).toBe(1);
      expect(document.getElementById('app-toast')).toBe(toast);
      expect(toast.textContent).toBe('Second');
    });

    it('is positioned clear of the rate-limit and task toasts', () => {
      uiErrors.showActionToast('Message');

      const toast = document.getElementById('app-toast');
      expect(toast.style.position).toBe('fixed');
      expect(toast.style.bottom).not.toBe('80px');
      expect(toast.style.bottom).not.toBe('20px');
      expect(parseInt(toast.style.bottom, 10)).toBeGreaterThan(80);
    });

    it('allows all three toasts to be visible simultaneously', async () => {
      document.body.innerHTML =
        '<div id="task-toast" class="task-toast show" style="bottom: 20px;">' +
        '<span id="task-toast-text"></span><div id="task-toast-bar"></div></div>';
      const { showRateLimitToast, _setRateLimited } = await import(FETCH_PATH);
      _setRateLimited(false);

      showRateLimitToast();
      uiErrors.showActionToast('Message');

      const rateToast = document.getElementById('rate-limit-toast');
      const taskToast = document.getElementById('task-toast');
      const appToast = document.getElementById('app-toast');
      expect(rateToast.style.opacity).toBe('1');
      expect(taskToast.classList.contains('show')).toBe(true);
      expect(appToast.style.opacity).toBe('1');

      const bottoms = [
        rateToast.style.bottom,
        taskToast.style.bottom,
        appToast.style.bottom,
      ];
      expect(new Set(bottoms).size).toBe(3);
    });

    it('never reads or writes the task toast elements', () => {
      document.body.innerHTML =
        '<div id="task-toast"><span id="task-toast-text">Working</span>' +
        '<div id="task-toast-bar" style="width: 40%;"></div></div>';
      const taskToastMarkup = document.getElementById('task-toast').outerHTML;
      const getById = vi.spyOn(document, 'getElementById');

      uiErrors.showActionToast('Message');

      const touchedIds = getById.mock.calls.map((call) => call[0]);
      expect(touchedIds).not.toContain('task-toast');
      expect(touchedIds).not.toContain('task-toast-text');
      expect(touchedIds).not.toContain('task-toast-bar');
      expect(document.getElementById('task-toast').outerHTML).toBe(
        taskToastMarkup,
      );
    });

    it('auto-hides after the display window', () => {
      uiErrors.showActionToast('Message');
      const toast = document.getElementById('app-toast');
      expect(toast.style.opacity).toBe('1');

      vi.advanceTimersByTime(uiErrors.ACTION_TOAST_DURATION_MS);

      expect(toast.style.opacity).toBe('0');
      expect(toast.classList.contains('show')).toBe(false);
    });

    it('renders a hostile message as literal text', () => {
      uiErrors.showActionToast('<img src=x onerror=alert(1)>');

      const toast = document.getElementById('app-toast');
      expect(toast.querySelector('img')).toBeNull();
      expect(toast.textContent).toBe('<img src=x onerror=alert(1)>');
    });
  });

  describe('showFormError', () => {
    beforeEach(() => {
      document.body.innerHTML =
        '<div class="error-message" id="error-message"></div>' +
        '<button id="save-settings">Save Changes</button>';
    });

    it('shows #error-message, disables the button, and restores both', () => {
      const button = document.getElementById('save-settings');

      uiErrors.showFormError('Timezone is invalid', { disable: button });

      const region = document.getElementById('error-message');
      expect(region.textContent).toBe('Timezone is invalid');
      expect(region.classList.contains('show')).toBe(true);
      expect(button.disabled).toBe(true);

      vi.advanceTimersByTime(uiErrors.FORM_ERROR_DURATION_MS);

      expect(region.classList.contains('show')).toBe(false);
      expect(button.disabled).toBe(false);
    });

    it('works without a button and preserves the 3 second window', () => {
      expect(uiErrors.FORM_ERROR_DURATION_MS).toBe(3000);

      expect(() => uiErrors.showFormError('Nope')).not.toThrow();

      expect(
        document.getElementById('error-message').classList.contains('show'),
      ).toBe(true);
    });

    it('renders a hostile message as literal text', () => {
      uiErrors.showFormError('<img src=x onerror=alert(1)>');

      const region = document.getElementById('error-message');
      expect(region.querySelector('img')).toBeNull();
      expect(region.textContent).toBe('<img src=x onerror=alert(1)>');
    });
  });

  describe('showViewPlaceholder', () => {
    it('renders a row with the requested colspan into a table body', () => {
      document.body.innerHTML =
        '<table><tbody id="preset-list-body"><tr><td>stale</td></tr></tbody></table>';
      const body = document.getElementById('preset-list-body');

      uiErrors.showViewPlaceholder(body, 'Failed to load presets', 4);

      const cells = body.querySelectorAll('td');
      expect(cells.length).toBe(1);
      expect(cells[0].getAttribute('colspan')).toBe('4');
      expect(cells[0].textContent).toBe('Failed to load presets');
    });

    it('renders a div placeholder into a non-table target without wiping it', () => {
      document.body.innerHTML =
        '<div id="settings-body"><input id="setting-date"></div>';
      const target = document.getElementById('settings-body');

      uiErrors.showViewPlaceholder(target, 'Failed to load settings');

      expect(target.textContent).toContain('Failed to load settings');
      expect(document.getElementById('setting-date')).not.toBeNull();
    });

    it('replaces a previous placeholder instead of stacking them', () => {
      document.body.innerHTML = '<div id="settings-body"></div>';
      const target = document.getElementById('settings-body');

      uiErrors.showViewPlaceholder(target, 'First');
      uiErrors.showViewPlaceholder(target, 'Second');

      const placeholders = target.querySelectorAll(
        `.${uiErrors.ERROR_PLACEHOLDER_CLASS}`,
      );
      expect(placeholders.length).toBe(1);
      expect(placeholders[0].textContent).toBe('Second');
    });

    it('clears the placeholder on request while leaving other content', () => {
      document.body.innerHTML =
        '<div id="settings-body"><input id="setting-date"></div>';
      const target = document.getElementById('settings-body');
      uiErrors.showViewPlaceholder(target, 'Failed to load settings');

      uiErrors.clearViewPlaceholder(target);

      expect(
        target.querySelectorAll(`.${uiErrors.ERROR_PLACEHOLDER_CLASS}`).length,
      ).toBe(0);
      expect(document.getElementById('setting-date')).not.toBeNull();
    });

    it('renders a hostile message as literal text', () => {
      document.body.innerHTML = '<table><tbody id="rows"></tbody></table>';
      const body = document.getElementById('rows');

      uiErrors.showViewPlaceholder(body, '<img src=x onerror=alert(1)>', 4);

      expect(body.querySelector('img')).toBeNull();
      expect(body.textContent).toBe('<img src=x onerror=alert(1)>');
    });
  });

  describe('missing targets', () => {
    it('logs and does not throw when the view target is absent', () => {
      expect(() =>
        uiErrors.reportError(new TypeError('boom'), {
          channel: 'view',
          fallback: 'Failed to load presets',
          target: null,
          colspan: 4,
        }),
      ).not.toThrow();

      expect(console.error).toHaveBeenCalledTimes(1);
    });

    it('logs and does not throw when #error-message is absent', () => {
      expect(() =>
        uiErrors.reportError(new TypeError('boom'), {
          channel: 'form',
          fallback: 'Failed to save settings',
        }),
      ).not.toThrow();

      expect(console.error).toHaveBeenCalledTimes(1);
    });
  });

  describe('single-log discipline', () => {
    const error = () => new JsonApiError(400, [{ detail: 'Nope' }]);

    it('logs console.error exactly once for the action channel', () => {
      uiErrors.reportError(error(), {
        channel: 'action',
        fallback: 'Fallback',
      });

      expect(console.error).toHaveBeenCalledTimes(1);
      expect(console.debug).not.toHaveBeenCalled();
    });

    it('logs console.error exactly once for the form channel', () => {
      document.body.innerHTML = '<div id="error-message"></div>';

      uiErrors.reportError(error(), { channel: 'form', fallback: 'Fallback' });

      expect(console.error).toHaveBeenCalledTimes(1);
      expect(console.debug).not.toHaveBeenCalled();
    });

    it('logs console.error exactly once for the view channel', () => {
      document.body.innerHTML = '<table><tbody id="rows"></tbody></table>';

      uiErrors.reportError(error(), {
        channel: 'view',
        fallback: 'Fallback',
        target: document.getElementById('rows'),
        colspan: 4,
      });

      expect(console.error).toHaveBeenCalledTimes(1);
      expect(console.debug).not.toHaveBeenCalled();
    });

    it('logs console.debug exactly once for the silent channel and mutates no DOM', () => {
      document.body.innerHTML = '<div id="error-message"></div>';
      const before = document.body.innerHTML;

      uiErrors.reportError(error(), { channel: 'silent', fallback: 'Fallback' });

      expect(console.debug).toHaveBeenCalledTimes(1);
      expect(console.error).not.toHaveBeenCalled();
      expect(document.body.innerHTML).toBe(before);
      expect(document.getElementById('app-toast')).toBeNull();
    });

    it('logs console.debug exactly once for the indicator channel and invokes onDegrade', () => {
      const onDegrade = vi.fn();

      uiErrors.reportError(error(), {
        channel: 'indicator',
        fallback: 'Fallback',
        onDegrade,
      });

      expect(console.debug).toHaveBeenCalledTimes(1);
      expect(console.error).not.toHaveBeenCalled();
      expect(onDegrade).toHaveBeenCalledTimes(1);
      expect(document.getElementById('app-toast')).toBeNull();
    });

    it('does not throw when the indicator channel has no callback', () => {
      expect(() =>
        uiErrors.reportError(error(), {
          channel: 'indicator',
          fallback: 'Fallback',
        }),
      ).not.toThrow();
    });

    it('does not throw and logs once for an unknown channel', () => {
      expect(() =>
        uiErrors.reportError(error(), {
          channel: 'nonsense',
          fallback: 'Fallback',
        }),
      ).not.toThrow();

      expect(console.error).toHaveBeenCalledTimes(1);
      expect(document.getElementById('app-toast')).toBeNull();
    });

    it('renders the derived message, never the raw exception text', () => {
      uiErrors.reportError(new Error('stack trace leak'), {
        channel: 'action',
        fallback: 'Something went wrong',
      });

      expect(document.getElementById('app-toast').textContent).toBe(
        'Something went wrong',
      );
    });
  });

  describe('installGlobalRejectionHandler', () => {
    it('produces one console.error and one action toast per unhandledrejection', () => {
      uiErrors.installGlobalRejectionHandler();

      const event = new Event('unhandledrejection');
      event.reason = new TypeError('Failed to fetch');
      window.dispatchEvent(event);

      expect(console.error).toHaveBeenCalledTimes(1);
      const toast = document.getElementById('app-toast');
      expect(toast).not.toBeNull();
      expect(toast.style.opacity).toBe('1');
      expect(toast.textContent.length).toBeGreaterThan(0);
    });

    it('surfaces a 4xx detail from the rejection reason', async () => {
      uiErrors.installGlobalRejectionHandler();

      const event = new Event('unhandledrejection');
      event.reason = new JsonApiError(400, [{ detail: 'Bad request detail' }]);
      window.dispatchEvent(event);

      expect(document.getElementById('app-toast').textContent).toBe(
        'Bad request detail',
      );
    });

    it('stays silent for a rejected 429', () => {
      uiErrors.installGlobalRejectionHandler();

      const event = new Event('unhandledrejection');
      event.reason = new JsonApiError(429, [{ detail: 'Too many requests' }]);
      window.dispatchEvent(event);

      expect(document.getElementById('app-toast')).toBeNull();
      expect(console.error).not.toHaveBeenCalled();
    });

    it('registers the listener only once across repeated calls', () => {
      uiErrors.installGlobalRejectionHandler();
      uiErrors.installGlobalRejectionHandler();

      const event = new Event('unhandledrejection');
      event.reason = new TypeError('Failed to fetch');
      window.dispatchEvent(event);

      expect(console.error).toHaveBeenCalledTimes(1);
    });
  });
});
