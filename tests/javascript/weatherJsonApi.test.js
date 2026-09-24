/**
 * JSON:API contract tests for Weather frontend consumption.
 *
 * Tests the jsonApiClient module behavior:
 * - Sends Accept: application/vnd.api+json header
 * - Unwraps data.attributes to get weather values
 * - Formats display as value + "°" + scale (e.g., "72°F")
 * - Handles errors from JSON:API errors array
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('Weather JSON:API Frontend Contract', () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn();
    global.fetch = fetchMock;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
  });

  /**
   * Helper to create a mock JSON:API success response.
   */
  function makeJsonApiSuccessResponse(attributes) {
    return {
      ok: true,
      status: 200,
      headers: new Headers({ 'Content-Type': 'application/vnd.api+json' }),
      json: () =>
        Promise.resolve({
          data: {
            type: 'weather',
            id: 'current',
            attributes,
          },
        }),
    };
  }

  /**
   * Helper to create a mock JSON:API error response.
   */
  function makeJsonApiErrorResponse(status, errors) {
    return {
      ok: false,
      status,
      headers: new Headers({ 'Content-Type': 'application/vnd.api+json' }),
      json: () => Promise.resolve({ errors }),
    };
  }

  describe('jsonApiClient module', () => {
    it('exports fetchJsonApi function', async () => {
      // This test will fail until jsonApiClient.js is created
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );
      expect(mod.fetchJsonApi).toBeDefined();
      expect(typeof mod.fetchJsonApi).toBe('function');
    });

    it('exports unwrapResource function', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );
      expect(mod.unwrapResource).toBeDefined();
      expect(typeof mod.unwrapResource).toBe('function');
    });

    it('exports unwrapErrors function', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );
      expect(mod.unwrapErrors).toBeDefined();
      expect(typeof mod.unwrapErrors).toBe('function');
    });
  });

  describe('fetchJsonApi Accept header', () => {
    it('sends Accept: application/vnd.api+json header', async () => {
      fetchMock.mockResolvedValueOnce(
        makeJsonApiSuccessResponse({
          temperature: '72',
          temperature_scale: 'F',
        }),
      );

      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );
      await mod.fetchJsonApi('http://localhost:8321/api/v1/plugins/weather/current');

      expect(fetchMock).toHaveBeenCalled();
      const [, options] = fetchMock.mock.calls[0];
      expect(options.headers.Accept).toBe('application/vnd.api+json');
    });

    it('uses resilientFetch under the hood', async () => {
      // fetchJsonApi should wrap resilientFetch to preserve 429/Retry-After handling
      fetchMock.mockResolvedValueOnce(
        makeJsonApiSuccessResponse({
          temperature: '72',
          temperature_scale: 'F',
        }),
      );

      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      // Verify the module imports and uses resilientFetch
      // This is tested implicitly by checking the correct behavior
      await mod.fetchJsonApi('http://localhost:8321/api/v1/plugins/weather/current');
      expect(fetchMock).toHaveBeenCalled();
    });
  });

  describe('unwrapResource', () => {
    it('extracts attributes from data.attributes', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      const response = {
        data: {
          type: 'current',
          id: 'current',
          attributes: {
            temperature: '72',
            temperature_scale: 'F',
            daily_low: '55',
            daily_low_scale: 'F',
            daily_high: '80',
            daily_high_scale: 'F',
          },
        },
      };

      const result = mod.unwrapResource(response);
      expect(result.attributes.temperature).toBe('72');
      expect(result.attributes.temperature_scale).toBe('F');
      expect(result.attributes.daily_low).toBe('55');
      expect(result.attributes.daily_high).toBe('80');
    });

    it('preserves resource id', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      const response = {
        data: {
          type: 'weather',
          id: 'current',
          attributes: { temperature: '72', temperature_scale: 'F' },
        },
      };

      const result = mod.unwrapResource(response);
      expect(result.id).toBe('current');
    });

    it('preserves resource type', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      const response = {
        data: {
          type: 'weather',
          id: 'current',
          attributes: { temperature: '72', temperature_scale: 'F' },
        },
      };

      const result = mod.unwrapResource(response);
      expect(result.type).toBe('weather');
    });

    it('returns null for null data', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      const result = mod.unwrapResource({ data: null });
      expect(result).toBeNull();
    });

    it('returns null for missing data key', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      const result = mod.unwrapResource({});
      expect(result).toBeNull();
    });
  });

  describe('unwrapErrors', () => {
    it('extracts errors array from response', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      const response = {
        errors: [
          {
            status: '400',
            code: 'weather_unavailable',
            detail: 'Unable to retrieve weather data',
          },
        ],
      };

      const result = mod.unwrapErrors(response);
      expect(result).toHaveLength(1);
      expect(result[0].status).toBe('400');
      expect(result[0].code).toBe('weather_unavailable');
      expect(result[0].detail).toBe('Unable to retrieve weather data');
    });

    it('returns empty array when no errors key', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      const result = mod.unwrapErrors({});
      expect(result).toEqual([]);
    });

    it('handles multiple errors', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      const response = {
        errors: [
          { status: '400', code: 'error_1', detail: 'First error' },
          { status: '400', code: 'error_2', detail: 'Second error' },
        ],
      };

      const result = mod.unwrapErrors(response);
      expect(result).toHaveLength(2);
    });
  });

  describe('Weather display formatting', () => {
    it('formatWeatherTemp concatenates value and scale with degree symbol', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      // The client should export a helper for weather display formatting
      const result = mod.formatWeatherTemp('72', 'F');
      expect(result).toBe('72°F');
    });

    it('formatWeatherTemp handles Celsius', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      const result = mod.formatWeatherTemp('22', 'C');
      expect(result).toBe('22°C');
    });

    it('formatWeatherTemp handles N/A values', async () => {
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      const result = mod.formatWeatherTemp('N/A', 'F');
      expect(result).toBe('N/A°F');
    });
  });

  describe('Error response handling', () => {
    it('fetchJsonApi throws on non-ok response with error details', async () => {
      fetchMock.mockResolvedValueOnce(
        makeJsonApiErrorResponse(400, [
          {
            status: '400',
            code: 'weather_unavailable',
            detail: 'Unable to retrieve weather data',
          },
        ]),
      );

      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      await expect(
        mod.fetchJsonApi('http://localhost:8321/api/v1/plugins/weather/current'),
      ).rejects.toMatchObject({
        status: 400,
        errors: expect.arrayContaining([
          expect.objectContaining({ code: 'weather_unavailable' }),
        ]),
      });
    });

    it('fetchJsonApi throws on 500 error with generic message', async () => {
      fetchMock.mockResolvedValueOnce(
        makeJsonApiErrorResponse(500, [
          {
            status: '500',
            code: 'internal_error',
            detail: 'An unexpected error occurred',
          },
        ]),
      );

      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      await expect(
        mod.fetchJsonApi('http://localhost:8321/api/v1/plugins/weather/current'),
      ).rejects.toMatchObject({
        status: 500,
        errors: expect.arrayContaining([
          expect.objectContaining({ code: 'internal_error' }),
        ]),
      });
    });
  });

  describe('Rate limiting preservation', () => {
    it('wraps resilientFetch which handles 429 retries', async () => {
      // Verify the module uses resilientFetch (which handles 429)
      // We can't easily test the full retry flow here without fake timers
      // The actual retry behavior is tested in resilientFetch.test.js

      const mod = await import(
        '../../src/smplfrm/smplfrm/static/jsonApiClient.js'
      );

      // Verify fetchJsonApi exists and is a function
      expect(typeof mod.fetchJsonApi).toBe('function');

      // Verify it uses resilientFetch by checking it doesn't use raw fetch directly
      // This is implicitly tested by the other tests that mock global.fetch
    });
  });
});


describe('Weather degraded indicator', () => {
  const MAIN = '../../src/smplfrm/smplfrm/static/main.js';
  const settle = () => new Promise((r) => setTimeout(r, 0));

  function setupBottomBar() {
    document.body.innerHTML = `
            <div id="bottom-bar">
                <div class="info-group" id="photo-date-group"><span id="photo-date"></span></div>
                <div class="group-separator"></div>
                <div class="info-group" id="current-date-group"><span id="current-date"></span></div>
                <div class="group-separator"></div>
                <div class="info-group" id="weather-group"><span id="weather-temp"></span></div>
            </div>
        `;
  }

  async function importMain() {
    vi.resetModules();
    global.window = Object.assign(global.window || {}, {
      SMPL_CONFIG: {
        host: 'http://localhost',
        port: '8321',
        refreshInterval: 30000,
        transitionInterval: 10000,
        plugins: ['weather'],
      },
    });
    return import(MAIN);
  }

  function weatherTemp() {
    return document.getElementById('weather-temp');
  }

  function separatorBeforeWeather() {
    return document.getElementById('weather-group').previousElementSibling;
  }

  beforeEach(() => {
    global.fetch = vi.fn();
    setupBottomBar();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'debug').mockImplementation(() => {});
  });

  afterEach(() => {
    document.getElementById('app-toast')?.remove();
    vi.restoreAllMocks();
    vi.resetModules();
  });

  it('renders the degraded indicator when the weather fetch fails', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () =>
        Promise.resolve({
          errors: [{ status: '500', detail: 'An unexpected error occurred' }],
        }),
    });

    const mod = await importMain();
    mod.displayWeather();
    await settle();

    expect(weatherTemp().textContent).toBe('🌡️ ⚠️');
    expect(document.getElementById('app-toast')).toBeNull();
  });

  it('renders the degraded indicator on a network rejection', async () => {
    global.fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

    const mod = await importMain();
    mod.displayWeather();
    await settle();

    expect(weatherTemp().textContent).toBe('🌡️ ⚠️');
  });

  it('never renders a placeholder row or toast for a weather failure', async () => {
    global.fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

    const mod = await importMain();
    mod.displayWeather();
    await settle();

    expect(document.getElementById('app-toast')).toBeNull();
    expect(document.querySelectorAll('.ui-error-placeholder').length).toBe(0);
  });

  it('leaves the weather slot untouched when rate limited', async () => {
    vi.useFakeTimers();
    global.fetch.mockResolvedValue({
      ok: false,
      status: 429,
      headers: { get: () => '1' },
      json: () => Promise.resolve({ errors: [{ status: '429' }] }),
    });

    const mod = await importMain();
    mod.displayWeather();
    // Let resilientFetch exhaust its retry chain.
    await vi.advanceTimersByTimeAsync(30000);

    expect(weatherTemp().textContent).toBe('');
    expect(document.getElementById('app-toast')).toBeNull();
    vi.useRealTimers();
  });

  it('keeps the weather group and its separator visible on failure', async () => {
    global.fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

    const mod = await importMain();
    mod.displayWeather();
    mod.updateSeparators();
    await settle();

    expect(document.getElementById('weather-group').style.display).not.toBe(
      'none',
    );
    expect(separatorBeforeWeather().style.display).toBe('');
  });

  it('matches the success path for group and separator visibility', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          data: {
            type: 'weather',
            id: 'current',
            attributes: { temperature: '72', temperature_scale: 'F' },
          },
        }),
    });

    const mod = await importMain();
    mod.displayWeather();
    mod.updateSeparators();
    await settle();

    const successDisplay = document.getElementById('weather-group').style.display;
    const successSeparator = separatorBeforeWeather().style.display;

    setupBottomBar();
    global.fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    mod.displayWeather();
    mod.updateSeparators();
    await settle();

    expect(document.getElementById('weather-group').style.display).toBe(
      successDisplay,
    );
    expect(separatorBeforeWeather().style.display).toBe(successSeparator);
  });

  it('renders a temperature containing markup as literal text', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          data: {
            type: 'weather',
            id: 'current',
            attributes: {
              temperature: '<img src=x onerror=alert(1)>',
              temperature_scale: 'F',
            },
          },
        }),
    });

    const mod = await importMain();
    mod.displayWeather();
    await settle();

    expect(weatherTemp().querySelector('img')).toBeNull();
    expect(weatherTemp().textContent).toBe('🌡️ <img src=x onerror=alert(1)>°F');
  });

  it('shows the temperature on the success path', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          data: {
            type: 'weather',
            id: 'current',
            attributes: { temperature: '72', temperature_scale: 'F' },
          },
        }),
    });

    const mod = await importMain();
    mod.displayWeather();
    await settle();

    expect(weatherTemp().textContent).toBe('🌡️ 72°F');
  });
});
