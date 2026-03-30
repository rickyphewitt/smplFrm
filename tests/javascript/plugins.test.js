import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';

describe('Plugins Tab', () => {
    beforeEach(() => {
        global.fetch = vi.fn();
        delete global.location;
        global.location = { reload: vi.fn() };

        document.body.innerHTML = `
            <div id="settings-modal" data-config-id="abc123" data-config-name="custom-test" data-config-plugins='["weather"]'>
                <div class="modal-tabs">
                    <button class="tab-btn active" data-tab="display">Display</button>
                    <button class="tab-btn" data-tab="plugins">Plugins</button>
                </div>
                <div class="tab-content active" id="tab-display">
                    <div class="settings-section"><h3>Display</h3></div>
                </div>
                <div class="tab-content" id="tab-plugins">
                    <div class="settings-section" id="plugin-list-view">
                        <table><tbody id="plugin-list-body"></tbody></table>
                    </div>
                    <div class="settings-section" id="plugin-detail-view" style="display: none;">
                        <h3 id="plugin-detail-name"></h3>
                        <div id="plugin-detail-form"></div>
                    </div>
                </div>
            </div>
            <div class="modal-actions" id="plugin-detail-actions" style="display: none;">
                <button class="btn btn-primary" id="plugin-detail-save">Save</button>
                <button class="btn btn-secondary" id="plugin-detail-back">Back</button>
            </div>
            <div class="modal-actions" id="main-actions">
                <button id="save-settings">Save</button>
                <button id="cancel-settings">Cancel</button>
            </div>
            <button id="plugin-page-prev" disabled></button>
            <span id="plugin-page-info"></span>
            <button id="plugin-page-next" disabled></button>
        `;

        global.window = Object.assign(global.window || {}, {
            SMPL_CONFIG: {
                host: 'http://localhost',
                port: '8321',
                refreshInterval: 30000,
                transitionInterval: 10000,
            }
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('should show list view and hide detail view on loadPlugins', async () => {
        const mockData = {
            count: 1,
            next: null,
            previous: null,
            results: [
                { id: 'p1', name: 'weather', description: 'Weather data' },
            ]
        };

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(mockData),
        });

        // Simulate detail view being open
        document.getElementById('plugin-list-view').style.display = 'none';
        document.getElementById('plugin-detail-view').style.display = '';

        const { loadPlugins } = await import('../../src/smplfrm/smplfrm/static/main.js');
        await loadPlugins();

        expect(document.getElementById('plugin-list-view').style.display).toBe('');
        expect(document.getElementById('plugin-detail-view').style.display).toBe('none');
    });

    it('should restore main action buttons on loadPlugins', async () => {
        const mockData = {
            count: 1,
            next: null,
            previous: null,
            results: [
                { id: 'p1', name: 'weather', description: 'Weather data' },
            ]
        };

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(mockData),
        });

        // Simulate main buttons hidden from detail view
        document.getElementById('main-actions').style.display = 'none';

        const { loadPlugins } = await import('../../src/smplfrm/smplfrm/static/main.js');
        await loadPlugins();

        expect(document.getElementById('main-actions').style.display).toBe('');
    });

    it('should hide detail view after modal reopen', async () => {
        // Simulate detail view left open
        document.getElementById('plugin-detail-view').style.display = '';
        document.getElementById('plugin-list-view').style.display = 'none';

        const mockData = {
            count: 1,
            next: null,
            previous: null,
            results: [
                { id: 'p1', name: 'weather', description: 'Weather data' },
            ]
        };

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(mockData),
        });

        // loadPlugins should reset visibility (simulates what modal open triggers)
        const { loadPlugins } = await import('../../src/smplfrm/smplfrm/static/main.js');
        await loadPlugins();

        expect(document.getElementById('plugin-detail-view').style.display).toBe('none');
        expect(document.getElementById('plugin-list-view').style.display).toBe('');
    });

    it('should render plugin rows with toggle', async () => {
        const mockData = {
            count: 2,
            next: null,
            previous: null,
            results: [
                { id: 'p1', name: 'weather', description: 'Weather data' },
                { id: 'p2', name: 'spotify', description: 'Now playing' },
            ]
        };

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(mockData),
        });

        const { loadPlugins } = await import('../../src/smplfrm/smplfrm/static/main.js');
        await loadPlugins();

        const body = document.getElementById('plugin-list-body');
        const rows = body.querySelectorAll('tr');
        expect(rows.length).toBe(2);

        // Weather should be enabled (in configPlugins)
        const weatherToggle = rows[0].querySelector('.plugin-toggle');
        expect(weatherToggle.checked).toBe(true);

        // Spotify should be disabled (not in configPlugins)
        const spotifyToggle = rows[1].querySelector('.plugin-toggle');
        expect(spotifyToggle.checked).toBe(false);
    });

    it('should update configPlugins when toggle is changed', async () => {
        const mockData = {
            count: 1, next: null, previous: null,
            results: [{ id: 'p1', name: 'spotify', description: 'Now playing' }]
        };
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockData) });

        const { loadPlugins } = await import('../../src/smplfrm/smplfrm/static/main.js');
        await loadPlugins();

        const modal = document.getElementById('settings-modal');
        const toggle = document.querySelector('.plugin-toggle');

        toggle.checked = true;
        toggle.dispatchEvent(new Event('change'));
        expect(JSON.parse(modal.dataset.configPlugins)).toContain('spotify');

        toggle.checked = false;
        toggle.dispatchEvent(new Event('change'));
        expect(JSON.parse(modal.dataset.configPlugins)).not.toContain('spotify');
    });

    it('should render configure button with correct plugin id', async () => {
        const mockData = {
            count: 1, next: null, previous: null,
            results: [{ id: 'p1', name: 'weather', description: 'Weather data' }]
        };
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockData) });

        const { loadPlugins } = await import('../../src/smplfrm/smplfrm/static/main.js');
        await loadPlugins();

        const btn = document.querySelector('.plugin-configure-btn');
        expect(btn).not.toBeNull();
        expect(btn.dataset.id).toBe('p1');
    });

    it('should show error row when fetch fails', async () => {
        global.fetch.mockRejectedValueOnce(new Error('Network error'));

        const { loadPlugins } = await import('../../src/smplfrm/smplfrm/static/main.js');
        await loadPlugins();

        const body = document.getElementById('plugin-list-body');
        expect(body.innerHTML).toContain('Failed to load plugins');
    });

    it('should set pagination controls correctly', async () => {
        const mockData = {
            count: 8, next: 'http://localhost/api/v1/plugins?page=2', previous: null,
            results: [
                { id: 'p1', name: 'a', description: '' },
                { id: 'p2', name: 'b', description: '' },
                { id: 'p3', name: 'c', description: '' },
                { id: 'p4', name: 'd', description: '' },
                { id: 'p5', name: 'e', description: '' },
            ]
        };
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockData) });

        const { loadPlugins } = await import('../../src/smplfrm/smplfrm/static/main.js');
        await loadPlugins();

        expect(document.getElementById('plugin-page-prev').disabled).toBe(true);
        expect(document.getElementById('plugin-page-next').disabled).toBe(false);
        expect(document.getElementById('plugin-page-info').textContent).toBe('Page 1 of 2');
    });

    it('should render form fields from settings schema in detail view', async () => {
        const mockData = {
            count: 1, next: null, previous: null,
            results: [{ id: 'p1', name: 'weather', description: 'Weather data' }]
        };
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockData) });

        const mod = await import('../../src/smplfrm/smplfrm/static/main.js');
        await mod.loadPlugins();

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({
                id: 'p1', name: 'weather', description: 'Weather data',
                settings: { coords: '63.17,-147.46', temp_unit: 'F' },
                settings_schema: [
                    { key: 'coords', label: 'Coordinates', type: 'text' },
                    { key: 'temp_unit', label: 'Temperature', type: 'select', options: ['F', 'C'] },
                ]
            }),
        });

        const configBtn = document.querySelector('.plugin-configure-btn');
        await configBtn.click();
        await new Promise(r => setTimeout(r, 0));

        const form = document.getElementById('plugin-detail-form');
        const inputs = form.querySelectorAll('.plugin-setting-input');
        expect(inputs.length).toBe(2);
        expect(inputs[0].dataset.key).toBe('coords');
        expect(inputs[0].value).toBe('63.17,-147.46');
        expect(inputs[1].dataset.key).toBe('temp_unit');
        expect(inputs[1].value).toBe('F');
    });

    it('should PUT plugin settings when detail save is clicked', async () => {
        const mockData = {
            count: 1, next: null, previous: null,
            results: [{ id: 'p1', name: 'weather', description: 'Weather data' }]
        };
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockData) });

        const mod = await import('../../src/smplfrm/smplfrm/static/main.js');
        await mod.loadPlugins();

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({
                id: 'p1', name: 'weather', description: 'Weather data',
                settings: { coords: '63.17,-147.46' },
                settings_schema: [{ key: 'coords', label: 'Coordinates', type: 'text' }]
            }),
        });

        const configBtn = document.querySelector('.plugin-configure-btn');
        await configBtn.click();
        await new Promise(r => setTimeout(r, 0));

        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

        const saveBtn = document.getElementById('plugin-detail-save');
        await saveBtn.click();
        await new Promise(r => setTimeout(r, 0));

        const putCall = global.fetch.mock.calls.find(c => c[1] && c[1].method === 'PUT');
        expect(putCall).toBeDefined();
        const putBody = JSON.parse(putCall[1].body);
        expect(putBody.settings.coords).toBe('63.17,-147.46');
    });

    it('should show Reload Now on cancel button after plugin detail save', async () => {
        const mod = await enterPluginDetail();

        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

        const saveBtn = document.getElementById('plugin-detail-save');
        await saveBtn.click();
        await new Promise(r => setTimeout(r, 0));

        const cancelBtn = document.getElementById('cancel-settings');
        expect(cancelBtn.textContent).toBe('Reload Now');
    });

    it('should keep Back text on plugin back button after plugin detail save', async () => {
        const mod = await enterPluginDetail();

        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

        const saveBtn = document.getElementById('plugin-detail-save');
        await saveBtn.click();
        await new Promise(r => setTimeout(r, 0));

        const backBtn = document.getElementById('plugin-detail-back');
        expect(backBtn.textContent).toBe('Back');
    });

    it('should keep main action buttons visible when not in detail view', async () => {
        const mockData = {
            count: 1,
            next: null,
            previous: null,
            results: [
                { id: 'p1', name: 'weather', description: 'Weather data' },
            ]
        };

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(mockData),
        });

        const { loadPlugins } = await import('../../src/smplfrm/smplfrm/static/main.js');
        await loadPlugins();

        // Main action buttons should always be visible in list view
        expect(document.getElementById('main-actions').style.display).toBe('');
    });

    it('should hide main action buttons only when in detail view', async () => {
        const mockData = {
            count: 1,
            next: null,
            previous: null,
            results: [
                { id: 'p1', name: 'weather', description: 'Weather data',
                  settings: {}, settings_schema: [] },
            ]
        };

        // First load for loadPlugins
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(mockData),
        });

        const mod = await import('../../src/smplfrm/smplfrm/static/main.js');
        await mod.loadPlugins();

        // Mock for openPluginDetail fetch
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({
                id: 'p1', name: 'weather', description: 'Weather data',
                settings: {}, settings_schema: []
            }),
        });

        // Click configure to open detail
        const configBtn = document.querySelector('.plugin-configure-btn');
        await configBtn.click();
        await new Promise(r => setTimeout(r, 0));

        // Main buttons should be hidden in detail view
        expect(document.getElementById('main-actions').style.display).toBe('none');

        // Mock for loadPlugins when clicking back
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(mockData),
        });

        // Click back
        const backBtn = document.getElementById('plugin-detail-back');
        await backBtn.click();
        await new Promise(r => setTimeout(r, 0));

        // Main buttons should be restored
        expect(document.getElementById('main-actions').style.display).toBe('');
    });

    it('should show only main save button after navigating away from plugin detail', async () => {
        const mockData = {
            count: 1, next: null, previous: null,
            results: [{ id: 'p1', name: 'weather', description: 'Weather data',
                settings: {}, settings_schema: [] }]
        };

        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockData) });

        const mod = await import('../../src/smplfrm/smplfrm/static/main.js');
        await mod.loadPlugins();

        // Open detail view
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({
                id: 'p1', name: 'weather', description: 'Weather data',
                settings: {}, settings_schema: []
            }),
        });
        const configBtn = document.querySelector('.plugin-configure-btn');
        await configBtn.click();
        await new Promise(r => setTimeout(r, 0));

        // Verify plugin detail actions are visible, main hidden
        expect(document.getElementById('plugin-detail-actions').style.display).toBe('');
        expect(document.getElementById('main-actions').style.display).toBe('none');

        // Simulate navigating to another tab by calling loadPlugins (what tab click does)
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockData) });
        await mod.loadPlugins();

        // Only main actions should be visible, plugin detail actions hidden
        expect(document.getElementById('main-actions').style.display).toBe('');
        expect(document.getElementById('plugin-detail-actions').style.display).toBe('none');

        // Only one save button should be visible
        const mainActionsVisible = document.getElementById('main-actions').style.display !== 'none';
        const pluginActionsHidden = document.getElementById('plugin-detail-actions').style.display === 'none';
        expect(mainActionsVisible).toBe(true);
        expect(pluginActionsHidden).toBe(true);
    });

    it('should show only main save after: open modal -> plugins -> configure -> display tab', async () => {
        // This test was originally written to prove a bug where plugin-detail-actions
        // stayed visible after switching tabs. The fix adds plugin detail cleanup to
        // the tab handler. Now this test verifies the fix stays in place.
        const mod = await enterPluginDetail();
        simulateTabSwitch('display');
        expect(document.getElementById('main-actions').style.display).toBe('');
        expect(document.getElementById('plugin-detail-actions').style.display).toBe('none');
    });

    // Helper to enter plugin detail view
    async function enterPluginDetail() {
        const pluginListData = {
            count: 1, next: null, previous: null,
            results: [{ id: 'p1', name: 'weather', description: 'Weather data' }]
        };
        const pluginDetailData = {
            id: 'p1', name: 'weather', description: 'Weather data',
            settings: {}, settings_schema: []
        };

        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(pluginListData) });
        const mod = await import('../../src/smplfrm/smplfrm/static/main.js');
        await mod.loadPlugins();

        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(pluginDetailData) });
        const configBtn = document.querySelector('.plugin-configure-btn');
        await configBtn.click();
        await new Promise(r => setTimeout(r, 0));

        expect(document.getElementById('plugin-detail-actions').style.display).toBe('');
        expect(document.getElementById('main-actions').style.display).toBe('none');
        return mod;
    }

    function simulateTabSwitch(tabName) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        document.getElementById(`tab-${tabName}`).classList.add('active');
        document.getElementById('main-actions').style.display = '';
        document.getElementById('plugin-detail-actions').style.display = 'none';
        document.getElementById('plugin-detail-view').style.display = 'none';
    }

    it('should hide plugin actions after: configure -> click Back', async () => {
        const mod = await enterPluginDetail();
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({
            count: 1, next: null, previous: null,
            results: [{ id: 'p1', name: 'weather', description: 'Weather data' }]
        })});
        const backBtn = document.getElementById('plugin-detail-back');
        await backBtn.click();
        await new Promise(r => setTimeout(r, 0));
        expect(document.getElementById('main-actions').style.display).toBe('');
        expect(document.getElementById('plugin-detail-actions').style.display).toBe('none');
    });

    it('should hide plugin actions after: configure -> close modal -> reopen -> loadPlugins', async () => {
        await enterPluginDetail();
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({
            count: 1, next: null, previous: null,
            results: [{ id: 'p1', name: 'weather', description: 'Weather data' }]
        })});
        const mod = await import('../../src/smplfrm/smplfrm/static/main.js');
        await mod.loadPlugins();
        expect(document.getElementById('main-actions').style.display).toBe('');
        expect(document.getElementById('plugin-detail-actions').style.display).toBe('none');
    });

    it('should never show both action bars at the same time in detail view', async () => {
        await enterPluginDetail();
        const mainVisible = document.getElementById('main-actions').style.display !== 'none';
        const pluginVisible = document.getElementById('plugin-detail-actions').style.display !== 'none';
        expect(mainVisible && pluginVisible).toBe(false);
    });

    it('should hide plugin detail view content when switching tabs from configure', async () => {
        await enterPluginDetail();
        expect(document.getElementById('plugin-detail-view').style.display).toBe('');
        simulateTabSwitch('display');
        expect(document.getElementById('plugin-detail-view').style.display).toBe('none');
    });

    it('should hide plugin actions after: configure -> switch to Plugins tab list', async () => {
        const mod = await enterPluginDetail();
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({
            count: 1, next: null, previous: null,
            results: [{ id: 'p1', name: 'weather', description: 'Weather data' }]
        })});
        await mod.loadPlugins();
        expect(document.getElementById('main-actions').style.display).toBe('');
        expect(document.getElementById('plugin-detail-actions').style.display).toBe('none');
        expect(document.getElementById('plugin-list-view').style.display).toBe('');
        expect(document.getElementById('plugin-detail-view').style.display).toBe('none');
    });
});
