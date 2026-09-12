import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

// Regression tests for Spotify bar visibility.
// The bar must not flash empty — it should only become visible after data loads.
// The OAuth flow must still show the clickable Spotify icon.
describe('spotify bar visibility', () => {
  let document, getNowPlaying;

  // Helper to create JSON:API status response
  function createStatusResponse(isPlaying, artist, song, trackUri) {
    const trackId = trackUri
      ? Array.from(new TextEncoder().encode(trackUri))
          .reduce((hash, byte) => ((hash << 5) - hash + byte) | 0, 0)
          .toString(16)
          .slice(0, 16)
      : null;

    const response = {
      data: {
        type: 'spotify_status',
        id: 'current',
        attributes: { is_playing: isPlaying },
        relationships: {
          track: {
            data: trackId
              ? { type: 'spotify_tracks', id: trackId }
              : null,
          },
        },
      },
    };

    if (trackId) {
      response.included = [
        {
          type: 'spotify_tracks',
          id: trackId,
          attributes: { artist, song },
        },
      ];
    }

    return response;
  }

  // Helper to create JSON:API error response
  function createErrorResponse(status, code, detail) {
    return {
      errors: [{ status: String(status), code, detail }],
    };
  }

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
    document = dom.window.document;

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
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(
            createStatusResponse(true, 'Artist', 'Song', 'spotify:track:123'),
          ),
      }),
    );
    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNowPlaying = module.getNowPlaying;

    await getNowPlaying();

    const bar = document.getElementById('spotify-bar');
    expect(bar.style.display).toBe('flex');
    expect(document.getElementById('spotify-now-playing').innerHTML).toContain(
      'Artist',
    );
  });

  it('shows spotify bar with icon when not playing', async () => {
    setupDOM();
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(createStatusResponse(false, null, null, null)),
      }),
    );
    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNowPlaying = module.getNowPlaying;

    await getNowPlaying();

    const bar = document.getElementById('spotify-bar');
    expect(bar.style.display).toBe('flex');
    expect(document.getElementById('spotify-now-playing').innerHTML).toContain(
      'iconoir-spotify',
    );
    expect(document.getElementById('spotify-now-playing').innerHTML).not.toContain(
      'Artist',
    );
  });

  it('shows spotify bar with oauth link when not authenticated', async () => {
    setupDOM();
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () =>
          Promise.resolve(
            createErrorResponse(
              401,
              'spotify_authorization_required',
              'Spotify authorization missing',
            ),
          ),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            auth_url: 'https://accounts.spotify.com/authorize',
          }),
      });
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
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () =>
          Promise.resolve(
            createErrorResponse(
              401,
              'spotify_authorization_required',
              'Spotify authorization missing',
            ),
          ),
      })
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) });
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
