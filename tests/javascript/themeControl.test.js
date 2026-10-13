/**
 * Theme control behaviour in the Display tab (#setting-theme).
 *
 * Covers:
 * - Building the control from the themes endpoint, including following
 *   links.next across pages and stopping at the ten-page cap.
 * - Load order independence: the stored theme ends up selected whether the
 *   config request or the themes request settles first, and an immediate
 *   save does not change the stored value.
 * - Degradation on a themes-endpoint failure: the control still shows the
 *   stored theme, the failure surfaces through the view-placeholder error,
 *   and saving other settings still works.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const MAIN = '../../src/smplfrm/smplfrm/static/main.js';

function setupSettingsModal() {
  document.body.innerHTML = `
            <div class="settings-modal open" id="settings-modal" data-config-id="cfg1" data-config-name="custom-test">
                <div class="modal-content">
                    <div class="modal-tabs">
                        <button class="tab-btn active" data-tab="display">Display</button>
                    </div>
                    <div class="tab-content active" id="tab-display">
                        <div class="settings-section">
                            <input type="checkbox" id="setting-date">
                            <input type="checkbox" id="setting-force-date-path">
                            <input type="checkbox" id="setting-clock">
                            <input type="text" id="setting-timezone">
                            <input type="number" id="setting-refresh">
                            <input type="number" id="setting-transition">
                            <input type="number" id="setting-cache-timeout">
                            <input type="checkbox" id="setting-zoom">
                            <select id="setting-transition-type"><option value="fade">fade</option></select>
                            <select id="setting-fill-mode"><option value="cover">cover</option></select>
                            <select id="setting-theme"></select>
                        </div>
                    </div>
                    <div class="modal-actions" id="main-actions">
                        <button id="save-settings">Save Changes</button>
                        <button id="cancel-settings" class="btn-secondary">Cancel</button>
                    </div>
                    <div class="error-message" id="error-message"></div>
                </div>
            </div>
        `;
}

function configResponse(theme = 'classic') {
  return {
    data: {
      type: 'configs',
      id: 'cfg1',
      attributes: {
        name: 'custom-test',
        plugins: [],
        display_date: true,
        display_clock: true,
        image_refresh_interval: 45000,
        image_transition_interval: 15000,
        image_zoom_effect: true,
        image_transition_type: 'fade',
        image_cache_timeout: 3600,
        timezone: 'UTC',
        image_fill_mode: 'cover',
        force_date_from_path: false,
        theme,
      },
    },
  };
}

function themesPage(themes, { next = null } = {}) {
  return {
    data: themes.map((t) => ({
      type: 'themes',
      id: t.id,
      attributes: { label: t.label, description: t.description || '' },
    })),
    links: { next },
    meta: { pagination: { count: themes.length } },
  };
}

function okResponse(body) {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ 'Content-Type': 'application/vnd.api+json' }),
    json: () => Promise.resolve(body),
  };
}

function errorResponse(status, detail) {
  return {
    ok: false,
    status,
    headers: new Headers({ 'Content-Type': 'application/vnd.api+json' }),
    json: () =>
      Promise.resolve({ errors: [{ status: String(status), detail }] }),
  };
}

function placeholders() {
  return document.querySelectorAll('.ui-error-placeholder');
}

describe('theme control (#setting-theme)', () => {
  beforeEach(() => {
    vi.resetModules();
    global.fetch = vi.fn();
    delete global.location;
    global.location = { reload: vi.fn() };
    setupSettingsModal();
    global.window = Object.assign(global.window || {}, {
      SMPL_CONFIG: {
        host: 'http://localhost',
        port: '8321',
        refreshInterval: 30000,
        transitionInterval: 10000,
      },
    });
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('populates the select from a single-page themes response', async () => {
    global.fetch.mockResolvedValueOnce(
      okResponse(
        themesPage([
          { id: 'classic', label: 'Classic' },
          { id: 'gallery', label: 'Gallery' },
        ]),
      ),
    );

    const mod = await import(MAIN);
    await mod.loadThemeOptions();

    const select = document.getElementById('setting-theme');
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toEqual(['classic', 'gallery']);
  });

  it('follows links.next across multiple pages', async () => {
    global.fetch
      .mockResolvedValueOnce(
        okResponse(
          themesPage([{ id: 'classic', label: 'Classic' }], {
            next: 'http://localhost:8321/api/v1/themes?page[number]=2',
          }),
        ),
      )
      .mockResolvedValueOnce(
        okResponse(themesPage([{ id: 'gallery', label: 'Gallery' }])),
      );

    const mod = await import(MAIN);
    await mod.loadThemeOptions();

    const select = document.getElementById('setting-theme');
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toEqual(['classic', 'gallery']);
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it('stops at the ten-page cap on a pathological multi-page response', async () => {
    // Every page links to a next page, forever.
    global.fetch.mockImplementation((url) => {
      const pageMatch = /page\[number\]=(\d+)/.exec(url);
      const page = pageMatch ? parseInt(pageMatch[1], 10) : 1;
      return Promise.resolve(
        okResponse(
          themesPage([{ id: `theme-${page}`, label: `Theme ${page}` }], {
            next: `http://localhost:8321/api/v1/themes?page[number]=${page + 1}`,
          }),
        ),
      );
    });

    const mod = await import(MAIN);
    await mod.loadThemeOptions();

    expect(global.fetch).toHaveBeenCalledTimes(10);
    expect(document.getElementById('setting-theme').options.length).toBe(10);
  });

  describe('load order independence (FR-42)', () => {
    it('selects the stored theme when the config response settles first', async () => {
      global.fetch.mockResolvedValueOnce(okResponse(configResponse('gallery')));
      const mod = await import(MAIN);
      await mod.loadConfig();

      global.fetch.mockResolvedValueOnce(
        okResponse(
          themesPage([
            { id: 'classic', label: 'Classic' },
            { id: 'gallery', label: 'Gallery' },
          ]),
        ),
      );
      await mod.loadThemeOptions();

      expect(document.getElementById('setting-theme').value).toBe('gallery');
    });

    it('selects the stored theme when the themes response settles first', async () => {
      global.fetch.mockResolvedValueOnce(
        okResponse(
          themesPage([
            { id: 'classic', label: 'Classic' },
            { id: 'gallery', label: 'Gallery' },
          ]),
        ),
      );
      const mod = await import(MAIN);
      await mod.loadThemeOptions();

      global.fetch.mockResolvedValueOnce(okResponse(configResponse('gallery')));
      await mod.loadConfig();

      expect(document.getElementById('setting-theme').value).toBe('gallery');
    });

    it('an immediate save after load does not change the stored theme', async () => {
      global.fetch.mockResolvedValueOnce(okResponse(configResponse('gallery')));
      global.fetch.mockResolvedValueOnce(
        okResponse(
          themesPage([
            { id: 'classic', label: 'Classic' },
            { id: 'gallery', label: 'Gallery' },
          ]),
        ),
      );
      const mod = await import(MAIN);
      await Promise.all([mod.loadConfig(), mod.loadThemeOptions()]);

      expect(document.getElementById('setting-theme').value).toBe('gallery');

      global.fetch.mockResolvedValueOnce(okResponse(configResponse('gallery')));
      await mod.saveConfig();

      const putCall = global.fetch.mock.calls.find(
        (call) => call[1]?.method === 'PUT',
      );
      expect(JSON.parse(putCall[1].body).data.attributes.theme).toBe('gallery');
    });
  });

  describe('degraded state on themes-fetch failure (FR-26)', () => {
    it('shows the stored theme as the only option and reports a view error', async () => {
      global.fetch.mockResolvedValueOnce(okResponse(configResponse('gallery')));
      global.fetch.mockResolvedValueOnce(errorResponse(500, 'boom'));

      const mod = await import(MAIN);
      await Promise.all([mod.loadConfig(), mod.loadThemeOptions()]);

      const select = document.getElementById('setting-theme');
      expect(select.options.length).toBe(1);
      expect(select.value).toBe('gallery');
      expect(placeholders().length).toBeGreaterThan(0);
    });

    it('still allows saving other settings after a themes-fetch failure', async () => {
      global.fetch.mockResolvedValueOnce(okResponse(configResponse('gallery')));
      global.fetch.mockResolvedValueOnce(errorResponse(500, 'boom'));

      const mod = await import(MAIN);
      await Promise.all([mod.loadConfig(), mod.loadThemeOptions()]);

      global.fetch.mockResolvedValueOnce(okResponse(configResponse('gallery')));
      const result = await mod.saveConfig();

      expect(result).toBe(true);
    });

    it('renders no empty select even when both the config and themes requests fail', async () => {
      global.fetch.mockResolvedValueOnce(errorResponse(500, 'config down'));
      global.fetch.mockResolvedValueOnce(errorResponse(500, 'themes down'));

      const mod = await import(MAIN);
      await Promise.all([mod.loadConfig(), mod.loadThemeOptions()]);

      const select = document.getElementById('setting-theme');
      expect(select.options.length).toBe(0);
    });

    it('offers the stored theme when the themes failure settles before the config load', async () => {
      // Both requests start together and the themes failure lands first: a
      // server-side rejection returns well before a config read. The stored
      // id is not known at that moment, so the fallback option has to be
      // built when the config finally arrives. A 500 rather than a 429 keeps
      // resilientFetch's retry/sleep chain out of the test.
      let releaseConfig;
      const configDoc = okResponse(configResponse('gallery'));
      global.fetch.mockImplementation((url) => {
        if (String(url).includes('/themes')) {
          return Promise.resolve(errorResponse(500, 'themes down'));
        }
        return new Promise((resolve) => {
          releaseConfig = () => resolve(configDoc);
        });
      });

      const mod = await import(MAIN);
      const settled = Promise.all([mod.loadConfig(), mod.loadThemeOptions()]);
      await new Promise((r) => setTimeout(r, 0));
      releaseConfig();
      await settled;

      const select = document.getElementById('setting-theme');
      expect(select.options.length).toBe(1);
      expect(select.value).toBe('gallery');
    });

    it('still saves unrelated settings when the themes failure settles first', async () => {
      let releaseConfig;
      const configDoc = okResponse(configResponse('gallery'));
      global.fetch.mockImplementation((url) => {
        if (String(url).includes('/themes')) {
          return Promise.resolve(errorResponse(500, 'themes down'));
        }
        return new Promise((resolve) => {
          releaseConfig = () => resolve(configDoc);
        });
      });

      const mod = await import(MAIN);
      const settled = Promise.all([mod.loadConfig(), mod.loadThemeOptions()]);
      await new Promise((r) => setTimeout(r, 0));
      releaseConfig();
      await settled;

      global.fetch.mockImplementation(() =>
        Promise.resolve(okResponse(configResponse('gallery'))),
      );
      const result = await mod.saveConfig();

      expect(result).toBe(true);
      const putCall = global.fetch.mock.calls.find(
        (call) => call[1]?.method === 'PUT',
      );
      // An empty value here would be rejected by the serializer, taking every
      // other setting in the same payload down with it.
      expect(JSON.parse(putCall[1].body).data.attributes.theme).toBe('gallery');
    });
  });
});
