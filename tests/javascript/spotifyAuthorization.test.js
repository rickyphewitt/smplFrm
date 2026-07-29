import { beforeEach, describe, expect, it, vi } from 'vitest';
import { JSDOM } from 'jsdom';

function makeResponse(status, body = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(),
    json: () => Promise.resolve(body),
  };
}

function setupDOM() {
  const dom = new JSDOM(
    `
      <!DOCTYPE html>
      <html><body>
        <div id="spotify-bar" style="display: none;">
          <span id="spotify-now-playing"></span>
        </div>
        <div id="image-container"></div>
        <div id="progress-bar"></div>
        <div id="bottom-bar" style="display: none;">
          <div id="photo-date-group"></div>
          <div class="group-separator"></div>
          <div id="current-date-group"></div>
          <div class="group-separator"></div>
          <div id="current-time-group"></div>
          <div class="group-separator"></div>
          <div id="weather-group"></div>
        </div>
        <div id="task-toast">
          <span id="task-toast-text"></span>
          <div id="task-toast-bar"></div>
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

describe('Spotify authorization recovery', () => {
  beforeEach(() => {
    vi.resetModules();
    setupDOM();
  });

  it('shows a connect link for a missing authorization', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        makeResponse(401, {
          error: 'spotify_authorization_required',
          reason: 'missing',
        }),
      )
      .mockResolvedValueOnce(
        makeResponse(200, {
          auth_url: 'https://accounts.spotify.com/authorize?state=first',
        }),
      );
    const { getNowPlaying } = await import(
      '../../src/smplfrm/smplfrm/static/main.js'
    );

    await getNowPlaying();

    const link = document.querySelector('#spotify-now-playing a');
    expect(link.textContent).toContain('Connect Spotify');
    expect(link.href).toContain('state=first');
    expect(link.classList.contains('spotify-reconnect-link')).toBe(false);
  });

  it('shows a distinct reconnect link for an expired token', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        makeResponse(401, {
          error: 'spotify_authorization_required',
          reason: 'expired',
        }),
      )
      .mockResolvedValueOnce(
        makeResponse(200, {
          auth_url: 'https://accounts.spotify.com/authorize?state=reconnect',
        }),
      );
    const { getNowPlaying } = await import(
      '../../src/smplfrm/smplfrm/static/main.js'
    );

    await getNowPlaying();

    const link = document.querySelector('#spotify-now-playing a');
    expect(link.textContent).toContain('Expired');
    expect(link.textContent).toContain('Reconnect Spotify');
    expect(link.title).toBe(
      'Spotify connection expired - Click to reconnect',
    );
    expect(link.classList.contains('spotify-reconnect-link')).toBe(true);
    expect(
      link.querySelector('.spotify-icon').classList.contains('spotify-expired'),
    ).toBe(true);
  });

  it('does not rotate OAuth state while an authorization link is active', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        makeResponse(401, {
          error: 'spotify_authorization_required',
          reason: 'expired',
        }),
      )
      .mockResolvedValueOnce(
        makeResponse(200, {
          auth_url: 'https://accounts.spotify.com/authorize?state=stable',
        }),
      )
      .mockResolvedValueOnce(
        makeResponse(401, {
          error: 'spotify_authorization_required',
          reason: 'expired',
        }),
      );
    const { getNowPlaying } = await import(
      '../../src/smplfrm/smplfrm/static/main.js'
    );

    await getNowPlaying();
    await getNowPlaying();

    expect(global.fetch).toHaveBeenCalledTimes(3);
    expect(document.querySelector('#spotify-now-playing a').href).toContain(
      'state=stable',
    );
  });

  it('does not initiate OAuth for an unrelated Spotify failure', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce(makeResponse(412));
    const { getNowPlaying } = await import(
      '../../src/smplfrm/smplfrm/static/main.js'
    );

    await getNowPlaying();

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(document.querySelector('#spotify-now-playing a')).toBeNull();
    expect(document.querySelector('.spotify-icon')).not.toBeNull();
  });

  it('transitions from track data to an expired reconnect prompt', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        makeResponse(200, { artist: 'Artist', song: 'Song' }),
      )
      .mockResolvedValueOnce(
        makeResponse(401, {
          error: 'spotify_authorization_required',
          reason: 'expired',
        }),
      )
      .mockResolvedValueOnce(
        makeResponse(200, {
          auth_url: 'https://accounts.spotify.com/authorize?state=new',
        }),
      );
    const { getNowPlaying } = await import(
      '../../src/smplfrm/smplfrm/static/main.js'
    );

    await getNowPlaying();
    expect(document.getElementById('spotify-now-playing').textContent).toContain(
      'Artist - Song',
    );

    await getNowPlaying();
    expect(document.getElementById('spotify-now-playing').textContent).toContain(
      'Reconnect Spotify',
    );
  });
});
