// Module-level state
export let _rateLimited = false;
export const MAX_RETRIES = 3;
export const DEFAULT_RETRY_AFTER_SECONDS = 5;
export const TOAST_MIN_DISPLAY_MS = 10000;

// Timer ID for the toast auto-hide
let _toastHideTimer = null;

/**
 * Resets the rate-limited state. Used for testing.
 *
 * @param {boolean} value - The value to set _rateLimited to
 */
export function _setRateLimited(value) {
  _rateLimited = value;
}

/**
 * Shows the rate-limit informational toast.
 * Creates the toast element dynamically if it doesn't already exist in the DOM.
 * The toast stays visible for at least 10 seconds. If re-triggered during that
 * window, the timer resets to another 10 seconds.
 */
export function showRateLimitToast() {
  let toast = document.getElementById('rate-limit-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'rate-limit-toast';
    toast.className = 'rate-limit-toast';
    Object.assign(toast.style, {
      position: 'fixed',
      bottom: '80px',
      right: '20px',
      background: 'rgba(45, 55, 72, 0.92)',
      color: '#cbd5e0',
      padding: '12px 18px',
      borderRadius: '8px',
      fontSize: '13px',
      zIndex: '10000',
      opacity: '0',
      pointerEvents: 'none',
      transition: 'opacity 0.3s',
      minWidth: '180px',
    });

    const text = document.createElement('span');
    text.id = 'rate-limit-toast-text';
    text.innerHTML =
      '⏳ Requests are temporarily rate-limited. ' +
      '<a href="https://github.com/rickyphewitt/smplFrm/wiki/Environment-Variables#security" ' +
      'target="_blank" style="color: #90cdf4; text-decoration: underline;">Increase the rate limit</a>';
    toast.appendChild(text);
    document.body.appendChild(toast);
  }
  toast.classList.add('show');
  toast.style.opacity = '1';
  toast.style.pointerEvents = 'auto';

  // Reset the auto-hide timer on each 429 trigger
  if (_toastHideTimer !== null) {
    clearTimeout(_toastHideTimer);
    _toastHideTimer = null;
  }
}

/**
 * Schedules the toast to hide after the minimum display period.
 * Called when rate-limited state clears. If the toast was shown less than
 * 10 seconds ago, it waits the remaining time before hiding.
 */
export function hideRateLimitToast() {
  // Clear any existing hide timer
  if (_toastHideTimer !== null) {
    clearTimeout(_toastHideTimer);
  }
  // Schedule hide after minimum display period
  _toastHideTimer = setTimeout(() => {
    const toast = document.getElementById('rate-limit-toast');
    if (toast) {
      toast.classList.remove('show');
      toast.style.opacity = '0';
      toast.style.pointerEvents = 'none';
    }
    _toastHideTimer = null;
  }, TOAST_MIN_DISPLAY_MS);
}

/**
 * Wraps setTimeout in a Promise for async/await usage.
 *
 * @param {number} ms - Milliseconds to wait
 * @returns {Promise<void>}
 */
export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Extracts the wait duration from a 429 response's Retry-After header.
 *
 * @param {Response} response - The 429 response
 * @returns {number} - Seconds to wait (defaults to 5 if header is absent/invalid)
 */
export function parseRetryAfter(response) {
  const header = response.headers.get('Retry-After');
  if (header === null || header === undefined) {
    return DEFAULT_RETRY_AFTER_SECONDS;
  }
  const value = Number(header);
  if (Number.isFinite(value) && value > 0) {
    return value;
  }
  return DEFAULT_RETRY_AFTER_SECONDS;
}

/**
 * Wraps the browser fetch API with 429 retry/backoff logic.
 *
 * @param {string} url - The request URL
 * @param {RequestInit} [options] - Standard fetch options
 * @returns {Promise<Response>} - The final response (success or exhausted 429)
 */
export async function resilientFetch(url, options = {}) {
  let response = await fetch(url, options);

  if (response.status !== 429) {
    if (_rateLimited) {
      _rateLimited = false;
      hideRateLimitToast();
    }
    return response;
  }

  // First 429 — enter rate-limited state
  if (!_rateLimited) {
    _rateLimited = true;
    showRateLimitToast();
  }

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    const waitSeconds = parseRetryAfter(response);
    console.debug(
      `[resilientFetch] 429 received (attempt ${attempt + 1}/${MAX_RETRIES}), retrying after ${waitSeconds}s`,
    );

    await sleep(waitSeconds * 1000);

    response = await fetch(url, options);

    if (response.status !== 429) {
      if (_rateLimited) {
        _rateLimited = false;
        hideRateLimitToast();
      }
      return response;
    }
  }

  // Exhausted retries — return the final 429 response
  console.debug(
    `[resilientFetch] 429 persisted after ${MAX_RETRIES} retries, returning 429 to caller`,
  );
  return response;
}
