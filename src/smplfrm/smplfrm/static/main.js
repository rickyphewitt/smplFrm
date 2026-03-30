const IMAGE_ID_ATTR = "image-id";
const OPACITY_INCREMENT = 0.1;
const OPACITY_MAX = 1.0;
const CLOCK_REFRESH_MS = 1000;
const SPOTIFY_REFRESH_MS = 5000;

const imageContainer = document.getElementById("image-container");
const progressBar = document.getElementById("progress-bar");
const config = window.SMPL_CONFIG;

export function getWindowDimensions() {
    return {
        width: window.innerWidth,
        height: window.innerHeight
    };
}

export function buildApiUrl(endpoint) {
    return `${config.host}:${config.port}/api/v1/${endpoint}`;
}

export function startProgress() {
    let width = 100;
    const interval = setInterval(() => {
        width -= 1;
        if (width <= 0) {
            clearInterval(interval);
            width = 0;
        }
        progressBar.style.width = `${width}%`;
    }, config.refreshInterval / 100);
}

export async function getNextImage() {
    const { width, height } = getWindowDimensions();
    const response = await fetch(buildApiUrl(`images/next?width=${width}&height=${height}`));
    return response.json();
}

async function displayMetadata(imageId) {
    if (!config.displayDate) return;

    try {
        const response = await fetch(buildApiUrl(`images_metadata?image__external_id=${imageId}`));
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
        }
        
        const data = await response.json();
        const takenDate = Date.parse(data[0].taken);
        
        if (isNaN(takenDate)) {
            document.getElementById("photo-date").innerHTML = `📷`;
        } else {
            const prettyDate = new Intl.DateTimeFormat("en-US", {
                year: "numeric",
                month: "long"
            }).format(takenDate);
            document.getElementById("photo-date").innerHTML = `📷 ${prettyDate}`;
        }
    } catch (error) {
        console.error('Fetch error:', error);
        document.getElementById("photo-date").innerHTML = `📷`;
    }
}

async function buildImage() {
    const nextImage = await getNextImage();
    const { width, height } = getWindowDimensions();
    const img = new Image();
    img.src = buildApiUrl(`images/${nextImage.id}/display?width=${width}&height=${height}`);
    img.setAttribute(IMAGE_ID_ATTR, nextImage.id);
    return img;
}

export function getRandomTransition() {
    const transitions = ['fade', 'slide-left', 'slide-right', 'zoom'];
    return transitions[Math.floor(Math.random() * transitions.length)];
}

export function applyTransition(image, transitionType) {
    const transition = transitionType === 'random' ? getRandomTransition() : transitionType;
    const duration = config.transitionInterval / 1000;
    
    if (transition === 'fade') {
        image.style.animation = `fadeIn ${duration}s linear forwards`;
        image.style.opacity = '1';
        return 'fade';
    } else if (transition === 'slide-left') {
        image.style.animation = `slideInLeft ${duration}s linear forwards`;
        image.style.opacity = '1';
        return 'slide-left';
    } else if (transition === 'slide-right') {
        image.style.animation = `slideInRight ${duration}s linear forwards`;
        image.style.opacity = '1';
        return 'slide-right';
    } else if (transition === 'zoom') {
        image.style.animation = `zoomInTransition ${duration}s linear forwards`;
        image.style.opacity = '1';
        return 'zoom';
    } else if (transition === 'none') {
        image.style.opacity = '1';
        return 'none';
    }
    return 'fade';
}

export function fadeInImage(image, onComplete) {
    const transitionType = applyTransition(image, config.imageTransitionType);
    
    if (transitionType === 'none') {
        // No transition, apply zoom effect immediately if enabled
        if (config.imageZoomEffect) {
            const zoomDuration = config.refreshInterval / 1000;
            image.style.animation = `zoomIn ${zoomDuration}s linear forwards`;
        }
        if (onComplete) onComplete();
        return;
    }
    
    // CSS animation-based transitions
    setTimeout(() => {
        if (config.imageZoomEffect) {
            const zoomDuration = config.refreshInterval / 1000;
            image.style.animation = `zoomIn ${zoomDuration}s linear forwards`;
        }
        if (onComplete) onComplete();
    }, config.transitionInterval);
}

async function loadNext(currentImage) {
    const newImage = await buildImage();
    newImage.classList.add("main-img");
    
    newImage.onload = () => {
        imageContainer.appendChild(newImage);
        
        setTimeout(() => {
            fadeInImage(newImage, () => {
                imageContainer.removeChild(currentImage);
            });
            displayMetadata(newImage.getAttribute(IMAGE_ID_ATTR));
            startProgress();
            loadNext(newImage);
        }, config.refreshInterval);
    };
}

async function startImages() {
    const newImage = await buildImage();
    newImage.onload = () => {
        newImage.classList.add("main-img");
        imageContainer.appendChild(newImage);
        
        fadeInImage(newImage);
        displayMetadata(newImage.getAttribute(IMAGE_ID_ATTR));
        startProgress();
        loadNext(newImage);
    };
}

function displayClock() {
    const now = new Date();
    
    // Display current date
    const currentDate = new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric"
    }).format(now);
    document.getElementById("current-date").innerHTML = `📅 ${currentDate}`;
    
    // Display current time without seconds
    const timeString = now.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true 
    });
    document.getElementById("current-time").innerHTML = `🕐 ${timeString}`;
    
    setTimeout(displayClock, CLOCK_REFRESH_MS);
}

function displayWeather() {
    if (config.weatherCurrentTemp) {
        document.getElementById("weather-temp").innerHTML = `🌡️ ${config.weatherCurrentTemp}`;
    }
}

function updateSpotifyDisplay(content) {
    const spotifyDiv = document.getElementById("spotify-now-playing");
    spotifyDiv.innerHTML = content;
}

async function getNowPlaying() {
    try {
        const response = await fetch(buildApiUrl('plugins/spotify/now_playing'));
        
        if (!response.ok) {
            const authResponse = await fetch(buildApiUrl('plugins/spotify/auth'));
            if (!authResponse.ok) {
                updateSpotifyDisplay(`<i class="iconoir-spotify spotify-icon"></i>`);
                return;
            }
            
            const authData = await authResponse.json();
            updateSpotifyDisplay(`<a href="${authData.auth_url}"><i class="iconoir-spotify spotify-icon"></i></a>`);
            return;
        }
        
        const data = await response.json();
        updateSpotifyDisplay(`<i class="iconoir-spotify spotify-icon"></i> ${data.artist} - ${data.song}`);
    } catch (error) {
        console.error('Spotify error:', error);
        updateSpotifyDisplay(`<i class="iconoir-spotify spotify-icon"></i>`);
    }
}

function refreshSpotify() {
    const spotifyBar = document.getElementById("spotify-bar");
    spotifyBar.style.display = 'flex';
    
    getNowPlaying();
    setTimeout(refreshSpotify, SPOTIFY_REFRESH_MS);
}

export function init() {
    initSettingsModal();
    startImages();

    if (config.displayClock) {
        window.onload = displayClock;
    } else {
        document.getElementById('current-date-group').style.display = 'none';
        document.getElementById('current-time-group').style.display = 'none';
    }

    if (!config.displayDate) {
        document.getElementById('photo-date-group').style.display = 'none';
    }

    displayWeather();
    if (!config.displayWeather) {
        document.getElementById('weather-group').style.display = 'none';
    }

    // Hide separators between hidden groups
    updateSeparators();

    if (config.pluginSpotifyEnabled) {
        refreshSpotify();
    }
}

function updateSeparators() {
    const bottomBar = document.getElementById('bottom-bar');
    const groups = bottomBar.querySelectorAll('.info-group');
    const separators = bottomBar.querySelectorAll('.group-separator');

    // Hide all separators first
    separators.forEach(sep => sep.style.display = 'none');

    // Show separators only between visible groups
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

async function loadConfig() {
    const modal = document.getElementById('settings-modal');
    const configId = modal.dataset.configId;
    
    try {
        const response = await fetch(buildApiUrl(`configs/${configId}`));
        if (!response.ok) throw new Error('Failed to load config');
        
        const config = await response.json();
        
        modal.dataset.configName = config.name;
        modal.dataset.configPlugins = JSON.stringify(config.plugins || []);
        document.getElementById('setting-date').checked = config.display_date;
        document.getElementById('setting-clock').checked = config.display_clock;
        document.getElementById('setting-refresh').value = config.image_refresh_interval;
        document.getElementById('setting-transition').value = config.image_transition_interval;
        document.getElementById('setting-zoom').checked = config.image_zoom_effect;
        document.getElementById('setting-transition-type').value = config.image_transition_type;
        document.getElementById('setting-cache-timeout').value = config.image_cache_timeout;
        document.getElementById('setting-timezone').value = config.timezone;
        document.getElementById('setting-fill-mode').value = config.image_fill_mode;
        document.getElementById('setting-force-date-path').checked = config.force_date_from_path;
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

async function saveConfig() {
    const modal = document.getElementById('settings-modal');
    let configId = modal.dataset.configId;
    const configName = modal.dataset.configName;
    const errorMessage = document.getElementById('error-message');
    const cancelBtn = document.getElementById('cancel-settings');
    
    const configData = {
        display_date: document.getElementById('setting-date').checked,
        display_clock: document.getElementById('setting-clock').checked,
        image_refresh_interval: parseInt(document.getElementById('setting-refresh').value),
        image_transition_interval: parseInt(document.getElementById('setting-transition').value),
        image_zoom_effect: document.getElementById('setting-zoom').checked,
        image_transition_type: document.getElementById('setting-transition-type').value,
        image_cache_timeout: parseInt(document.getElementById('setting-cache-timeout').value),
        timezone: document.getElementById('setting-timezone').value,
        image_fill_mode: document.getElementById('setting-fill-mode').value,
        force_date_from_path: document.getElementById('setting-force-date-path').checked,
        plugins: JSON.parse(modal.dataset.configPlugins || '[]')
    };
    
    try {
        // If active config is system-managed, create a custom copy first
        if (configName && configName.startsWith('smplFrm ')) {
            const applyResponse = await fetch(buildApiUrl('configs/apply'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            if (!applyResponse.ok) {
                const err = await applyResponse.json();
                throw new Error(err.detail || 'Failed to create custom config');
            }
            const newConfig = await applyResponse.json();
            configId = newConfig.id;
            modal.dataset.configId = configId;
            modal.dataset.configName = newConfig.name;
        }

        configData.name = modal.dataset.configName;

        const response = await fetch(buildApiUrl(`configs/${configId}`), {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(configData)
        });
        
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Failed to save settings');
        }
        
        console.log('Settings saved successfully');
        
        // Mark that changes were saved
        modal.dataset.changesSaved = 'true';
        
        // Change cancel button to reload button
        cancelBtn.textContent = 'Reload Now';
        cancelBtn.classList.remove('btn-secondary');
        cancelBtn.classList.add('btn-primary');
        
        return true;
    } catch (error) {
        console.error('Error saving config:', error);
        errorMessage.textContent = error.message;
        errorMessage.classList.add('show');

        const saveBtn = document.getElementById('save-settings');
        saveBtn.disabled = true;

        setTimeout(() => {
            errorMessage.classList.remove('show');
            saveBtn.disabled = false;
        }, 3000);
        
        return false;
    }
}

export async function startTask(taskType) {
    const toast = document.getElementById('task-toast');
    const bar = document.getElementById('task-toast-bar');
    const text = document.getElementById('task-toast-text');
    try {
        const response = await fetch(buildApiUrl('tasks'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_type: taskType })
        });
        if (response.status === 409) {
            const data = await response.json();
            toast.classList.add('show');
            bar.style.width = '0%';
            text.textContent = data.detail || 'Task already running';
            setTimeout(() => toast.classList.remove('show'), 3000);
            return null;
        }
        if (!response.ok) throw new Error('Failed to start task');
        const task = await response.json();
        pollTask(task.id, task.task_type_label);
        return task;
    } catch (error) {
        console.error('Error starting task:', error);
        toast.classList.add('show');
        bar.style.width = '0%';
        text.textContent = 'Failed to start task';
        setTimeout(() => toast.classList.remove('show'), 3000);
        return null;
    }
}

function pollTask(taskId, label) {
    const toast = document.getElementById('task-toast');
    const bar = document.getElementById('task-toast-bar');
    const text = document.getElementById('task-toast-text');

    toast.classList.add('show');
    text.textContent = `${label} 0%`;
    bar.style.width = '0%';

    const interval = setInterval(async () => {
        try {
            const response = await fetch(buildApiUrl(`tasks/${taskId}`));
            if (!response.ok) throw new Error('Poll failed');
            const task = await response.json();

            bar.style.width = `${task.progress}%`;
            text.textContent = `${label} ${task.progress}%`;

            if (task.status === 'completed' || task.status === 'failed') {
                clearInterval(interval);
                text.textContent = task.status === 'completed' ? `${label} Done!` : `${label} Failed: ${task.error}`;
                setTimeout(() => toast.classList.remove('show'), 3000);
            }
        } catch {
            clearInterval(interval);
            toast.classList.remove('show');
        }
    }, 1000);
}

let taskPage = 1;
let presetPage = 1;

let pluginPage = 1;

export async function loadPlugins(page = 1) {
    pluginPage = page;
    document.getElementById('plugin-list-view').style.display = '';
    document.getElementById('plugin-detail-view').style.display = 'none';
    document.getElementById('main-actions').style.display = '';
    document.getElementById('plugin-detail-actions').style.display = 'none';
    const body = document.getElementById('plugin-list-body');
    const modal = document.getElementById('settings-modal');
    const prev = document.getElementById('plugin-page-prev');
    const next = document.getElementById('plugin-page-next');
    const info = document.getElementById('plugin-page-info');
    const enabledPlugins = JSON.parse(modal.dataset.configPlugins || '[]');

    try {
        const response = await fetch(buildApiUrl(`plugins?page=${page}`));
        if (!response.ok) throw new Error('Failed to load plugins');
        const data = await response.json();

        body.innerHTML = data.results.map(p => {
            const isEnabled = enabledPlugins.includes(p.name);
            const checked = isEnabled ? 'checked' : '';
            return `<tr>
                <td>${p.name}</td>
                <td>${p.description || ''}</td>
                <td><button class="btn btn-secondary btn-sm plugin-configure-btn" data-id="${p.id}">Configure</button></td>
                <td><label class="toggle-switch plugin-toggle-wrap"><input type="checkbox" class="plugin-toggle" data-name="${p.name}" ${checked}><span class="slider"></span></label></td>
            </tr>`;
        }).join('');

        // Toggles only update local state — Save button does the PUT
        body.querySelectorAll('.plugin-toggle').forEach(toggle => {
            toggle.addEventListener('change', () => {
                const name = toggle.dataset.name;
                if (toggle.checked) {
                    if (!enabledPlugins.includes(name)) enabledPlugins.push(name);
                } else {
                    const idx = enabledPlugins.indexOf(name);
                    if (idx > -1) enabledPlugins.splice(idx, 1);
                }
                modal.dataset.configPlugins = JSON.stringify(enabledPlugins);
            });
        });

        // Configure button opens detail view
        body.querySelectorAll('.plugin-configure-btn').forEach(btn => {
            btn.addEventListener('click', () => openPluginDetail(btn.dataset.id));
        });

        const totalPages = Math.ceil(data.count / 5) || 1;
        info.textContent = `Page ${page} of ${totalPages}`;
        prev.disabled = !data.previous;
        next.disabled = !data.next;
    } catch {
        body.innerHTML = '<tr><td colspan="4">Failed to load plugins</td></tr>';
    }
}

const PLUGIN_ACTION_HANDLERS = {
    geolocation: (input) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'action-btn';
        btn.textContent = '📍';
        btn.title = 'Use current location';
        btn.addEventListener('click', () => {
            if (!navigator.geolocation) return;
            btn.textContent = '...';
            navigator.geolocation.getCurrentPosition(
                pos => { input.value = `${pos.coords.latitude},${pos.coords.longitude}`; btn.textContent = '📍'; },
                () => { btn.textContent = '📍'; }
            );
        });
        return btn;
    }
};

async function openPluginDetail(pluginId) {
    const listView = document.getElementById('plugin-list-view');
    const detailView = document.getElementById('plugin-detail-view');
    const nameEl = document.getElementById('plugin-detail-name');
    const formEl = document.getElementById('plugin-detail-form');

    const resp = await fetch(buildApiUrl(`plugins/${pluginId}`));
    if (!resp.ok) return;
    const plugin = await resp.json();

    nameEl.textContent = plugin.name;
    formEl.innerHTML = '';

    (plugin.settings_schema || []).forEach(field => {
        const div = document.createElement('div');
        div.className = 'setting-item';

        const label = document.createElement('label');
        label.textContent = field.label;
        div.appendChild(label);

        const row = document.createElement('div');
        row.className = 'field-row';

        let input;
        if (field.type === 'select') {
            input = document.createElement('select');
            input.className = 'select-input';
            (field.options || []).forEach(opt => {
                const option = document.createElement('option');
                option.value = opt;
                option.textContent = opt;
                input.appendChild(option);
            });
            input.value = plugin.settings[field.key] || '';
        } else if (field.type === 'toggle') {
            const toggleLabel = document.createElement('label');
            toggleLabel.className = 'toggle-switch';
            input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = !!plugin.settings[field.key];
            const slider = document.createElement('span');
            slider.className = 'slider';
            toggleLabel.appendChild(input);
            toggleLabel.appendChild(slider);
            row.appendChild(toggleLabel);
        } else {
            input = document.createElement('input');
            input.type = field.type === 'password' ? 'password' : 'text';
            input.className = 'select-input';
            input.value = plugin.settings[field.key] || '';
            if (field.type === 'password') {
                const reveal = document.createElement('button');
                reveal.type = 'button';
                reveal.className = 'reveal-btn';
                reveal.textContent = '👁';
                reveal.addEventListener('click', () => {
                    input.type = input.type === 'password' ? 'text' : 'password';
                });
                row.appendChild(input);
                row.appendChild(reveal);
            }
        }

        input.dataset.key = field.key;
        input.classList.add('plugin-setting-input');

        if (field.type !== 'password' && field.type !== 'toggle') row.appendChild(input);

        if (field.action && PLUGIN_ACTION_HANDLERS[field.action]) {
            row.appendChild(PLUGIN_ACTION_HANDLERS[field.action](input));
        }

        div.appendChild(row);
        formEl.appendChild(div);
    });

    // Save handler
    const saveBtn = document.getElementById('plugin-detail-save');
    const newSave = saveBtn.cloneNode(true);
    saveBtn.parentNode.replaceChild(newSave, saveBtn);
    newSave.addEventListener('click', async () => {
        const settings = {};
        formEl.querySelectorAll('.plugin-setting-input').forEach(el => {
            settings[el.dataset.key] = el.type === 'checkbox' ? el.checked : el.value;
        });
        await fetch(buildApiUrl(`plugins/${pluginId}`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ settings })
        });
        newSave.textContent = 'Saved!';
        setTimeout(() => { newSave.textContent = 'Save'; }, 1500);

        const modal = document.getElementById('settings-modal');
        modal.dataset.changesSaved = 'true';
        const cancelBtn = document.getElementById('cancel-settings');
        cancelBtn.textContent = 'Reload Now';
        cancelBtn.classList.remove('btn-secondary');
        cancelBtn.classList.add('btn-primary');
    });

    listView.style.display = 'none';
    detailView.style.display = '';
    document.getElementById('main-actions').style.display = 'none';
    document.getElementById('plugin-detail-actions').style.display = '';

    // Back button
    const backBtn = document.getElementById('plugin-detail-back');
    const newBack = backBtn.cloneNode(true);
    backBtn.parentNode.replaceChild(newBack, backBtn);
    newBack.addEventListener('click', () => loadPlugins(pluginPage));
}

export async function loadPresets(page = 1) {
    presetPage = page;
    const body = document.getElementById('preset-list-body');
    const prev = document.getElementById('preset-page-prev');
    const next = document.getElementById('preset-page-next');
    const info = document.getElementById('preset-page-info');
    const modal = document.getElementById('settings-modal');
    const activeConfigId = modal.dataset.configId;

    try {
        const response = await fetch(buildApiUrl(`configs?page=${page}`));
        if (!response.ok) throw new Error('Failed to load presets');
        const data = await response.json();

        body.innerHTML = data.results.map(c => {
            const isManaged = c.name.startsWith('smplFrm ');
            const nameCell = isManaged
                ? `<td>${c.name}</td>`
                : `<td class="editable" contenteditable="true" data-id="${c.id}" data-field="name">${c.name}</td>`;
            const descCell = isManaged
                ? `<td>${c.description || ''}</td>`
                : `<td class="editable" contenteditable="true" data-id="${c.id}" data-field="description">${c.description || ''}</td>`;
            const status = c.is_active
                ? '<span class="badge-active">Active</span>'
                : `<button class="btn btn-secondary btn-sm preset-activate-btn" data-id="${c.id}">Activate</button>`;
            const deleteBtn = (!isManaged && !c.is_active)
                ? `<button class="btn btn-secondary btn-sm task-delete-btn preset-delete-btn" data-id="${c.id}">&times;</button>`
                : isManaged
                    ? `<span class="delete-disabled" title="System-managed configs cannot be deleted">🔒</span>`
                    : `<span class="delete-disabled" title="Active config cannot be deleted">🔒</span>`;
            return `<tr>${nameCell}${descCell}<td>${status}</td><td>${deleteBtn}</td></tr>`;
        }).join('');

        body.querySelectorAll('.editable').forEach(cell => {
            cell.dataset.original = cell.textContent.trim();
            const save = async () => {
                const value = cell.textContent.trim();
                if (value === cell.dataset.original) return;
                const id = cell.dataset.id;
                const field = cell.dataset.field;
                try {
                    const getResp = await fetch(buildApiUrl(`configs/${id}`));
                    if (!getResp.ok) return;
                    const config = await getResp.json();
                    config[field] = value;
                    delete config.id;
                    delete config.is_active;
                    await fetch(buildApiUrl(`configs/${id}`), {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(config)
                    });
                    cell.dataset.original = value;
                } catch (e) {
                    console.error('Failed to save:', e);
                }
            };
            cell.addEventListener('blur', save);
            cell.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') { e.preventDefault(); cell.blur(); }
            });
        });

        body.querySelectorAll('.preset-activate-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-inline"></span>';
                try {
                    const resp = await fetch(buildApiUrl(`configs/${btn.dataset.id}/activate`), { method: 'POST' });
                    if (!resp.ok) throw new Error('Failed to activate');
                    location.reload();
                } catch {
                    btn.disabled = false;
                    btn.textContent = 'Activate';
                }
            });
        });

        body.querySelectorAll('.preset-delete-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                await fetch(buildApiUrl(`configs/${btn.dataset.id}`), { method: 'DELETE' });
                loadPresets(presetPage);
            });
        });

        const totalPages = Math.ceil(data.count / 5) || 1;
        info.textContent = `Page ${page} of ${totalPages}`;
        prev.disabled = !data.previous;
        next.disabled = !data.next;
    } catch {
        body.innerHTML = '<tr><td colspan="4">Failed to load presets</td></tr>';
    }
}

export async function loadTasks(page = 1) {
    taskPage = page;
    const body = document.getElementById('task-list-body');
    const prev = document.getElementById('task-page-prev');
    const next = document.getElementById('task-page-next');
    const info = document.getElementById('task-page-info');

    try {
        const response = await fetch(buildApiUrl(`tasks?page=${page}`));
        if (!response.ok) throw new Error('Failed to load tasks');
        const data = await response.json();

        body.innerHTML = data.results.map(t => {
            const created = new Date(t.created).toLocaleString();
            return `<tr data-id="${t.id}"><td>${t.task_type_label}</td><td>${t.status}</td><td>${t.progress}%</td><td>${created}</td><td><button class="btn btn-secondary btn-sm task-delete-btn" data-id="${t.id}">&times;</button></td></tr>`;
        }).join('');

        body.querySelectorAll('.task-delete-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                await fetch(buildApiUrl(`tasks/${btn.dataset.id}`), { method: 'DELETE' });
                loadTasks(taskPage);
            });
        });

        const totalPages = Math.ceil(data.count / 5) || 1;
        info.textContent = `Page ${page} of ${totalPages}`;
        prev.disabled = !data.previous;
        next.disabled = !data.next;
    } catch {
        body.innerHTML = '<tr><td colspan="5">Failed to load tasks</td></tr>';
    }
}

function initSettingsModal() {
    const modal = document.getElementById('settings-modal');
    const logoIcon = document.getElementById('logo-icon');
    const closeBtn = document.getElementById('close-modal');
    const cancelBtn = document.getElementById('cancel-settings');
    const saveBtn = document.getElementById('save-settings');
    const tabBtns = document.querySelectorAll('.tab-btn');

    logoIcon.addEventListener('click', async () => {
        modal.classList.add('open');
        modal.dataset.changesSaved = 'false';
        cancelBtn.textContent = 'Cancel';
        cancelBtn.classList.remove('btn-primary');
        cancelBtn.classList.add('btn-secondary');

        // Reset plugin detail view
        document.getElementById('plugin-detail-view').style.display = 'none';
        document.getElementById('plugin-list-view').style.display = '';
        document.getElementById('main-actions').style.display = '';

        const activeTab = document.querySelector('.tab-content.active');
        const sections = activeTab.querySelectorAll('.settings-section');
        sections.forEach(s => s.style.display = 'none');
        const spinner = document.createElement('div');
        spinner.className = 'spinner';
        activeTab.appendChild(spinner);
        await loadConfig();
        spinner.remove();
        sections.forEach(s => s.style.display = '');

        // Ensure plugin detail stays hidden after section restore
        document.getElementById('plugin-detail-view').style.display = 'none';
        document.getElementById('plugin-detail-actions').style.display = 'none';
    });

    const closeModal = () => {
        const changesSaved = modal.dataset.changesSaved === 'true';
        if (changesSaved) {
            location.reload();
        } else {
            modal.classList.remove('open');
        }
    };

    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('open')) {
            closeModal();
        }
    });

    tabBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const tabName = btn.dataset.tab;
            
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`tab-${tabName}`).classList.add('active');

            // Always restore main action buttons and hide plugin detail when switching tabs
            document.getElementById('main-actions').style.display = '';
            document.getElementById('plugin-detail-actions').style.display = 'none';
            document.getElementById('plugin-detail-view').style.display = 'none';

            if (tabName === 'tasks') {
                const taskTab = document.getElementById('tab-tasks');
                const sections = taskTab.querySelectorAll('.settings-section, .task-pagination');
                sections.forEach(s => s.style.display = 'none');
                const spinner = document.createElement('div');
                spinner.className = 'spinner';
                taskTab.appendChild(spinner);
                await loadTasks();
                spinner.remove();
                sections.forEach(s => s.style.display = '');
            }

            if (tabName === 'presets') {
                const presetsTab = document.getElementById('tab-presets');
                const sections = presetsTab.querySelectorAll('.settings-section, .preset-pagination');
                sections.forEach(s => s.style.display = 'none');
                const spinner = document.createElement('div');
                spinner.className = 'spinner';
                presetsTab.appendChild(spinner);
                await loadPresets();
                spinner.remove();
                sections.forEach(s => s.style.display = '');
            }

            if (tabName === 'plugins') {
                const pluginsTab = document.getElementById('tab-plugins');
                const listView = document.getElementById('plugin-list-view');
                listView.style.display = 'none';
                document.getElementById('plugin-detail-view').style.display = 'none';
                const spinner = document.createElement('div');
                spinner.className = 'spinner';
                pluginsTab.appendChild(spinner);
                await loadPlugins();
                spinner.remove();
            }
        });
    });

    saveBtn.addEventListener('click', async () => {
        await saveConfig();
    });

    // Task pagination buttons
    document.getElementById('task-page-prev').addEventListener('click', () => loadTasks(taskPage - 1));
    document.getElementById('task-page-next').addEventListener('click', () => loadTasks(taskPage + 1));

    // Preset pagination buttons
    document.getElementById('preset-page-prev').addEventListener('click', () => loadPresets(presetPage - 1));
    document.getElementById('preset-page-next').addEventListener('click', () => loadPresets(presetPage + 1));

    // Plugin pagination buttons
    document.getElementById('plugin-page-prev').addEventListener('click', () => loadPlugins(pluginPage - 1));
    document.getElementById('plugin-page-next').addEventListener('click', () => loadPlugins(pluginPage + 1));

    // Library maintenance buttons
    document.getElementById('task-reset-count').addEventListener('click', () => {
        startTask('reset_image_count');
    });
    document.getElementById('task-clear-cache').addEventListener('click', () => {
        startTask('clear_cache');
    });
    document.getElementById('task-rescan-library').addEventListener('click', () => {
        startTask('rescan_library');
    });
}
