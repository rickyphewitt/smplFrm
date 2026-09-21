import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';

function setupBottomBar() {
  document.body.innerHTML = `
        <div id="bottom-bar">
            <div class="info-group" id="photo-date-group"><span id="photo-date"></span></div>
            <div class="group-separator"></div>
            <div class="info-group" id="current-date-group"><span id="current-date"></span></div>
            <div class="group-separator"></div>
            <div class="info-group" id="current-time-group"><span id="current-time"></span></div>
            <div class="group-separator"></div>
            <div class="info-group" id="weather-group"><span id="weather-temp"></span></div>
        </div>
    `;
}

function updateSeparators() {
  const bottomBar = document.getElementById('bottom-bar');
  const groups = bottomBar.querySelectorAll('.info-group');
  const separators = bottomBar.querySelectorAll('.group-separator');

  separators.forEach((sep) => (sep.style.display = 'none'));

  const visibleGroups = Array.from(groups).filter(
    (g) => g.style.display !== 'none',
  );
  visibleGroups.forEach((group, index) => {
    if (index < visibleGroups.length - 1) {
      const sep = group.nextElementSibling;
      if (sep && sep.classList.contains('group-separator')) {
        sep.style.display = '';
      }
    }
  });
}

describe('Config API Integration', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
    delete global.location;
    global.location = { reload: vi.fn() };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should call GET API to load config', async () => {
    const mockConfig = {
      id: 'test123',
      display_date: true,
      display_clock: false,
      image_refresh_interval: 45000,
      image_transition_interval: 15000,
      image_zoom_effect: true,
      image_transition_type: 'fade',
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockConfig,
    });

    const response = await fetch(
      'http://localhost:8321/api/v1/configs/test123',
    );
    const config = await response.json();

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8321/api/v1/configs/test123',
    );
    expect(config.display_date).toBe(true);
    expect(config.display_clock).toBe(false);
    expect(config.image_refresh_interval).toBe(45000);
  });

  it('should call PUT API to save config', async () => {
    const configData = {
      display_date: false,
      display_clock: true,
      image_refresh_interval: 60000,
      image_transition_interval: 20000,
      image_zoom_effect: false,
      image_transition_type: 'zoom',
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => configData,
    });

    await fetch('http://localhost:8321/api/v1/configs/test123', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(configData),
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8321/api/v1/configs/test123',
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(configData),
      },
    );
  });

  it('should handle save error and show error message', async () => {
    vi.useFakeTimers();

    document.body.innerHTML =
      '<div id="error-message" class="error-message"></div>';
    const errorMessage = document.getElementById('error-message');

    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    try {
      const response = await fetch(
        'http://localhost:8321/api/v1/configs/test123',
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        },
      );

      if (!response.ok) {
        errorMessage.textContent = 'Failed to save settings. Please try again.';
        errorMessage.classList.add('show');

        setTimeout(() => {
          errorMessage.classList.remove('show');
        }, 3000);
      }
    } catch (error) {
      // Error handled
    }

    expect(errorMessage.textContent).toBe(
      'Failed to save settings. Please try again.',
    );
    expect(errorMessage.classList.contains('show')).toBe(true);

    vi.advanceTimersByTime(3000);
    expect(errorMessage.classList.contains('show')).toBe(false);

    vi.useRealTimers();
  });

  it('should keep modal open after successful save', async () => {
    document.body.innerHTML = `
            <div id="settings-modal" data-config-id="test123" data-changes-saved="false">
                <button id="cancel-settings" class="btn btn-secondary">Cancel</button>
            </div>
        `;

    const modal = document.getElementById('settings-modal');
    const cancelBtn = document.getElementById('cancel-settings');

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    const response = await fetch(
      'http://localhost:8321/api/v1/configs/test123',
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      },
    );

    if (response.ok) {
      modal.dataset.changesSaved = 'true';
      cancelBtn.textContent = 'Reload Now';
      cancelBtn.classList.remove('btn-secondary');
      cancelBtn.classList.add('btn-primary');
    }

    expect(modal.dataset.changesSaved).toBe('true');
    expect(cancelBtn.textContent).toBe('Reload Now');
    expect(cancelBtn.classList.contains('btn-primary')).toBe(true);
    expect(cancelBtn.classList.contains('btn-secondary')).toBe(false);
  });

  it('should reload page when closing modal after save', () => {
    document.body.innerHTML = `
            <div id="settings-modal" data-changes-saved="true" class="open"></div>
        `;

    const modal = document.getElementById('settings-modal');
    const changesSaved = modal.dataset.changesSaved === 'true';

    if (changesSaved) {
      location.reload();
    } else {
      modal.classList.remove('open');
    }

    expect(location.reload).toHaveBeenCalled();
  });

  it('should not reload page when closing modal without save', () => {
    document.body.innerHTML = `
            <div id="settings-modal" data-changes-saved="false" class="open"></div>
        `;

    const modal = document.getElementById('settings-modal');
    const changesSaved = modal.dataset.changesSaved === 'true';

    if (changesSaved) {
      location.reload();
    } else {
      modal.classList.remove('open');
    }

    expect(location.reload).not.toHaveBeenCalled();
    expect(modal.classList.contains('open')).toBe(false);
  });
});

describe('Bottom Bar Visibility', () => {
  beforeEach(() => {
    setupBottomBar();
  });

  it('should hide photo date group when displayDate is false', () => {
    document.getElementById('photo-date-group').style.display = 'none';
    updateSeparators();

    expect(document.getElementById('photo-date-group').style.display).toBe(
      'none',
    );
  });

  it('should hide clock groups when displayClock is false', () => {
    document.getElementById('current-date-group').style.display = 'none';
    document.getElementById('current-time-group').style.display = 'none';
    updateSeparators();

    expect(document.getElementById('current-date-group').style.display).toBe(
      'none',
    );
    expect(document.getElementById('current-time-group').style.display).toBe(
      'none',
    );
  });

  it('should hide separators between hidden groups', () => {
    document.getElementById('photo-date-group').style.display = 'none';
    document.getElementById('current-date-group').style.display = 'none';
    document.getElementById('current-time-group').style.display = 'none';
    updateSeparators();

    const separators = document.querySelectorAll('.group-separator');
    const visibleSeps = Array.from(separators).filter(
      (s) => s.style.display !== 'none',
    );

    // Only weather group visible, no separators needed
    expect(visibleSeps.length).toBe(0);
  });

  it('should show separator only between visible groups', () => {
    document.getElementById('current-date-group').style.display = 'none';
    document.getElementById('current-time-group').style.display = 'none';
    updateSeparators();

    const separators = document.querySelectorAll('.group-separator');
    const visibleSeps = Array.from(separators).filter(
      (s) => s.style.display !== 'none',
    );

    // photo-date and weather visible, one separator between them
    expect(visibleSeps.length).toBe(1);
  });

  it('should show all separators when all groups visible', () => {
    updateSeparators();

    const separators = document.querySelectorAll('.group-separator');
    const visibleSeps = Array.from(separators).filter(
      (s) => s.style.display !== 'none',
    );

    expect(visibleSeps.length).toBe(3);
  });
});

describe('Library Maintenance Tasks', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should POST to create a task with JSON:API format', async () => {
    const mockResponse = {
      data: {
        type: 'clear_cache_tasks',
        id: 'task123',
        attributes: {
          label: 'Clear Cache',
          status: 'pending',
          progress: 0,
          error: '',
          created: '2026-08-05T10:30:00Z',
        },
      },
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const response = await fetch('http://localhost:8321/api/v1/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/vnd.api+json' },
      body: JSON.stringify({
        data: {
          type: 'clear_cache_tasks',
          attributes: {},
        },
      }),
    });
    const data = await response.json();

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8321/api/v1/tasks',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(data.data.type).toBe('clear_cache_tasks');
    expect(data.data.attributes.status).toBe('pending');
  });

  it('should GET to poll task status with JSON:API format', async () => {
    const mockResponse = {
      data: {
        type: 'rescan_library_tasks',
        id: 'task123',
        attributes: {
          label: 'Rescan Library',
          status: 'running',
          progress: 50,
          error: '',
          created: '2026-08-05T10:30:00Z',
        },
      },
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const response = await fetch('http://localhost:8321/api/v1/tasks/task123');
    const data = await response.json();

    expect(data.data.attributes.status).toBe('running');
    expect(data.data.attributes.progress).toBe(50);
  });

  it('should handle task creation failure', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({
        errors: [
          {
            status: '409',
            code: 'conflict',
            detail: 'A conflicting task already exists',
          },
        ],
      }),
    });

    const response = await fetch('http://localhost:8321/api/v1/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/vnd.api+json' },
      body: JSON.stringify({
        data: {
          type: 'invalid-type',
          attributes: {},
        },
      }),
    });

    expect(response.ok).toBe(false);
  });
});

describe('Task Progress UI', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
    document.body.innerHTML = `
            <div class="task-toast" id="task-toast">
                <span id="task-toast-text">Running...</span>
                <div class="task-toast-track">
                    <div class="task-toast-bar" id="task-toast-bar"></div>
                </div>
            </div>
        `;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should show toast when task starts', async () => {
    const toast = document.getElementById('task-toast');
    toast.classList.add('show');

    expect(toast.classList.contains('show')).toBe(true);
  });

  it('should update progress bar width from task response', () => {
    const bar = document.getElementById('task-toast-bar');
    const text = document.getElementById('task-toast-text');

    // Simulate poll response
    const task = { status: 'running', progress: 75, error: '' };
    bar.style.width = `${task.progress}%`;
    text.textContent = `Running... ${task.progress}%`;

    expect(bar.style.width).toBe('75%');
    expect(text.textContent).toBe('Running... 75%');
  });

  it('should show Done on completion', () => {
    const text = document.getElementById('task-toast-text');
    const task = { status: 'completed', progress: 100, error: '' };

    text.textContent =
      task.status === 'completed' ? 'Done!' : `Failed: ${task.error}`;

    expect(text.textContent).toBe('Done!');
  });

  it('should show error on failure', () => {
    const text = document.getElementById('task-toast-text');
    const task = { status: 'failed', progress: 30, error: 'Connection lost' };

    text.textContent =
      task.status === 'completed' ? 'Done!' : `Failed: ${task.error}`;

    expect(text.textContent).toBe('Failed: Connection lost');
  });

  it('should hide toast after completion delay', () => {
    vi.useFakeTimers();
    const toast = document.getElementById('task-toast');
    toast.classList.add('show');

    setTimeout(() => toast.classList.remove('show'), 3000);

    vi.advanceTimersByTime(3000);
    expect(toast.classList.contains('show')).toBe(false);

    vi.useRealTimers();
  });
});


describe('Settings load failure and save guard', () => {
  const MAIN = '../../src/smplfrm/smplfrm/static/main.js';

  function setupSettingsModal() {
    document.body.innerHTML = `
            <div class="settings-modal open" id="settings-modal" data-config-id="cfg1" data-config-name="custom-test">
                <div class="modal-content">
                    <div class="modal-tabs">
                        <button class="tab-btn active" data-tab="display">Display</button>
                        <button class="tab-btn" data-tab="tasks">Tasks</button>
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
                        </div>
                    </div>
                    <div class="tab-content" id="tab-tasks">
                        <div class="settings-section">
                            <table><tbody id="task-list-body"></tbody></table>
                        </div>
                        <div class="task-pagination">
                            <button id="task-page-prev"></button>
                            <span id="task-page-info"></span>
                            <button id="task-page-next"></button>
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

  function configResponse(overrides = {}) {
    return {
      data: {
        type: 'configs',
        id: 'cfg1',
        attributes: {
          name: 'custom-test',
          plugins: ['weather'],
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
          ...overrides,
        },
      },
    };
  }

  function okResponse(body) {
    return { ok: true, status: 200, json: () => Promise.resolve(body) };
  }

  function errorResponse(status, detail) {
    return {
      ok: false,
      status,
      json: () => Promise.resolve({ errors: [{ status: String(status), detail }] }),
    };
  }

  function placeholders() {
    return document.querySelectorAll('.ui-error-placeholder');
  }

  beforeEach(() => {
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

  it('renders an inline placeholder in the settings body when the config fetch fails', async () => {
    global.fetch.mockResolvedValueOnce(errorResponse(500, 'Internal error'));

    const { loadConfig } = await import(MAIN);
    await loadConfig();

    expect(placeholders().length).toBe(1);
    expect(document.getElementById('tab-display').textContent).toContain(
      'Failed to load settings',
    );
  });

  it('disables the save button and marks the config unloaded on failure', async () => {
    global.fetch.mockResolvedValueOnce(errorResponse(500, 'Internal error'));

    const { loadConfig } = await import(MAIN);
    await loadConfig();

    expect(document.getElementById('save-settings').disabled).toBe(true);
    expect(
      document.getElementById('settings-modal').dataset.configLoaded,
    ).toBe('false');
  });

  it('enables the save button and marks the config loaded on success', async () => {
    global.fetch.mockResolvedValueOnce(okResponse(configResponse()));

    const { loadConfig } = await import(MAIN);
    await loadConfig();

    expect(document.getElementById('save-settings').disabled).toBe(false);
    expect(
      document.getElementById('settings-modal').dataset.configLoaded,
    ).toBe('true');
    expect(placeholders().length).toBe(0);
  });

  it('leaves the modal open and other tabs working after a failed load', async () => {
    global.fetch.mockResolvedValueOnce(errorResponse(503, 'Unavailable'));

    const mod = await import(MAIN);
    await mod.loadConfig();

    expect(
      document.getElementById('settings-modal').classList.contains('open'),
    ).toBe(true);

    global.fetch.mockResolvedValueOnce(
      okResponse({
        data: [
          {
            type: 'rescan_library_tasks',
            id: 't1',
            attributes: {
              label: 'Rescan Library',
              status: 'completed',
              progress: 100,
              created: '2026-08-05T10:30:00Z',
            },
          },
        ],
        meta: { pagination: { pages: 1, page: 1 } },
        links: {},
      }),
    );
    await mod.loadTasks();

    expect(
      document.getElementById('task-list-body').querySelectorAll('tr').length,
    ).toBe(1);
  });

  it('issues no request at all when saving after a failed load', async () => {
    global.fetch.mockResolvedValueOnce(errorResponse(500, 'Internal error'));

    const mod = await import(MAIN);
    await mod.loadConfig();
    const callsAfterLoad = global.fetch.mock.calls.length;

    const result = await mod.saveConfig();

    expect(global.fetch.mock.calls.length).toBe(callsAfterLoad);
    const bodies = global.fetch.mock.calls
      .map((call) => call[1]?.body)
      .filter(Boolean);
    expect(bodies.some((body) => body.includes('"plugins":[]'))).toBe(false);
    expect(bodies.some((body) => body.includes('"is_active":true'))).toBe(false);
    expect(
      global.fetch.mock.calls.some((call) => call[1]?.method === 'POST'),
    ).toBe(false);
    expect(result).toBe(false);
  });

  it('shows an inline form error when saving after a failed load', async () => {
    global.fetch.mockResolvedValueOnce(errorResponse(500, 'Internal error'));

    const mod = await import(MAIN);
    await mod.loadConfig();
    const result = await mod.saveConfig();

    const errorMessage = document.getElementById('error-message');
    expect(errorMessage.classList.contains('show')).toBe(true);
    expect(errorMessage.textContent.length).toBeGreaterThan(0);
    expect(result).toBe(false);
  });

  it('recovers on reopen without a page reload', async () => {
    global.fetch.mockResolvedValueOnce(errorResponse(500, 'Internal error'));

    const mod = await import(MAIN);
    await mod.loadConfig();
    expect(placeholders().length).toBe(1);

    global.fetch.mockResolvedValueOnce(okResponse(configResponse()));
    await mod.loadConfig();

    expect(placeholders().length).toBe(0);
    expect(document.getElementById('save-settings').disabled).toBe(false);
    expect(
      document.getElementById('settings-modal').dataset.configLoaded,
    ).toBe('true');
    expect(global.location.reload).not.toHaveBeenCalled();
    expect(document.getElementById('setting-timezone').value).toBe('UTC');
  });

  it('saves normally once the config has loaded', async () => {
    global.fetch.mockResolvedValueOnce(okResponse(configResponse()));

    const mod = await import(MAIN);
    await mod.loadConfig();

    global.fetch.mockResolvedValueOnce(okResponse(configResponse()));
    const result = await mod.saveConfig();

    expect(result).toBe(true);
    const putCall = global.fetch.mock.calls.find(
      (call) => call[1]?.method === 'PUT',
    );
    expect(putCall).toBeDefined();
    expect(JSON.parse(putCall[1].body).data.attributes.plugins).toEqual([
      'weather',
    ]);
  });

  it('shows the server reason when a save is rejected', async () => {
    global.fetch.mockResolvedValueOnce(okResponse(configResponse()));

    const mod = await import(MAIN);
    await mod.loadConfig();

    global.fetch.mockResolvedValueOnce(errorResponse(400, 'Timezone is invalid'));
    const result = await mod.saveConfig();

    expect(result).toBe(false);
    const errorMessage = document.getElementById('error-message');
    expect(errorMessage.textContent).toBe('Timezone is invalid');
    expect(errorMessage.classList.contains('show')).toBe(true);
    expect(document.getElementById('save-settings').disabled).toBe(true);
  });

  it('falls back to a static message when a save fails without a usable reason', async () => {
    global.fetch.mockResolvedValueOnce(okResponse(configResponse()));

    const mod = await import(MAIN);
    await mod.loadConfig();

    global.fetch.mockResolvedValueOnce(errorResponse(500, 'Traceback leaked'));
    const result = await mod.saveConfig();

    expect(result).toBe(false);
    const errorMessage = document.getElementById('error-message');
    expect(errorMessage.textContent).toBe('Failed to save settings.');
    expect(errorMessage.textContent).not.toContain('Traceback');
  });

  it('does not mark changes saved when a save is rejected', async () => {
    global.fetch.mockResolvedValueOnce(okResponse(configResponse()));

    const mod = await import(MAIN);
    await mod.loadConfig();

    global.fetch.mockResolvedValueOnce(errorResponse(400, 'Timezone is invalid'));
    await mod.saveConfig();

    const modal = document.getElementById('settings-modal');
    expect(modal.dataset.changesSaved).not.toBe('true');
    expect(document.getElementById('cancel-settings').textContent).toBe(
      'Cancel',
    );
  });
});
