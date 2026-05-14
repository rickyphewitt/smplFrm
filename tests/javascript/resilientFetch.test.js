import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('resilientFetch', () => {
  let resilientFetch,
    parseRetryAfter,
    _rateLimited,
    _setRateLimited,
    MAX_RETRIES,
    DEFAULT_RETRY_AFTER_SECONDS,
    showRateLimitToast,
    hideRateLimitToast;

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn());
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});

    // Provide minimal DOM for toast functions
    document.body.innerHTML = '<div id="rate-limit-toast"></div>';

    const mod = await import(
      '../../src/smplfrm/smplfrm/static/resilientFetch.js'
    );
    resilientFetch = mod.resilientFetch;
    parseRetryAfter = mod.parseRetryAfter;
    MAX_RETRIES = mod.MAX_RETRIES;
    DEFAULT_RETRY_AFTER_SECONDS = mod.DEFAULT_RETRY_AFTER_SECONDS;
    showRateLimitToast = mod.showRateLimitToast;
    hideRateLimitToast = mod.hideRateLimitToast;
    _setRateLimited = mod._setRateLimited;

    // Reset rate-limited state before each test
    _setRateLimited(false);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.resetModules();
  });

  function makeResponse(status, headers = {}, body = '') {
    const headerMap = new Headers(headers);
    return new Response(body, { status, headers: headerMap });
  }

  describe('parseRetryAfter', () => {
    it('returns numeric value from Retry-After header', () => {
      const response = makeResponse(429, { 'Retry-After': '10' });
      expect(parseRetryAfter(response)).toBe(10);
    });

    it('returns default when Retry-After header is missing', () => {
      const response = makeResponse(429);
      expect(parseRetryAfter(response)).toBe(DEFAULT_RETRY_AFTER_SECONDS);
    });

    it('returns default when Retry-After header is non-numeric', () => {
      const response = makeResponse(429, { 'Retry-After': 'invalid' });
      expect(parseRetryAfter(response)).toBe(DEFAULT_RETRY_AFTER_SECONDS);
    });

    it('returns default when Retry-After header is zero', () => {
      const response = makeResponse(429, { 'Retry-After': '0' });
      expect(parseRetryAfter(response)).toBe(DEFAULT_RETRY_AFTER_SECONDS);
    });

    it('returns default when Retry-After header is negative', () => {
      const response = makeResponse(429, { 'Retry-After': '-5' });
      expect(parseRetryAfter(response)).toBe(DEFAULT_RETRY_AFTER_SECONDS);
    });
  });

  describe('non-429 responses', () => {
    it('passes through a 200 response unchanged', async () => {
      const expected = makeResponse(200, { 'X-Custom': 'value' }, 'ok');
      fetch.mockResolvedValueOnce(expected);

      const result = await resilientFetch('/api/test');

      expect(result).toBe(expected);
      expect(result.status).toBe(200);
      expect(result.headers.get('X-Custom')).toBe('value');
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('passes through a 500 response unchanged', async () => {
      const expected = makeResponse(500, {}, 'server error');
      fetch.mockResolvedValueOnce(expected);

      const result = await resilientFetch('/api/test');

      expect(result).toBe(expected);
      expect(result.status).toBe(500);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('passes through a 404 response unchanged', async () => {
      const expected = makeResponse(404, {}, 'not found');
      fetch.mockResolvedValueOnce(expected);

      const result = await resilientFetch('/api/test');

      expect(result).toBe(expected);
      expect(result.status).toBe(404);
      expect(fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('429 retry logic', () => {
    it('retries after waiting the Retry-After duration', async () => {
      const retryResponse = makeResponse(429, { 'Retry-After': '3' });
      const successResponse = makeResponse(200, {}, 'success');

      fetch.mockResolvedValueOnce(retryResponse);
      fetch.mockResolvedValueOnce(successResponse);

      const promise = resilientFetch('/api/test');

      // Advance past the 3-second wait
      await vi.advanceTimersByTimeAsync(3000);

      const result = await promise;

      expect(result).toBe(successResponse);
      expect(result.status).toBe(200);
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it('defaults to 5 seconds when Retry-After is missing', async () => {
      const retryResponse = makeResponse(429);
      const successResponse = makeResponse(200, {}, 'success');

      fetch.mockResolvedValueOnce(retryResponse);
      fetch.mockResolvedValueOnce(successResponse);

      const promise = resilientFetch('/api/test');

      // Should not resolve before 5 seconds
      await vi.advanceTimersByTimeAsync(4999);
      // Advance the remaining time
      await vi.advanceTimersByTimeAsync(1);

      const result = await promise;

      expect(result.status).toBe(200);
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it('defaults to 5 seconds when Retry-After is invalid', async () => {
      const retryResponse = makeResponse(429, { 'Retry-After': 'abc' });
      const successResponse = makeResponse(200, {}, 'success');

      fetch.mockResolvedValueOnce(retryResponse);
      fetch.mockResolvedValueOnce(successResponse);

      const promise = resilientFetch('/api/test');

      await vi.advanceTimersByTimeAsync(5000);

      const result = await promise;

      expect(result.status).toBe(200);
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it('retries max 3 times then returns final 429 (4 total fetch calls)', async () => {
      const retryResponse = makeResponse(429, { 'Retry-After': '1' });

      fetch.mockResolvedValue(retryResponse);

      const promise = resilientFetch('/api/test');

      // Advance through all 3 retry waits (1s each)
      await vi.advanceTimersByTimeAsync(1000);
      await vi.advanceTimersByTimeAsync(1000);
      await vi.advanceTimersByTimeAsync(1000);

      const result = await promise;

      expect(result.status).toBe(429);
      // 1 initial + 3 retries = 4 total
      expect(fetch).toHaveBeenCalledTimes(4);
    });

    it('returns the successful response after retries', async () => {
      const retryResponse = makeResponse(429, { 'Retry-After': '1' });
      const successResponse = makeResponse(200, {}, 'recovered');

      // 429, 429, then 200
      fetch.mockResolvedValueOnce(retryResponse);
      fetch.mockResolvedValueOnce(retryResponse);
      fetch.mockResolvedValueOnce(successResponse);

      const promise = resilientFetch('/api/test');

      await vi.advanceTimersByTimeAsync(1000);
      await vi.advanceTimersByTimeAsync(1000);

      const result = await promise;

      expect(result).toBe(successResponse);
      expect(result.status).toBe(200);
      expect(fetch).toHaveBeenCalledTimes(3);
    });
  });

  describe('console logging', () => {
    it('never calls console.error for 429 responses', async () => {
      const retryResponse = makeResponse(429, { 'Retry-After': '1' });

      fetch.mockResolvedValue(retryResponse);

      const promise = resilientFetch('/api/test');

      await vi.advanceTimersByTimeAsync(1000);
      await vi.advanceTimersByTimeAsync(1000);
      await vi.advanceTimersByTimeAsync(1000);

      await promise;

      expect(console.error).not.toHaveBeenCalled();
    });

    it('calls console.debug with 429 info on each retry', async () => {
      const retryResponse = makeResponse(429, { 'Retry-After': '2' });
      const successResponse = makeResponse(200, {}, 'ok');

      fetch.mockResolvedValueOnce(retryResponse);
      fetch.mockResolvedValueOnce(successResponse);

      const promise = resilientFetch('/api/test');

      await vi.advanceTimersByTimeAsync(2000);

      await promise;

      expect(console.debug).toHaveBeenCalled();
      expect(console.debug.mock.calls[0][0]).toContain('429');
    });
  });

  describe('_rateLimited state', () => {
    it('sets _rateLimited to true on first 429', async () => {
      const retryResponse = makeResponse(429, { 'Retry-After': '1' });

      fetch.mockResolvedValue(retryResponse);

      const promise = resilientFetch('/api/test');

      await vi.advanceTimersByTimeAsync(1000);
      await vi.advanceTimersByTimeAsync(1000);
      await vi.advanceTimersByTimeAsync(1000);

      await promise;

      // Re-import to check module state
      const mod = await import(
        '../../src/smplfrm/smplfrm/static/resilientFetch.js'
      );
      expect(mod._rateLimited).toBe(true);
    });

    it('sets _rateLimited to false on successful response after being rate-limited', async () => {
      const retryResponse = makeResponse(429, { 'Retry-After': '1' });
      const successResponse = makeResponse(200, {}, 'ok');

      fetch.mockResolvedValueOnce(retryResponse);
      fetch.mockResolvedValueOnce(successResponse);

      const promise = resilientFetch('/api/test');

      await vi.advanceTimersByTimeAsync(1000);

      await promise;

      const mod = await import(
        '../../src/smplfrm/smplfrm/static/resilientFetch.js'
      );
      expect(mod._rateLimited).toBe(false);
    });

    it('clears _rateLimited on non-429 response when previously rate-limited', async () => {
      // Set rate-limited state first
      _setRateLimited(true);

      const successResponse = makeResponse(200, {}, 'ok');
      fetch.mockResolvedValueOnce(successResponse);

      await resilientFetch('/api/test');

      const mod = await import(
        '../../src/smplfrm/smplfrm/static/resilientFetch.js'
      );
      expect(mod._rateLimited).toBe(false);
    });
  });
});
