import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('task poll resilience to 429 responses', () => {
  let startTask;

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn());
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});

    document.body.innerHTML = `
      <div class="task-toast" id="task-toast">
        <span id="task-toast-text"></span>
        <div class="task-toast-track">
          <div class="task-toast-bar" id="task-toast-bar"></div>
        </div>
      </div>
    `;

    window.SMPL_CONFIG = {
      host: 'http://localhost',
      port: '8321',
    };

    const mod = await import('../../src/smplfrm/smplfrm/static/main.js');
    startTask = mod.startTask;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.resetModules();
  });

  function makeResponse(status, body = {}, headers = {}) {
    return {
      ok: status >= 200 && status < 300,
      status,
      headers: new Headers(headers),
      json: () => Promise.resolve(body),
    };
  }

  it('task toast preserved with last progress on exhausted 429', async () => {
    let callCount = 0;
    fetch.mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        // startTask POST — success
        return Promise.resolve(
          makeResponse(201, {
            id: 'task-1',
            task_type_label: 'Rescan Library',
            progress: 0,
            status: 'pending',
          }),
        );
      }
      if (callCount === 2) {
        // First poll — returns progress 40%
        return Promise.resolve(
          makeResponse(200, {
            id: 'task-1',
            task_type_label: 'Rescan Library',
            progress: 40,
            status: 'running',
          }),
        );
      }
      // Subsequent polls — all 429 (resilientFetch retries exhaust, returns 429)
      return Promise.resolve(makeResponse(429, {}, { 'Retry-After': '1' }));
    });

    await startTask('rescan_library');

    // First poll tick — gets 40% progress
    await vi.advanceTimersByTimeAsync(1000);

    const text = document.getElementById('task-toast-text');
    const bar = document.getElementById('task-toast-bar');
    expect(text.textContent).toBe('Rescan Library 40%');
    expect(bar.style.width).toBe('40%');

    // Second poll tick — gets 429 (after resilientFetch exhausts retries)
    // resilientFetch will retry 3 times with 1s waits, so advance enough time
    await vi.advanceTimersByTimeAsync(1000); // interval fires
    await vi.advanceTimersByTimeAsync(1000); // retry 1
    await vi.advanceTimersByTimeAsync(1000); // retry 2
    await vi.advanceTimersByTimeAsync(1000); // retry 3

    // Toast should still show last progress (40%)
    expect(text.textContent).toBe('Rescan Library 40%');
    expect(bar.style.width).toBe('40%');
    expect(document.getElementById('task-toast').classList.contains('show')).toBe(true);
  });

  it('polling continues at 1s interval after exhausted retries', async () => {
    let callCount = 0;
    fetch.mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        // startTask POST — success
        return Promise.resolve(
          makeResponse(201, {
            id: 'task-1',
            task_type_label: 'Clear Cache',
            progress: 0,
            status: 'pending',
          }),
        );
      }
      if (callCount === 2) {
        // First poll — 429 (resilientFetch retries exhaust)
        return Promise.resolve(makeResponse(429, {}, { 'Retry-After': '1' }));
      }
      // After 429 retries exhaust, subsequent calls also 429
      // but eventually we want to check that the interval still fires
      return Promise.resolve(makeResponse(429, {}, { 'Retry-After': '1' }));
    });

    await startTask('clear_cache');

    // First poll tick fires at 1s, resilientFetch retries 3 times (1s each)
    await vi.advanceTimersByTimeAsync(1000); // interval fires, fetch returns 429
    await vi.advanceTimersByTimeAsync(1000); // retry 1
    await vi.advanceTimersByTimeAsync(1000); // retry 2
    await vi.advanceTimersByTimeAsync(1000); // retry 3

    // The interval should still be active — record fetch count after first exhausted 429
    const countAfterFirst429 = callCount;

    // Advance another full cycle: 1s interval + 3x1s retries
    await vi.advanceTimersByTimeAsync(1000); // next interval fires
    await vi.advanceTimersByTimeAsync(1000); // retry 1
    await vi.advanceTimersByTimeAsync(1000); // retry 2
    await vi.advanceTimersByTimeAsync(1000); // retry 3

    // More fetch calls should have been made, proving the interval continued
    expect(callCount).toBeGreaterThan(countAfterFirst429);
  });

  it('task toast not dismissed on 429', async () => {
    let callCount = 0;
    fetch.mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        // startTask POST — success
        return Promise.resolve(
          makeResponse(201, {
            id: 'task-1',
            task_type_label: 'Clear Cache',
            progress: 0,
            status: 'pending',
          }),
        );
      }
      // All polls return 429
      return Promise.resolve(makeResponse(429, {}, { 'Retry-After': '1' }));
    });

    await startTask('clear_cache');

    const toast = document.getElementById('task-toast');
    expect(toast.classList.contains('show')).toBe(true);

    // Advance through multiple poll cycles with 429s
    await vi.advanceTimersByTimeAsync(1000); // interval fires
    await vi.advanceTimersByTimeAsync(1000); // retry 1
    await vi.advanceTimersByTimeAsync(1000); // retry 2
    await vi.advanceTimersByTimeAsync(1000); // retry 3

    // Toast should still be visible
    expect(toast.classList.contains('show')).toBe(true);

    // Advance through another cycle
    await vi.advanceTimersByTimeAsync(1000); // next interval
    await vi.advanceTimersByTimeAsync(1000); // retry 1
    await vi.advanceTimersByTimeAsync(1000); // retry 2
    await vi.advanceTimersByTimeAsync(1000); // retry 3

    // Toast should still be visible — never dismissed
    expect(toast.classList.contains('show')).toBe(true);
  });

  it('no error messages shown for 429s', async () => {
    let callCount = 0;
    fetch.mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        // startTask POST — success
        return Promise.resolve(
          makeResponse(201, {
            id: 'task-1',
            task_type_label: 'Clear Cache',
            progress: 0,
            status: 'pending',
          }),
        );
      }
      // All polls return 429
      return Promise.resolve(makeResponse(429, {}, { 'Retry-After': '1' }));
    });

    await startTask('clear_cache');

    // Advance through poll cycles with 429s
    await vi.advanceTimersByTimeAsync(1000); // interval fires
    await vi.advanceTimersByTimeAsync(1000); // retry 1
    await vi.advanceTimersByTimeAsync(1000); // retry 2
    await vi.advanceTimersByTimeAsync(1000); // retry 3

    const text = document.getElementById('task-toast-text');

    // Toast text should not contain error-related messages
    expect(text.textContent).not.toContain('Failed');
    expect(text.textContent).not.toContain('Error');
    expect(text.textContent).not.toContain('error');

    // console.error should not have been called for 429 handling
    // (it may be called for other reasons, so check no 429-related error calls)
    const errorCalls = console.error.mock.calls;
    for (const call of errorCalls) {
      const msg = call.join(' ');
      expect(msg).not.toContain('429');
      expect(msg).not.toContain('Poll failed');
    }
  });
});
