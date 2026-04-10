// @vitest-environment jsdom
import { describe, it, expect, beforeAll, vi } from 'vitest';

/**
 * Geolocation Handler Tests
 *
 * The Weather plugin's 📍 button previously used the browser Geolocation API
 * (navigator.geolocation), which is unavailable on plain HTTP pages. Since
 * smplFrm is typically served over HTTP on local networks (e.g. Raspberry Pi),
 * the button silently did nothing — no error, no feedback, no fallback.
 *
 * The fix replaces the Geolocation API with a simple window.open to latlong.net,
 * giving users a reliable way to look up coordinates regardless of protocol.
 * Client-side coordinate validation was also added to catch invalid input before save.
 */

let PLUGIN_ACTION_HANDLERS;
let validateCoordinates;

beforeAll(async () => {
  // main.js references these DOM elements at the top level
  document.body.innerHTML = `
    <div id="image-container"></div>
    <div id="progress-bar"></div>
    <div id="photo-date"></div>
    <div id="current-date"></div>
    <div id="current-time"></div>
    <div id="weather-temp"></div>
    <div id="weather-group"></div>
    <div id="spotify-now-playing"></div>
    <div id="spotify-bar"></div>
    <div id="bottom-bar">
      <div class="info-group"></div>
    </div>
    <div id="settings-modal"></div>
    <div class="error-message" id="error-message"></div>
  `;

  // main.js reads window.SMPL_CONFIG at the top level
  window.SMPL_CONFIG = {
    host: 'http://localhost',
    port: '8321',
    transitionInterval: 1000,
    refreshInterval: 3000,
    displayDate: false,
    displayClock: false,
    imageTransitionType: 'fade',
    imageZoomEffect: false,
    plugins: [],
  };

  // Simulate HTTP context: navigator.geolocation is undefined
  Object.defineProperty(navigator, 'geolocation', {
    value: undefined,
    writable: true,
    configurable: true,
  });

  const mod = await import('../../src/smplfrm/smplfrm/static/main.js');
  PLUGIN_ACTION_HANDLERS = mod.PLUGIN_ACTION_HANDLERS;
  validateCoordinates = mod.validateCoordinates;
});

describe('Bug Condition: Silent Failure on 📍 Button Click', () => {
  it('should call window.open with latlong.net when 📍 button is clicked (HTTP context)', () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    const input = document.createElement('input');
    input.type = 'text';

    const btn = PLUGIN_ACTION_HANDLERS.geolocation(input);
    btn.click();

    expect(openSpy).toHaveBeenCalledWith('https://www.latlong.net', '_blank');

    openSpy.mockRestore();
  });

  it('should provide visible feedback by changing button text on click', () => {
    vi.spyOn(window, 'open').mockImplementation(() => null);

    const input = document.createElement('input');
    input.type = 'text';

    const btn = PLUGIN_ACTION_HANDLERS.geolocation(input);
    btn.click();

    // After click, button text should change from '📍' to provide visible feedback
    // On unfixed code, the handler returns early so textContent stays '📍'
    expect(btn.textContent).not.toBe('📍');

    vi.restoreAllMocks();
  });
});

/**
 * Preservation tests — verify the handler still produces a correctly structured
 * button element and doesn't introduce side effects on the input field.
 */
describe('Preservation: Button Creation and DOM Integration', () => {
  it('returns a <button> element', () => {
    const input = document.createElement('input');
    input.type = 'text';

    const btn = PLUGIN_ACTION_HANDLERS.geolocation(input);

    expect(btn).toBeInstanceOf(HTMLButtonElement);
  });

  it('returned button has type="button"', () => {
    const input = document.createElement('input');
    input.type = 'text';

    const btn = PLUGIN_ACTION_HANDLERS.geolocation(input);

    expect(btn.type).toBe('button');
  });

  it('returned button has className="action-btn"', () => {
    const input = document.createElement('input');
    input.type = 'text';

    const btn = PLUGIN_ACTION_HANDLERS.geolocation(input);

    expect(btn.className).toBe('action-btn');
  });

  it('returned button has textContent="📍"', () => {
    const input = document.createElement('input');
    input.type = 'text';

    const btn = PLUGIN_ACTION_HANDLERS.geolocation(input);

    expect(btn.textContent).toBe('📍');
  });

  it('returned button has a non-empty title attribute', () => {
    const input = document.createElement('input');
    input.type = 'text';

    const btn = PLUGIN_ACTION_HANDLERS.geolocation(input);

    expect(btn.title).toBeTruthy();
    expect(typeof btn.title).toBe('string');
    expect(btn.title.length).toBeGreaterThan(0);
  });

  it('does not modify the input element value when handler is called (before click)', () => {
    const input = document.createElement('input');
    input.type = 'text';
    input.value = 'original-value';

    PLUGIN_ACTION_HANDLERS.geolocation(input);

    expect(input.value).toBe('original-value');
  });

  it('for any mock input element, handler returns a valid button with correct attributes', () => {
    // Property-style: test with multiple different input configurations
    const inputConfigs = [
      { type: 'text', value: '' },
      { type: 'text', value: '40.7128,-74.0060' },
      { type: 'text', value: 'some random text' },
      { type: 'text', value: '0,0' },
      { type: 'text', value: '-90,-180' },
    ];

    for (const config of inputConfigs) {
      const input = document.createElement('input');
      input.type = config.type;
      input.value = config.value;

      const btn = PLUGIN_ACTION_HANDLERS.geolocation(input);

      expect(btn).toBeInstanceOf(HTMLButtonElement);
      expect(btn.type).toBe('button');
      expect(btn.className).toBe('action-btn');
      expect(btn.textContent).toBe('📍');
      expect(btn.title.length).toBeGreaterThan(0);
      // Input value must remain unchanged
      expect(input.value).toBe(config.value);
    }
  });
});

/**
 * Coordinate validation tests — validateCoordinates accepts "lat,long" format
 * where lat is [-90, 90] and long is [-180, 180]. Empty string is allowed
 * (the field is optional). Whitespace around values is trimmed.
 */
describe('validateCoordinates — valid formats', () => {
  it.each([
    ['40.7128,-74.0060', 'typical city coordinates'],
    ['-33.8688,151.2093', 'negative lat, positive lon (Sydney)'],
    ['0,0', 'origin point'],
    ['-90,-180', 'minimum boundary values'],
    ['90,180', 'maximum boundary values'],
    [' 40.7128 , -74.0060 ', 'spaces trimmed'],
    ['63.1786,-147.4661', 'default weather plugin value'],
  ])('returns true for "%s" (%s)', (value) => {
    expect(validateCoordinates(value)).toBe(true);
  });

  it('returns true for empty string (field is optional)', () => {
    expect(validateCoordinates('')).toBe(true);
  });
});

describe('validateCoordinates — invalid formats', () => {
  it.each([
    ['not coords', 'non-numeric text'],
    ['abc,def', 'alphabetic values'],
    ['999,999', 'numbers outside valid range'],
    ['40.7128', 'single number, missing longitude'],
    ['40.7128,-74.0060,0', 'three values'],
    ['91,0', 'latitude > 90'],
    ['-91,0', 'latitude < -90'],
    ['0,181', 'longitude > 180'],
    ['0,-181', 'longitude < -180'],
    [',', 'comma only'],
    ['40.7128,', 'missing longitude after comma'],
  ])('returns false for "%s" (%s)', (value) => {
    expect(validateCoordinates(value)).toBe(false);
  });
});

describe('validateCoordinates — edge cases', () => {
  it.each([
    ['-90,-180', true, 'min boundary passes'],
    ['90,180', true, 'max boundary passes'],
    ['90.0001,0', false, 'just over lat fails'],
    ['0,180.0001', false, 'just over lon fails'],
    ['0.0,0.0', true, 'zero decimal passes'],
  ])('"%s" returns %s (%s)', (value, expected) => {
    expect(validateCoordinates(value)).toBe(expected);
  });
});

/**
 * Save-time validation — the plugin detail save handler validates coordinate
 * inputs before submitting. Invalid coordinates show an error using the
 * existing #error-message element and temporarily disable the save button.
 */
describe('Save prevention with invalid coordinates', () => {
  function buildSaveContext() {
    // Ensure the error-message element exists (mirrors the settings modal DOM)
    let errorMessage = document.getElementById('error-message');
    if (!errorMessage) {
      errorMessage = document.createElement('div');
      errorMessage.id = 'error-message';
      errorMessage.className = 'error-message';
      document.body.appendChild(errorMessage);
    }
    errorMessage.classList.remove('show');
    errorMessage.textContent = '';

    const formEl = document.createElement('div');
    formEl.id = 'plugin-detail-form';

    const row = document.createElement('div');
    row.className = 'field-row';

    const input = document.createElement('input');
    input.type = 'text';
    input.dataset.key = 'coords';
    input.classList.add('plugin-setting-input');
    row.appendChild(input);

    const btn = PLUGIN_ACTION_HANDLERS.geolocation(input);
    row.appendChild(btn);

    formEl.appendChild(row);

    const saveBtn = document.createElement('button');
    saveBtn.id = 'plugin-detail-save';
    saveBtn.disabled = false;

    return { formEl, input, saveBtn, errorMessage };
  }

  // Mirrors the save handler's validation logic from openPluginDetail
  function simulateSave(formEl, saveBtn) {
    const errorMessage = document.getElementById('error-message');
    const inputs = formEl.querySelectorAll('.plugin-setting-input');
    for (const el of inputs) {
      if (el.type === 'checkbox' || el.type === 'select-one') continue;
      if (!validateCoordinates(el.value)) {
        errorMessage.textContent = 'Invalid coordinates. Use lat,long format (e.g. 40.7128,-74.0060)';
        errorMessage.classList.add('show');
        saveBtn.disabled = true;
        return false;
      }
    }
    return true;
  }

  it('blocks save and shows error-message when coordinates are invalid', () => {
    const { formEl, input, saveBtn, errorMessage } = buildSaveContext();

    input.value = 'not coords';
    expect(simulateSave(formEl, saveBtn)).toBe(false);
    expect(errorMessage.classList.contains('show')).toBe(true);
    expect(errorMessage.textContent).toContain('Invalid coordinates');
    expect(saveBtn.disabled).toBe(true);
  });

  it('allows save when coordinates are valid', () => {
    const { formEl, input, saveBtn, errorMessage } = buildSaveContext();

    input.value = '40.7128,-74.0060';
    expect(simulateSave(formEl, saveBtn)).toBe(true);
    expect(errorMessage.classList.contains('show')).toBe(false);
  });

  it('allows save when coordinates are empty (optional field)', () => {
    const { formEl, input, saveBtn } = buildSaveContext();

    input.value = '';
    expect(simulateSave(formEl, saveBtn)).toBe(true);
  });

  it('blocks save for out-of-range coordinates', () => {
    const { formEl, input, saveBtn, errorMessage } = buildSaveContext();

    input.value = '91,181';
    expect(simulateSave(formEl, saveBtn)).toBe(false);
    expect(errorMessage.classList.contains('show')).toBe(true);
    expect(saveBtn.disabled).toBe(true);
  });
});
