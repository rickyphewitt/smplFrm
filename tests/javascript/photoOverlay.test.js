// @vitest-environment jsdom
import {
  describe,
  it,
  expect,
  beforeAll,
  beforeEach,
  afterEach,
  vi,
} from 'vitest';

/**
 * Photo-change hook.
 *
 * Themes animate the frame overlay on each new photo by targeting
 * `body.photo-changed`. The class is replayed (removed, reflowed, re-added)
 * so a CSS animation restarts every time, and it is replayed only after the
 * photo date is updated so an entrance animation never shows a stale date.
 */

let mod;

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

  window.SMPL_CONFIG = {
    host: 'http://localhost',
    port: '8321',
    transitionInterval: 1000,
    refreshInterval: 3000,
    displayDate: true,
    displayClock: false,
    imageTransitionType: 'fade',
    imageZoomEffect: false,
    plugins: [],
  };

  mod = await import('../../src/smplfrm/smplfrm/static/main.js');
});

function metadataResponse(taken) {
  return {
    ok: true,
    status: 200,
    headers: new Headers(),
    json: () =>
      Promise.resolve({
        data: [{ type: 'images_metadata', id: 'm1', attributes: { taken } }],
      }),
  };
}

describe('markPhotoChanged', () => {
  beforeEach(() => {
    document.body.classList.remove(mod.PHOTO_CHANGED_CLASS);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('adds the photo-changed class to <body>', () => {
    mod.markPhotoChanged();
    expect(document.body.classList.contains('photo-changed')).toBe(true);
  });

  it('removes the class and forces a reflow before re-adding it', () => {
    mod.markPhotoChanged();

    const events = [];
    const remove = vi
      .spyOn(document.body.classList, 'remove')
      .mockImplementation(function (...args) {
        events.push('remove');
        return DOMTokenList.prototype.remove.apply(this, args);
      });
    vi.spyOn(document.body, 'offsetWidth', 'get').mockImplementation(() => {
      events.push('reflow');
      return 0;
    });
    const add = vi
      .spyOn(document.body.classList, 'add')
      .mockImplementation(function (...args) {
        events.push('add');
        return DOMTokenList.prototype.add.apply(this, args);
      });

    mod.markPhotoChanged();

    expect(events).toEqual(['remove', 'reflow', 'add']);
    expect(remove).toHaveBeenCalledWith('photo-changed');
    expect(add).toHaveBeenCalledWith('photo-changed');
    expect(document.body.classList.contains('photo-changed')).toBe(true);
  });
});

describe('refreshPhotoOverlay', () => {
  beforeEach(() => {
    document.body.classList.remove(mod.PHOTO_CHANGED_CLASS);
    document.getElementById('photo-date').replaceChildren();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('signals the change only after the photo date is in place', async () => {
    let resolveFetch;
    global.fetch = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        }),
    );

    const pending = mod.refreshPhotoOverlay('img-1');

    // Metadata has not arrived, so the hook must not have fired yet.
    await vi.waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(document.body.classList.contains('photo-changed')).toBe(false);

    resolveFetch(metadataResponse('2024-11-02T12:00:00Z'));
    await pending;

    const photoDate = document.getElementById('photo-date');
    expect(photoDate.querySelector('i.iconoir-camera')).not.toBeNull();
    expect(photoDate.textContent).toContain('2024');
    expect(document.body.classList.contains('photo-changed')).toBe(true);
  });

  it('still signals the change when the metadata request fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    global.fetch = vi.fn(() =>
      Promise.reject(new TypeError('Failed to fetch')),
    );

    await mod.refreshPhotoOverlay('img-2');

    expect(document.body.classList.contains('photo-changed')).toBe(true);
  });
});
