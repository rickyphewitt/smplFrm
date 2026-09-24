/**
 * UI error-presentation standard for smplFrm.
 *
 * Every handled fetch failure in `main.js` passes through `reportError`, which
 * derives the user-facing message, logs it exactly once, and dispatches it to
 * one of five channels. The channel is chosen by *how the failure was
 * triggered*, never by the endpoint or the HTTP status code.
 *
 * ## Channels
 *
 * | Channel     | Trigger context                                            | Presentation                                  |
 * | ----------- | ---------------------------------------------------------- | --------------------------------------------- |
 * | `action`    | Discrete user action outside a form (activate/delete/start) | `#app-toast`, owned by this module            |
 * | `form`      | Submission from a form with an adjacent error region        | `#error-message`, 3s auto-hide, button disable |
 * | `view`      | Failure to populate a view region (list, detail, settings)  | Inline placeholder in the target element      |
 * | `silent`    | Background operation that genuinely retries on a later cycle| Console only, no DOM change                   |
 * | `indicator` | Small persistent kiosk status indicator                     | Caller-supplied `onDegrade` renders in place  |
 *
 * ## Message rules
 *
 * - A `JsonApiError` with a **4xx** status renders `errors[0].detail`. The API
 *   sanitizes 4xx detail text and writes it to be actionable for the operator.
 * - Everything else — 5xx, network `TypeError`, parse failure, programmer
 *   error — renders the call site's static fallback. Raw exception text,
 *   `error.stack`, and 5xx bodies never reach the DOM.
 * - **HTTP 429 is suppressed entirely**: no log, no DOM mutation, no channel
 *   output. `resilientFetch.js` already owns `#rate-limit-toast` and reports
 *   that condition globally, so a per-call-site message would double-report it.
 *
 * ## Logging
 *
 * Exactly one console line per reported failure: `console.error` for `action`,
 * `form`, and `view`; `console.debug` for `silent` and `indicator`. Call sites
 * must not log an error they have already reported.
 *
 * ## Call-site enumeration
 *
 * All 19 logical fetch call sites in `main.js` (22 raw `fetchJsonApi` /
 * `resilientFetch` / `taskPollFetch` invocations). This table is the channel
 * assignment of record for every one of them, including any that do not yet
 * route through this module. A new call site is unassigned until it appears
 * here.
 *
 * | Call site                   | Channel     |
 * | --------------------------- | ----------- |
 * | preset activate             | `action`    |
 * | preset delete               | `action`    |
 * | task delete                 | `action`    |
 * | `startTask`                 | `action`    |
 * | `saveConfig`                | `form`      |
 * | plugin settings save        | `form`      |
 * | preset inline field edit    | `form`      |
 * | `loadConfig`                | `view`      |
 * | `loadPlugins`               | `view`      |
 * | `openPluginDetail`          | `view`      |
 * | `loadPresets`               | `view`      |
 * | `loadTasks`                 | `view`      |
 * | `refillQueue`               | `silent`    |
 * | `requestPreload`            | `silent`    |
 * | `displayMetadata`           | `silent`    |
 * | `pollTask`                  | `silent`    |
 * | `displayWeather`            | `indicator` |
 * | `getNowPlaying`             | `indicator` |
 * | `showSpotifyAuthorization`  | `indicator` |
 *
 * `pollTask` is the one site that does not call `reportError`. It already meets
 * the silent contract — console only, no DOM change on failure — and its
 * scheduling, terminal-state, and stale-continuation logic owns the task toast,
 * so routing it through the reporter would couple error presentation to task
 * state for no behavioral gain.
 *
 * The global `unhandledrejection` listener installed by
 * `installGlobalRejectionHandler` reports through `action`. It is a safety net,
 * not a substitute for call-site handling.
 *
 * This module imports `JsonApiError` only. It deliberately does not import
 * `resilientFetch.js`: rate-limit presentation stays inside the fetch layer,
 * application error presentation sits above it.
 */

import { JsonApiError } from './jsonApiClient.js';

/** HTTP status already reported globally by `resilientFetch.js`. */
const RATE_LIMIT_STATUS = 429;

/**
 * Action-toast display window, in milliseconds. Long enough to read a short
 * sentence on a wall-mounted frame, short enough not to linger over the photo.
 */
export const ACTION_TOAST_DURATION_MS = 5000;

/**
 * Form-error display window, in milliseconds. Matches the timing the settings
 * form's `#error-message` region uses.
 */
export const FORM_ERROR_DURATION_MS = 3000;

/**
 * Class stamped on every failure placeholder this module renders. Callers use
 * it to find and remove those nodes on a recovery path without touching
 * surrounding content.
 */
export const ERROR_PLACEHOLDER_CLASS = 'ui-error-placeholder';

const LOG_PREFIX = '[uiErrors]';

let _actionToastHideTimer = null;
let _formErrorTimer = null;
let _rejectionHandler = null;

/**
 * Derives the user-facing message for a caught error.
 * Pure — no DOM access, no logging.
 *
 * @param {Error} error - The caught error
 * @param {string} fallback - Static message used when no safe detail exists
 * @returns {string} - errors[0].detail for a 4xx JsonApiError, else the fallback
 */
export function deriveErrorMessage(error, fallback) {
  if (!(error instanceof JsonApiError)) {
    return fallback;
  }
  if (!(error.status >= 400 && error.status < 500)) {
    return fallback;
  }
  const detail = error.errors?.[0]?.detail;
  if (typeof detail !== 'string' || detail.trim() === '') {
    return fallback;
  }
  return detail;
}

/**
 * True when the error is already reported globally and must not produce
 * per-call-site UI (HTTP 429, handled by `resilientFetch.js`).
 *
 * @param {Error} error - The caught error
 * @returns {boolean}
 */
export function isSuppressed(error) {
  return error instanceof JsonApiError && error.status === RATE_LIMIT_STATUS;
}

/**
 * Shows the action toast, creating `#app-toast` on first use.
 *
 * Follows the dynamic-creation pattern of `showRateLimitToast` in
 * `resilientFetch.js` so no template or CSS change is required. Stacked above
 * `#rate-limit-toast` (80px) and `#task-toast` (20px) so all three can be
 * visible at once. Never touches the task-toast elements.
 *
 * @param {string} message - Already-derived, user-facing message
 */
export function showActionToast(message) {
  let toast = document.querySelector('#app-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'app-toast';
    toast.className = 'app-toast';
    Object.assign(toast.style, {
      position: 'fixed',
      bottom: '140px',
      right: '20px',
      background: 'rgba(45, 55, 72, 0.92)',
      color: '#fed7d7',
      padding: '12px 18px',
      borderRadius: '8px',
      fontSize: '13px',
      zIndex: '10001',
      opacity: '0',
      pointerEvents: 'none',
      transition: 'opacity 0.3s',
      minWidth: '180px',
    });
    document.body.appendChild(toast);
  }

  toast.textContent = message;
  toast.classList.add('show');
  toast.style.opacity = '1';
  toast.style.pointerEvents = 'auto';

  if (_actionToastHideTimer !== null) {
    clearTimeout(_actionToastHideTimer);
  }
  _actionToastHideTimer = setTimeout(() => {
    toast.classList.remove('show');
    toast.style.opacity = '0';
    toast.style.pointerEvents = 'none';
    _actionToastHideTimer = null;
  }, ACTION_TOAST_DURATION_MS);
}

/**
 * Shows the inline form error in `#error-message`.
 *
 * Shows the region, disables the submit button for the display window, then
 * restores both — the behavior the settings form relies on.
 *
 * @param {string} message - Already-derived, user-facing message
 * @param {Object} [options]
 * @param {Element} [options.disable] - Submit button to disable for the window
 * @returns {boolean} - False when `#error-message` is absent
 */
export function showFormError(message, { disable } = {}) {
  const region = document.querySelector('#error-message');
  if (!region) {
    return false;
  }

  region.textContent = message;
  region.classList.add('show');
  if (disable) {
    disable.disabled = true;
  }

  if (_formErrorTimer !== null) {
    clearTimeout(_formErrorTimer);
  }
  _formErrorTimer = setTimeout(() => {
    region.classList.remove('show');
    if (disable) {
      disable.disabled = false;
    }
    _formErrorTimer = null;
  }, FORM_ERROR_DURATION_MS);

  return true;
}

/**
 * Renders an inline placeholder into a view region.
 *
 * For a table section the placeholder replaces the rows, since a list that
 * failed to load has no rows worth keeping. For any other element it is
 * inserted without removing existing children, so a failed load does not
 * destroy form inputs the recovery path needs.
 *
 * Built with `createElement` and `textContent` — never `innerHTML` — so a
 * malformed or hostile `detail` value cannot inject markup.
 *
 * @param {Element} target - Table section or container element
 * @param {string} message - Already-derived, user-facing message
 * @param {number} [colspan] - Column count for the table-section case
 * @returns {boolean} - False when the target is absent
 */
export function showViewPlaceholder(target, message, colspan = 1) {
  if (!target) {
    return false;
  }

  clearViewPlaceholder(target);

  const tag = target.tagName ? target.tagName.toUpperCase() : '';
  const isTableSection = tag === 'TBODY' || tag === 'THEAD' || tag === 'TABLE';

  if (isTableSection) {
    const row = document.createElement('tr');
    row.className = ERROR_PLACEHOLDER_CLASS;
    const cell = document.createElement('td');
    cell.setAttribute('colspan', String(colspan));
    cell.textContent = message;
    row.appendChild(cell);
    target.replaceChildren(row);
    return true;
  }

  const placeholder = document.createElement('div');
  placeholder.className = ERROR_PLACEHOLDER_CLASS;
  placeholder.textContent = message;
  target.prepend(placeholder);
  return true;
}

/**
 * Removes any placeholder this module rendered into the target, leaving all
 * other content intact. Used by recovery paths (for example a successful
 * `loadConfig` after a failed one).
 *
 * @param {Element} target - The element previously passed to showViewPlaceholder
 */
export function clearViewPlaceholder(target) {
  if (!target || typeof target.querySelectorAll !== 'function') {
    return;
  }
  target
    .querySelectorAll(`.${ERROR_PLACEHOLDER_CLASS}`)
    .forEach((node) => node.remove());
}

/**
 * Single entry point for every handled failure.
 *
 * Suppresses 429, derives the message, logs exactly once, then dispatches to
 * the channel renderer. Never throws: a missing target degrades to logging.
 *
 * @param {Error} error - The caught error
 * @param {Object} options
 * @param {'action'|'form'|'view'|'silent'|'indicator'} options.channel
 * @param {string} options.fallback - Static message for the non-4xx case
 * @param {Element} [options.target] - Required for the 'view' channel
 * @param {Element} [options.disable] - Optional submit button for 'form'
 * @param {number} [options.colspan] - Column count for 'view'
 * @param {Function} [options.onDegrade] - Invoked for 'indicator'
 * @returns {string|null} - The derived message, or null when suppressed
 */
export function reportError(error, options = {}) {
  if (isSuppressed(error)) {
    return null;
  }

  const { channel, fallback, target, disable, colspan, onDegrade } = options;
  const message = deriveErrorMessage(error, fallback);
  const quiet = channel === 'silent' || channel === 'indicator';

  if (quiet) {
    console.debug(`${LOG_PREFIX} ${channel}: ${message}`, error);
  } else {
    console.error(`${LOG_PREFIX} ${channel}: ${message}`, error);
  }

  switch (channel) {
    case 'action':
      showActionToast(message);
      break;
    case 'form':
      showFormError(message, { disable });
      break;
    case 'view':
      showViewPlaceholder(target, message, colspan);
      break;
    case 'indicator':
      if (typeof onDegrade === 'function') {
        onDegrade(message);
      }
      break;
    case 'silent':
      break;
    default:
      // Unassigned channel: the log above is the only output, and the missing
      // assignment is visible in review against the table in this docblock.
      break;
  }

  return message;
}

/**
 * Registers the global `unhandledrejection` safety net. Idempotent.
 *
 * Reports through the action channel with a generic fallback so an unhandled
 * rejection is never silent, while still surfacing a 4xx detail when present.
 */
export function installGlobalRejectionHandler() {
  if (_rejectionHandler !== null) {
    return;
  }

  _rejectionHandler = (event) => {
    reportError(event.reason, {
      channel: 'action',
      fallback: 'Something went wrong. Please try again.',
    });
  };

  window.addEventListener('unhandledrejection', _rejectionHandler);
}

/**
 * Removes the global rejection listener. Used for testing, where the module is
 * re-imported against a persistent `window` and listeners would otherwise
 * accumulate across cases. Mirrors the `_setRateLimited` seam in
 * `resilientFetch.js`.
 */
export function _resetGlobalRejectionHandler() {
  if (_rejectionHandler !== null) {
    window.removeEventListener('unhandledrejection', _rejectionHandler);
    _rejectionHandler = null;
  }
}
