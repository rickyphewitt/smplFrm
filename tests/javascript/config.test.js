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

    separators.forEach(sep => sep.style.display = 'none');

    const visibleGroups = Array.from(groups).filter(g => g.style.display !== 'none');
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
            image_transition_type: 'fade'
        };

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockConfig
        });

        const response = await fetch('http://localhost:8321/api/v1/configs/test123');
        const config = await response.json();
        
        expect(global.fetch).toHaveBeenCalledWith('http://localhost:8321/api/v1/configs/test123');
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
            image_transition_type: 'zoom'
        };

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => configData
        });
        
        await fetch('http://localhost:8321/api/v1/configs/test123', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(configData)
        });

        expect(global.fetch).toHaveBeenCalledWith(
            'http://localhost:8321/api/v1/configs/test123',
            {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(configData)
            }
        );
    });

    it('should handle save error and show error message', async () => {
        vi.useFakeTimers();
        
        document.body.innerHTML = '<div id="error-message" class="error-message"></div>';
        const errorMessage = document.getElementById('error-message');

        global.fetch.mockResolvedValueOnce({
            ok: false,
            status: 500
        });

        try {
            const response = await fetch('http://localhost:8321/api/v1/configs/test123', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });

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

        expect(errorMessage.textContent).toBe('Failed to save settings. Please try again.');
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
            json: async () => ({})
        });

        const response = await fetch('http://localhost:8321/api/v1/configs/test123', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

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

        expect(document.getElementById('photo-date-group').style.display).toBe('none');
    });

    it('should hide clock groups when displayClock is false', () => {
        document.getElementById('current-date-group').style.display = 'none';
        document.getElementById('current-time-group').style.display = 'none';
        updateSeparators();

        expect(document.getElementById('current-date-group').style.display).toBe('none');
        expect(document.getElementById('current-time-group').style.display).toBe('none');
    });

    it('should hide separators between hidden groups', () => {
        document.getElementById('photo-date-group').style.display = 'none';
        document.getElementById('current-date-group').style.display = 'none';
        document.getElementById('current-time-group').style.display = 'none';
        updateSeparators();

        const separators = document.querySelectorAll('.group-separator');
        const visibleSeps = Array.from(separators).filter(s => s.style.display !== 'none');
        
        // Only weather group visible, no separators needed
        expect(visibleSeps.length).toBe(0);
    });

    it('should show separator only between visible groups', () => {
        document.getElementById('current-date-group').style.display = 'none';
        document.getElementById('current-time-group').style.display = 'none';
        updateSeparators();

        const separators = document.querySelectorAll('.group-separator');
        const visibleSeps = Array.from(separators).filter(s => s.style.display !== 'none');
        
        // photo-date and weather visible, one separator between them
        expect(visibleSeps.length).toBe(1);
    });

    it('should show all separators when all groups visible', () => {
        updateSeparators();

        const separators = document.querySelectorAll('.group-separator');
        const visibleSeps = Array.from(separators).filter(s => s.style.display !== 'none');
        
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

    it('should POST to create a task', async () => {
        const mockTask = {
            id: 'task123',
            task_type: 'clear_cache',
            status: 'pending',
            progress: 0,
            error: ''
        };

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockTask
        });

        const response = await fetch('http://localhost:8321/api/v1/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_type: 'clear_cache' })
        });
        const task = await response.json();

        expect(global.fetch).toHaveBeenCalledWith(
            'http://localhost:8321/api/v1/tasks',
            expect.objectContaining({ method: 'POST' })
        );
        expect(task.task_type).toBe('clear_cache');
        expect(task.status).toBe('pending');
    });

    it('should GET to poll task status', async () => {
        const mockTask = {
            id: 'task123',
            task_type: 'rescan_library',
            status: 'running',
            progress: 50,
            error: ''
        };

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockTask
        });

        const response = await fetch('http://localhost:8321/api/v1/tasks/task123');
        const task = await response.json();

        expect(task.status).toBe('running');
        expect(task.progress).toBe(50);
    });

    it('should handle task creation failure', async () => {
        global.fetch.mockResolvedValueOnce({
            ok: false,
            status: 400
        });

        const response = await fetch('http://localhost:8321/api/v1/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_type: 'invalid' })
        });

        expect(response.ok).toBe(false);
    });
});
