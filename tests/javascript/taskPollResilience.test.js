/**
 * Regression tests for task poll resilience.
 *
 * Covers: non-overlapping single-in-flight polling, 3-second normal cadence,
 * 429 backoff without internal retry chains, terminal cancellation, duplicate
 * poll prevention, and concurrent independent pollers.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('task poll resilience', () => {
  let startTask, pollTask;

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
    pollTask = mod.pollTask;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.resetModules();
  });

  // ── helpers ──────────────────────────────────────────────────────────────

  function makeResponse(status, body = {}, headers = {}) {
    return {
      ok: status >= 200 && status < 300,
      status,
      headers: new Headers(headers),
      json: () => Promise.resolve(body),
    };
  }

  function makeTaskResponse(status, taskData = {}) {
    return makeResponse(status, {
      data: {
        type: `${taskData.taskType || 'rescan-library'}-tasks`,
        id: taskData.id || 'task-1',
        attributes: {
          label: taskData.label || 'Rescan Library',
          status: taskData.status || 'pending',
          progress: taskData.progress || 0,
          error: taskData.error || '',
          created: '2026-08-05T10:30:00Z',
        },
      },
    });
  }

  function makeCreateResponse(taskData = {}) {
    return {
      ok: true,
      status: 201,
      headers: new Headers({}),
      json: () =>
        Promise.resolve({
          data: {
            type: `${taskData.taskType || 'clear_cache'}-tasks`,
            id: taskData.id || 'task-1',
            attributes: {
              label: taskData.label || 'Clear Cache',
              status: 'pending',
              progress: 0,
              error: '',
              created: '2026-08-05T10:30:00Z',
            },
          },
        }),
    };
  }

  // ── no overlap when request is in flight ─────────────────────────────────

  it('does not start a second request while one is already in flight', async () => {
    // The first poll resolves only when we release the deferred promise.
    let releasePoll;
    const blockedResponse = new Promise((resolve) => {
      releasePoll = () =>
        resolve(
          makeTaskResponse(200, {
            id: 'task-1',
            status: 'running',
            progress: 20,
          }),
        );
    });

    let pollCallCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        pollCallCount++;
        return blockedResponse;
      }
      // POST /tasks
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');

    // First poll tick fires at 3 s
    await vi.advanceTimersByTimeAsync(3000);
    // Request is now in flight (not resolved yet)

    // Advance well past another poll interval — no second request should start
    await vi.advanceTimersByTimeAsync(10000);

    expect(pollCallCount).toBe(1);

    // Release the in-flight response so teardown is clean
    releasePoll();
    await vi.advanceTimersByTimeAsync(0);
  });

  // ── 3-second cadence after settlement ────────────────────────────────────

  it('schedules the next poll 3 seconds after the prior response settles', async () => {
    const requestTimes = [];

    let callCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        requestTimes.push(Date.now());
        callCount++;
        return Promise.resolve(
          makeTaskResponse(200, {
            id: 'task-1',
            status: 'running',
            progress: callCount * 10,
          }),
        );
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');

    // Fire 4 polling cycles
    for (let i = 0; i < 4; i++) {
      await vi.advanceTimersByTimeAsync(3000);
    }

    // Must have made at least 3 status requests
    expect(requestTimes.length).toBeGreaterThanOrEqual(3);

    // Each gap between consecutive requests must be >= 3 seconds
    for (let i = 1; i < requestTimes.length; i++) {
      expect(requestTimes[i] - requestTimes[i - 1]).toBeGreaterThanOrEqual(
        3000,
      );
    }
  });

  it('does not schedule a poll before 3 seconds have elapsed', async () => {
    let pollCallCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        pollCallCount++;
        return Promise.resolve(
          makeTaskResponse(200, { id: 'task-1', status: 'running', progress: 10 }),
        );
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');

    // Advance only 2 seconds — first poll must not have fired yet
    await vi.advanceTimersByTimeAsync(2000);
    expect(pollCallCount).toBe(0);

    // Advance to 3 seconds — first poll fires
    await vi.advanceTimersByTimeAsync(1000);
    expect(pollCallCount).toBe(1);
  });

  // ── 429 with valid Retry-After ───────────────────────────────────────────

  it('on 429, issues exactly one request per iteration then waits Retry-After', async () => {
    let pollCallCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        pollCallCount++;
        return Promise.resolve(
          makeResponse(429, {}, { 'Retry-After': '10' }),
        );
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');

    // First poll iteration at 3 s
    await vi.advanceTimersByTimeAsync(3000);
    expect(pollCallCount).toBe(1);

    // No retry during the 10-second backoff window
    await vi.advanceTimersByTimeAsync(9000);
    expect(pollCallCount).toBe(1);

    // After the Retry-After delay elapses the next iteration fires
    await vi.advanceTimersByTimeAsync(1000);
    expect(pollCallCount).toBe(2);
  });

  it('on 429, the task toast remains visible with last progress', async () => {
    let callCount = 0;
    fetch.mockImplementation((url) => {
      callCount++;
      if (callCount === 1) {
        // POST /tasks
        return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Rescan Library', taskType: 'rescan_library' }));
      }
      if (callCount === 2) {
        // First poll — 40% progress
        return Promise.resolve(
          makeTaskResponse(200, {
            id: 'task-1',
            label: 'Rescan Library',
            status: 'running',
            progress: 40,
          }),
        );
      }
      // Subsequent polls — 429
      return Promise.resolve(makeResponse(429, {}, { 'Retry-After': '10' }));
    });

    await startTask('rescan_library');

    // First poll settles with 40%
    await vi.advanceTimersByTimeAsync(3000);

    const text = document.getElementById('task-toast-text');
    const bar = document.getElementById('task-toast-bar');
    expect(text.textContent).toBe('Rescan Library 40%');

    // Second iteration fires (3 s after first settled)
    await vi.advanceTimersByTimeAsync(3000);

    // Toast must remain visible with 40% — 429 must not dismiss or update it
    expect(text.textContent).toBe('Rescan Library 40%');
    expect(bar.style.width).toBe('40%');
    expect(
      document.getElementById('task-toast').classList.contains('show'),
    ).toBe(true);
  });

  // ── 429 with missing / invalid Retry-After falls back to 5 seconds ───────

  it('uses 5-second fallback when Retry-After header is missing', async () => {
    let pollCallCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        pollCallCount++;
        return Promise.resolve(makeResponse(429, {}));
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');

    await vi.advanceTimersByTimeAsync(3000); // first poll fires → 429
    expect(pollCallCount).toBe(1);

    // Still within the 5 s fallback window
    await vi.advanceTimersByTimeAsync(4000);
    expect(pollCallCount).toBe(1);

    // After the 5 s fallback the next iteration fires
    await vi.advanceTimersByTimeAsync(1000);
    expect(pollCallCount).toBe(2);
  });

  it('uses 5-second fallback when Retry-After is zero or negative', async () => {
    let pollCallCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        pollCallCount++;
        return Promise.resolve(
          makeResponse(429, {}, { 'Retry-After': '0' }),
        );
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');

    await vi.advanceTimersByTimeAsync(3000);
    expect(pollCallCount).toBe(1);

    await vi.advanceTimersByTimeAsync(4500);
    expect(pollCallCount).toBe(1);

    await vi.advanceTimersByTimeAsync(500);
    expect(pollCallCount).toBe(2);
  });

  // ── completed → no further requests or UI mutation ───────────────────────

  it('stops all future requests after a completed response', async () => {
    let pollCallCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        pollCallCount++;
        return Promise.resolve(
          makeTaskResponse(200, {
            id: 'task-1',
            label: 'Clear Cache',
            status: 'completed',
            progress: 100,
          }),
        );
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');

    // First poll → completed
    await vi.advanceTimersByTimeAsync(3000);
    expect(pollCallCount).toBe(1);

    // Advance well past normal and backoff deadlines — no more requests
    await vi.advanceTimersByTimeAsync(60000);
    expect(pollCallCount).toBe(1);
  });

  it('sets progress bar to 100% when the completed toast is shown', async () => {
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        return Promise.resolve(
          makeTaskResponse(200, {
            id: 'task-1',
            label: 'Clear Cache',
            status: 'completed',
            progress: 100,
          }),
        );
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');
    await vi.advanceTimersByTimeAsync(3000);

    expect(document.getElementById('task-toast-bar').style.width).toBe('100%');
    expect(document.getElementById('task-toast-text').textContent).toBe('Clear Cache Done!');
  });

  it('does not mutate task UI state after completed (stale callback guard)', async () => {
    let pollCallCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        pollCallCount++;
        return Promise.resolve(
          makeTaskResponse(200, {
            id: 'task-1',
            label: 'Clear Cache',
            status: 'completed',
            progress: 100,
          }),
        );
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');
    await vi.advanceTimersByTimeAsync(3000);

    const textAfterComplete =
      document.getElementById('task-toast-text').textContent;

    // After completion, advancing time must not change the text
    await vi.advanceTimersByTimeAsync(60000);
    expect(document.getElementById('task-toast-text').textContent).toBe(
      textAfterComplete,
    );
  });

  // ── failed → no further requests ─────────────────────────────────────────

  it('stops all future requests after a failed response', async () => {
    let pollCallCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        pollCallCount++;
        return Promise.resolve(
          makeTaskResponse(200, {
            id: 'task-1',
            label: 'Clear Cache',
            status: 'failed',
            error: 'disk full',
            progress: 30,
          }),
        );
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');
    await vi.advanceTimersByTimeAsync(3000);
    expect(pollCallCount).toBe(1);

    await vi.advanceTimersByTimeAsync(60000);
    expect(pollCallCount).toBe(1);
  });

  it('retains sanitized failure presentation on failed response', async () => {
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        return Promise.resolve(
          makeTaskResponse(200, {
            id: 'task-1',
            label: 'Clear Cache',
            status: 'failed',
            error: 'disk full',
            progress: 30,
          }),
        );
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');
    await vi.advanceTimersByTimeAsync(3000);

    const text = document.getElementById('task-toast-text');
    expect(text.textContent).toBe('Clear Cache Failed: disk full');
  });

  // ── duplicate poll for same task ID ──────────────────────────────────────

  it('calling startTask twice with the same task id does not create duplicate pollers', async () => {
    let pollCallCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        pollCallCount++;
        return Promise.resolve(
          makeTaskResponse(200, { id: 'task-1', status: 'running', progress: 10 }),
        );
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    // Start polling for the same task id twice
    await startTask('clear_cache');
    await startTask('clear_cache');

    // Advance one poll interval
    await vi.advanceTimersByTimeAsync(3000);

    // Only one in-flight request should have been made
    expect(pollCallCount).toBe(1);
  });

  // ── three concurrent task pollers stay independent and bounded ───────────

  it('three concurrent task ids operate independently with bounded request count', async () => {
    const counts = { 'task-a': 0, 'task-b': 0, 'task-c': 0 };

    fetch.mockImplementation((url) => {
      for (const id of Object.keys(counts)) {
        if (url.includes(`/tasks/${id}`)) {
          counts[id]++;
          return Promise.resolve(
            makeTaskResponse(200, { id, status: 'running', progress: 10 }),
          );
        }
      }
      // POST /tasks
      const taskId = Object.keys(counts).find((id) => counts[id] === 0) || 'task-a';
      return Promise.resolve({
        ok: true,
        status: 201,
        headers: new Headers({}),
        json: () =>
          Promise.resolve({
            data: {
              type: 'clear_cache_tasks',
              id: taskId,
              attributes: {
                label: 'Clear Cache',
                status: 'pending',
                progress: 0,
                error: '',
                created: '2026-08-05T10:30:00Z',
              },
            },
          }),
      });
    });

    // Use pollTask directly to start three independent pollers with known IDs
    pollTask('task-a', 'Task A');
    pollTask('task-b', 'Task B');
    pollTask('task-c', 'Task C');

    // Advance 60 seconds and count total requests
    await vi.advanceTimersByTimeAsync(60000);

    const total = counts['task-a'] + counts['task-b'] + counts['task-c'];

    // At 3 s cadence, each poller can fire at most 20 times in 60 s.
    // Three pollers combined must not exceed 60 requests.
    expect(total).toBeLessThanOrEqual(60);

    // Each poller must have fired at least once
    expect(counts['task-a']).toBeGreaterThan(0);
    expect(counts['task-b']).toBeGreaterThan(0);
    expect(counts['task-c']).toBeGreaterThan(0);
  });

  // ── task poll 429 does not internally retry ───────────────────────────────

  it('a task poll 429 does not trigger an internal retry chain', async () => {
    let pollCallCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        pollCallCount++;
        return Promise.resolve(makeResponse(429, {}, { 'Retry-After': '5' }));
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');

    // First poll fires at 3 s
    await vi.advanceTimersByTimeAsync(3000);
    expect(pollCallCount).toBe(1);

    // Advance within the backoff window — no retry chain should fire
    await vi.advanceTimersByTimeAsync(4000);
    expect(pollCallCount).toBe(1);
  });

  // ── 60-second request count bounds ───────────────────────────────────────

  it('one poller does not exceed 20 status requests in 60 seconds', async () => {
    let pollCallCount = 0;
    fetch.mockImplementation((url) => {
      if (url.includes('/tasks/task-1')) {
        pollCallCount++;
        return Promise.resolve(
          makeTaskResponse(200, { id: 'task-1', status: 'running', progress: 1 }),
        );
      }
      return Promise.resolve(makeCreateResponse({ id: 'task-1', label: 'Clear Cache', taskType: 'clear_cache' }));
    });

    await startTask('clear_cache');
    await vi.advanceTimersByTimeAsync(60000);

    expect(pollCallCount).toBeLessThanOrEqual(20);
  });
});
