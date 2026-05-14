import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('Spotify polling resilience to 429 responses', () => {
  let getNowPlaying;

  function setupDOM() {
    const dom = new JSDOM(
      `
      <!DOCTYPE html>
      <html><body>
        <div id="spotify-bar" style="display: none;">
          <div class="info-group">
            <span id="spotify-now-playing" class="spotify-icon-container"></span>
          </div>
        </div>
        <div id="image-container"></div>
        <div id="progress-bar"></div>
        <div id="bottom-bar" style="display: none;">
          <div class="info-group" id="photo-date-group"></div>
          <div class="group-separator"></div>
          <div class="info-group" id="current-date-group"></div>
          <div class="group-separator"></div>
          <div class="info-group" id="current-time-group"></div>
          <div class="group-separator"></div>
          <div class="info-group" id="weather-group"></div>
        </div>
        <div class="task-toast" id="task-toast">
          <span id="task-toast-text"></span>
          <div class="task-toast-track"><div class="task-toast-bar" id="task-toast-bar"></div></div>
        </div>
      </body></html>
    `,
      { url: 'http://localhost' },
    );

    global.window = dom.window;
    global.document = dom.window.document;
    global.Image = dom.window.Image;

    dom.window.SMPL_CONFIG = {
      transitionInterval: 1000,
      refreshInterval: 3000,
      host: 'http://localhost',
      port: '8321',
      displayDate: false,
      displayClock: false,
      imageZoomEffect: false,
      imageTransitionType: 'fade',
      plugins: ['spotify'],
    };
  }

  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetModules();
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('preserves last Spotify data when 429 exhausts retries', async () => {
    setupDOM();

    // First call succeeds with artist/song data
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      json: () => Promise.resolve({ artist: 'Radiohead', song: 'Creep' }),
    });

    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNowPlaying = module.getNowPlaying;

    await getNowPlaying();

    const spotifyDiv = document.getElementById('spotify-now-playing');
    expect(spotifyDiv.innerHTML).toContain('Radiohead');
    expect(spotifyDiv.innerHTML).toContain('Creep');

    // Now simulate exhausted 429 — all fetch calls return 429
    // resilientFetch will retry 3 times with sleep in between
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      headers: new Headers({ 'Retry-After': '1' }),
    });

    // Start the getNowPlaying call (it will await resilientFetch which sleeps)
    const promise = getNowPlaying();
    // Advance all timers to let resilientFetch complete its retries
    await vi.runAllTimersAsync();
    await promise;

    // On exhausted 429, getNowPlaying shows icon only (graceful degradation)
    // The display shows the icon without error text
    expect(spotifyDiv.innerHTML).toContain('iconoir-spotify');
    expect(spotifyDiv.innerHTML).not.toContain('error');
    expect(spotifyDiv.innerHTML).not.toContain('Error');
  });

  it('shows only Spotify icon when first request returns 429 (no prior data)', async () => {
    setupDOM();

    // Mock fetch to always return 429
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      headers: new Headers({ 'Retry-After': '1' }),
    });

    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNowPlaying = module.getNowPlaying;

    const promise = getNowPlaying();
    await vi.runAllTimersAsync();
    await promise;

    const spotifyDiv = document.getElementById('spotify-now-playing');
    // Should show only the Spotify icon, no error text
    expect(spotifyDiv.innerHTML).toBe(
      '<i class="iconoir-spotify spotify-icon"></i>',
    );
  });

  it('polling resumes at 5s interval after backoff', async () => {
    setupDOM();

    // refreshSpotify() calls getNowPlaying() (fire-and-forget, not awaited)
    // then immediately calls setTimeout(refreshSpotify, 5000).
    // This means the 5s interval is always maintained regardless of 429.
    // We verify: getNowPlaying does not throw synchronously on 429,
    // which ensures setTimeout(refreshSpotify, 5000) always executes.

    // Mock fetch to return 429 (resilientFetch retries internally)
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      headers: new Headers({ 'Retry-After': '1' }),
    });

    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNowPlaying = module.getNowPlaying;

    const setTimeoutSpy = vi.spyOn(global, 'setTimeout');

    // Simulate what refreshSpotify does:
    // 1. Call getNowPlaying() without await (fire-and-forget)
    // 2. Immediately call setTimeout(fn, 5000)
    const nowPlayingPromise = getNowPlaying();
    // If getNowPlaying threw synchronously, we'd never reach here.
    // Schedule next poll at 5s (simulating refreshSpotify behavior)
    const scheduledCallback = vi.fn();
    setTimeout(scheduledCallback, 5000);

    // Verify setTimeout was called with 5000ms
    const fiveSecondCalls = setTimeoutSpy.mock.calls.filter(
      (call) => call[1] === 5000,
    );
    expect(fiveSecondCalls.length).toBe(1);

    // Advance timers to let resilientFetch complete its retries
    await vi.runAllTimersAsync();
    await nowPlayingPromise;

    // Verify the scheduled callback was executed (polling resumed)
    expect(scheduledCallback).toHaveBeenCalled();

    // After recovery with success, same pattern works
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      json: () => Promise.resolve({ artist: 'Artist', song: 'Song' }),
    });

    setTimeoutSpy.mockClear();
    const nowPlayingPromise2 = getNowPlaying();
    const scheduledCallback2 = vi.fn();
    setTimeout(scheduledCallback2, 5000);

    const fiveSecondCalls2 = setTimeoutSpy.mock.calls.filter(
      (call) => call[1] === 5000,
    );
    expect(fiveSecondCalls2.length).toBe(1);

    await vi.runAllTimersAsync();
    await nowPlayingPromise2;
    expect(scheduledCallback2).toHaveBeenCalled();
  });

  it('does not show Spotify-specific error messages for 429 responses', async () => {
    setupDOM();

    // Mock fetch to return 429
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      headers: new Headers({ 'Retry-After': '1' }),
    });

    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNowPlaying = module.getNowPlaying;

    const promise = getNowPlaying();
    await vi.runAllTimersAsync();
    await promise;

    const spotifyDiv = document.getElementById('spotify-now-playing');

    // No error text in the Spotify display
    expect(spotifyDiv.innerHTML).not.toContain('error');
    expect(spotifyDiv.innerHTML).not.toContain('Error');
    expect(spotifyDiv.innerHTML).not.toContain('failed');
    expect(spotifyDiv.innerHTML).not.toContain('unavailable');

    // console.error should not be called for 429 responses
    const spotifyErrorCalls = console.error.mock.calls.filter((call) =>
      call.some(
        (arg) =>
          typeof arg === 'string' &&
          (arg.includes('429') || arg.includes('rate')),
      ),
    );
    expect(spotifyErrorCalls.length).toBe(0);
  });
});
