import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

// Regression tests for Spotify bar visibility.
// The bar must not flash empty — it should only become visible after data loads.
// The OAuth flow must still show the clickable Spotify icon.
describe('spotify bar visibility', () => {
  let document, getNowPlaying;

  function setupDOM() {
    const dom = new JSDOM(`
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
    `, { url: 'http://localhost' });

    global.window = dom.window;
    global.document = dom.window.document;
    global.Image = dom.window.Image;
    document = dom.window.document;

    dom.window.SMPL_CONFIG = {
      transitionInterval: 1000, refreshInterval: 3000,
      host: 'http://localhost', port: '8321',
      displayDate: false, displayClock: false,
      imageZoomEffect: false, imageTransitionType: 'fade',
      plugins: ['spotify']
    };
  }

  beforeEach(() => {
    vi.resetModules();
  });

  it('does not show spotify bar before data loads', async () => {
    setupDOM();
    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNowPlaying = module.getNowPlaying;

    const bar = document.getElementById('spotify-bar');
    expect(bar.style.display).toBe('none');
  });

  it('shows spotify bar with now playing data after fetch', async () => {
    setupDOM();
    global.fetch = vi.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ artist: 'Artist', song: 'Song' })
    }));
    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNowPlaying = module.getNowPlaying;

    await getNowPlaying();

    const bar = document.getElementById('spotify-bar');
    expect(bar.style.display).toBe('flex');
    expect(document.getElementById('spotify-now-playing').innerHTML).toContain('Artist');
  });

  it('shows spotify bar with oauth link when not authenticated', async () => {
    setupDOM();
    global.fetch = vi.fn()
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ auth_url: 'https://accounts.spotify.com/authorize' }) });
    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNowPlaying = module.getNowPlaying;

    await getNowPlaying();

    const bar = document.getElementById('spotify-bar');
    expect(bar.style.display).toBe('flex');
    const link = document.querySelector('#spotify-now-playing a');
    expect(link).toBeTruthy();
    expect(link.href).toContain('accounts.spotify.com');
  });

  it('shows spotify bar with icon on auth error', async () => {
    setupDOM();
    global.fetch = vi.fn()
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({ ok: false });
    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNowPlaying = module.getNowPlaying;

    await getNowPlaying();

    const bar = document.getElementById('spotify-bar');
    expect(bar.style.display).toBe('flex');
  });

  it('shows spotify bar with icon on network error', async () => {
    setupDOM();
    global.fetch = vi.fn(() => Promise.reject(new Error('network')));
    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNowPlaying = module.getNowPlaying;

    await getNowPlaying();

    const bar = document.getElementById('spotify-bar');
    expect(bar.style.display).toBe('flex');
  });
});
