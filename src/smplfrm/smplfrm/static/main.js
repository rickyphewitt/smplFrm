import { resilientFetch, taskPollFetch, parseRetryAfter } from './resilientFetch.js';
import {
  fetchJsonApi,
  JsonApiError,
  unwrapResource,
  unwrapResourceList,
  buildResourceDocument,
  formatWeatherTemp,
} from './jsonApiClient.js';
import {
  ERROR_PLACEHOLDER_CLASS,
  installGlobalRejectionHandler,
  reportError,
} from './uiErrors.js';

const IMAGE_ID_ATTR = 'image-id';
const OPACITY_INCREMENT = 0.1;
const OPACITY_MAX = 1.0;
const CLOCK_REFRESH_MS = 1000;
const SPOTIFY_REFRESH_MS = 5000;
const IMAGE_QUEUE_TARGET = 5;
const IMAGE_QUEUE_LOW_WATER = 2;

const imageContainer = document.getElementById('image-container');
const progressBar = document.getElementById('progress-bar');
const config = window.SMPL_CONFIG;

/**
 * Browser-local queue of image objects for continuous display.
 * Each entry contains { id: string, ...attributes }.
 * @type {Array<{id: string, name: string, [key: string]: any}>}
 */
let imageQueue = [];

/**
 * Current page number for paginated image fetching (1-indexed).
 * @type {number}
 */
let currentPage = 1;

/**
 * Total pages available from the last successful fetch, or null if unknown.
 * Used to wrap pagination back to page 1 when exhausted.
 * @type {number|null}
 */
let totalPages = null;

export function getWindowDimensions() {
  return {
    width: window.innerWidth,
    height: window.innerHeight,
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
  // Check if queue needs refilling
  if (imageQueue.length <= IMAGE_QUEUE_LOW_WATER) {
    await refillQueue();
  }

  // Return next image from queue, or null if empty
  if (imageQueue.length > 0) {
    return imageQueue.shift();
  }

  return null;
}

async function refillQueue() {
  try {
    // Wrap to page 1 if we've exceeded known total pages
    if (totalPages !== null && currentPage > totalPages) {
      currentPage = 1;
    }

    // Fetch next page of images with display_priority sort
    const response = await fetchJsonApi(
      buildApiUrl(`images?sort=display_priority&page[number]=${currentPage}`)
    );

    const { resources, meta } = unwrapResourceList(response);
    
    // Update total pages from response
    if (meta?.pagination?.pages) {
      totalPages = meta.pagination.pages;
    }
    
    if (resources.length === 0) {
      // No more images - reset to first page
      currentPage = 1;
      return;
    }

    // Extract new image IDs not already in queue
    const newImages = resources
      .map(r => ({ id: r.id, ...r.attributes }))
      .filter(img => !imageQueue.find(q => q.id === img.id));

    if (newImages.length === 0) {
      // All images already queued - advance or wrap to beginning
      if (currentPage >= totalPages) {
        currentPage = 1;
      } else {
        currentPage++;
      }
      return;
    }

    // Append new images to queue
    imageQueue.push(...newImages);

    // Request best-effort preload for newly appended images
    const imageIds = newImages.map(img => img.id);
    if (imageIds.length > 0) {
      const { width, height } = getWindowDimensions();
      await requestPreload(imageIds, width, height);
    }

    // Advance to next page, wrapping to 1 if we've reached the end
    if (currentPage >= totalPages) {
      currentPage = 1;
    } else {
      currentPage++;
    }
  } catch (error) {
    // On fetch failure, keep existing queue and retry on next refill attempt
    // If 404 (invalid page), reset to page 1
    if (error?.status === 404) {
      console.debug('Invalid page, resetting to page 1');
      currentPage = 1;
    } else {
      console.debug('Queue refill failed, will retry:', error);
    }
  }
}

async function requestPreload(imageIds, width, height) {
  try {
    const payload = {
      data: {
        type: 'preload_image_cache_tasks',
        attributes: {
          image_ids: imageIds.slice(0, 5), // Max 5 per spec
          width: Math.floor(width),
          height: Math.floor(height),
        },
      },
    };

    const response = await resilientFetch(buildApiUrl('tasks'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/vnd.api+json',
        'Accept': 'application/vnd.api+json',
      },
      body: JSON.stringify(payload),
    });

    // 409 (conflict or capacity) is non-critical - preload is best-effort
    if (response.status === 409) {
      console.debug('Preload conflict or capacity exceeded, continuing without preload');
      return;
    }

    // 429 (rate limited) is non-critical - continue without preload
    if (response.status === 429) {
      console.debug('Preload rate limited, continuing without preload');
      return;
    }

    if (!response.ok) {
      console.debug('Preload request failed:', response.status);
    }
  } catch (error) {
    // Non-critical failure - display continues with uncached images
    console.debug('Preload request error:', error);
  }
}

async function displayMetadata(imageId) {
  if (!config.displayDate) return;

  try {
    const response = await resilientFetch(
      buildApiUrl(`images_metadata?filter[image]=${imageId}`),
    );
    if (!response.ok) {
      // Silently ignore 429 responses — don't show error for rate limiting
      if (response.status === 429) return;
      throw new Error(`Network response was not ok: ${response.statusText}`);
    }

    const data = await response.json();
    // Unwrap JSON:API response
    const { resources } = unwrapResourceList(data);
    if (resources.length === 0) {
      document.getElementById('photo-date').innerHTML = `📷`;
      return;
    }

    const takenDate = Date.parse(resources[0].attributes.taken);

    if (isNaN(takenDate)) {
      document.getElementById('photo-date').innerHTML = `📷`;
    } else {
      const prettyDate = new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'long',
      }).format(takenDate);
      document.getElementById('photo-date').innerHTML = `📷 ${prettyDate}`;
    }
  } catch (error) {
    // Don't log 429 errors — they're handled silently
    if (error && error.status !== 429) {
      console.error('Fetch error:', error);
    }
    document.getElementById('photo-date').innerHTML = `📷`;
  }
}

async function buildImage() {
  const nextImage = await getNextImage();
  
  if (!nextImage) {
    // Queue empty and refill failed - return null
    return null;
  }
  
  const { width, height } = getWindowDimensions();
  const img = new Image();
  img.src = buildApiUrl(
    `images/${nextImage.id}/display?filter[width]=${width}&filter[height]=${height}`,
  );
  img.setAttribute(IMAGE_ID_ATTR, nextImage.id);
  return img;
}

export function getRandomTransition() {
  const transitions = ['fade', 'slide-left', 'slide-right', 'zoom'];
  return transitions[Math.floor(Math.random() * transitions.length)];
}

export function applyTransition(image, transitionType) {
  const transition =
    transitionType === 'random' ? getRandomTransition() : transitionType;
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
  try {
    const newImage = await buildImage();
    
    if (!newImage) {
      // No image available - keep current image, retry after refresh interval
      setTimeout(() => {
        loadNext(currentImage);
      }, config.refreshInterval);
      return;
    }
    
    newImage.classList.add('main-img');

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
  } catch (error) {
    // On fetch failure: keep current image, retry after refreshInterval
    setTimeout(() => {
      loadNext(currentImage);
    }, config.refreshInterval);
  }
}

async function startImages() {
  try {
    const newImage = await buildImage();
    
    if (!newImage) {
      // No images available - retry after refresh interval
      setTimeout(() => {
        startImages();
      }, config.refreshInterval);
      return;
    }
    
    newImage.onload = () => {
      newImage.classList.add('main-img');
      imageContainer.appendChild(newImage);

      fadeInImage(newImage);
      displayMetadata(newImage.getAttribute(IMAGE_ID_ATTR));
      startProgress();
      loadNext(newImage);
    };
  } catch (error) {
    // On fetch failure: retry after refreshInterval
    setTimeout(() => {
      startImages();
    }, config.refreshInterval);
  }
}

function displayClock() {
  const now = new Date();

  // Display current date
  const currentDate = new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(now);
  document.getElementById('current-date').innerHTML = `📅 ${currentDate}`;

  // Display current time without seconds
  const timeString = now.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
  document.getElementById('current-time').innerHTML = `🕐 ${timeString}`;

  setTimeout(displayClock, CLOCK_REFRESH_MS);
}

function displayWeather() {
  const weatherGroup = document.getElementById('weather-group');
  if (!config.plugins || !config.plugins.includes('weather')) {
    weatherGroup.style.display = 'none';
    return;
  }
  // Fetch weather data from plugin API (JSON:API format)
  fetchJsonApi(buildApiUrl('plugins/weather/current'))
    .then((jsonApiDoc) => {
      const resource = unwrapResource(jsonApiDoc);
      if (resource && resource.attributes) {
        const { temperature, temperature_scale } = resource.attributes;
        const formatted = formatWeatherTemp(temperature, temperature_scale);
        document.getElementById('weather-temp').innerHTML = `🌡️ ${formatted}`;
      }
    })
    .catch(() => {});
}

function showSpotifyBar(content) {
  const spotifyDiv = document.getElementById('spotify-now-playing');
  spotifyDiv.innerHTML = content;
  const bar = document.getElementById('spotify-bar');
  bar.style.display = 'flex';
  bar.classList.add('bar-fade-in');
}

let spotifyAuthLinkActive = false;
let spotifyAuthRequestInFlight = false;

function showSpotifyAuthLink(authUrl, reason) {
  const reconnect = reason === 'expired';
  const label = reconnect
    ? 'Expired - Reconnect Spotify'
    : 'Connect Spotify';
  const tooltip = reconnect
    ? 'Spotify connection expired - Click to reconnect'
    : 'Connect Spotify';
  const link = document.createElement('a');
  link.href = authUrl;
  link.title = tooltip;
  link.className = reconnect ? 'spotify-reconnect-link' : 'spotify-connect-link';

  const icon = document.createElement('i');
  icon.className = reconnect
    ? 'iconoir-spotify spotify-icon spotify-expired'
    : 'iconoir-spotify spotify-icon';
  const text = document.createElement('span');
  text.textContent = label;
  link.append(icon, text);

  const spotifyDiv = document.getElementById('spotify-now-playing');
  spotifyDiv.replaceChildren(link);
  const bar = document.getElementById('spotify-bar');
  bar.style.display = 'flex';
  bar.classList.add('bar-fade-in');
}

async function showSpotifyAuthorization(reason) {
  if (spotifyAuthLinkActive || spotifyAuthRequestInFlight) {
    return;
  }

  spotifyAuthRequestInFlight = true;
  try {
    const response = await fetchJsonApi(buildApiUrl('plugins/spotify/auth'));
    const resource = unwrapResource(response);

    if (!resource || !resource.attributes.auth_url) {
      showSpotifyBar(`<i class="iconoir-spotify spotify-icon"></i>`);
      return;
    }

    showSpotifyAuthLink(resource.attributes.auth_url, reason);
    spotifyAuthLinkActive = true;
  } catch (error) {
    // On any error (429, 500, 503): show icon only
    showSpotifyBar(`<i class="iconoir-spotify spotify-icon"></i>`);
  } finally {
    spotifyAuthRequestInFlight = false;
  }
}

export async function getNowPlaying() {
  try {
    const response = await fetchJsonApi(buildApiUrl('plugins/spotify/status'));
    const resource = unwrapResource(response);

    spotifyAuthLinkActive = false;

    // Check if plugin is configured
    if (!resource || !resource.attributes.configured) {
      showSpotifyBar(`<i class="iconoir-spotify spotify-icon"></i>`);
      return;
    }

    // Check if anything is playing
    if (!resource.attributes.is_playing) {
      showSpotifyBar(`<i class="iconoir-spotify spotify-icon"></i>`);
      return;
    }

    // Get track from included resources
    const trackId = resource.relationships?.track?.data?.id;
    const track = response.included?.find(
      (r) => r.type === 'spotify_tracks' && r.id === trackId,
    );

    if (track) {
      showSpotifyBar(
        `<i class="iconoir-spotify spotify-icon"></i> ${track.attributes.artist} - ${track.attributes.song}`,
      );
    } else {
      showSpotifyBar(`<i class="iconoir-spotify spotify-icon"></i>`);
    }
  } catch (error) {
    if (error instanceof JsonApiError) {
      if (error.status === 401) {
        const authError = error.errors[0];
        if (authError?.code === 'spotify_authorization_required') {
          const reason = authError.detail?.includes('expired')
            ? 'expired'
            : 'missing';
          await showSpotifyAuthorization(reason);
          return;
        }
      }

      // On 429 or other errors: show icon only
      if (error.status === 429) {
        if (!spotifyAuthLinkActive) {
          showSpotifyBar(`<i class="iconoir-spotify spotify-icon"></i>`);
        }
        return;
      }
    }

    console.error('Spotify error:', error);
    if (!spotifyAuthLinkActive) {
      showSpotifyBar(`<i class="iconoir-spotify spotify-icon"></i>`);
    }
  }
}

function refreshSpotify() {
  getNowPlaying();
  setTimeout(refreshSpotify, SPOTIFY_REFRESH_MS);
}

export function init() {
  // Installed first so a rejection from anything below still reaches the user.
  installGlobalRejectionHandler();
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

  // Hide separators between hidden groups
  updateSeparators();

  if (config.plugins && config.plugins.includes('spotify')) {
    refreshSpotify();
  }
}

export function updateSeparators() {
  const bottomBar = document.getElementById('bottom-bar');
  const groups = bottomBar.querySelectorAll('.info-group');
  const separators = bottomBar.querySelectorAll('.group-separator');

  // Hide all separators first
  separators.forEach((sep) => (sep.style.display = 'none'));

  // Show separators only between visible groups
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

  // Hide bottom bar entirely when no groups are visible
  if (visibleGroups.length === 0) {
    bottomBar.style.display = 'none';
  } else {
    bottomBar.style.display = 'flex';
    bottomBar.classList.add('bar-fade-in');
  }
}

/**
 * The region the settings form occupies, used as the failure target for a
 * config load. Falls back to the modal itself if no tab is active.
 *
 * @param {Element} modal - The settings modal
 * @returns {Element} - The element a load failure renders into
 */
function settingsBody(modal) {
  return modal.querySelector('.tab-content.active') || modal;
}

/**
 * Removes a config-load placeholder from whichever tab it was rendered into.
 * Scoped to direct children of a tab so it cannot disturb the placeholder rows
 * the plugin, preset, and task lists render inside their tables.
 *
 * @param {Element} modal - The settings modal
 */
function clearSettingsPlaceholder(modal) {
  modal
    .querySelectorAll(`.tab-content > .${ERROR_PLACEHOLDER_CLASS}`)
    .forEach((node) => node.remove());
}

export async function loadConfig() {
  const modal = document.getElementById('settings-modal');
  const configId = modal.dataset.configId;
  const saveBtn = document.getElementById('save-settings');

  try {
    const doc = await fetchJsonApi(buildApiUrl(`configs/${configId}`));
    const resource = unwrapResource(doc);
    if (!resource) throw new Error('Failed to load config');

    const config = { id: resource.id, ...resource.attributes };

    modal.dataset.configName = config.name;
    modal.dataset.configPlugins = JSON.stringify(config.plugins || []);
    document.getElementById('setting-date').checked = config.display_date;
    document.getElementById('setting-clock').checked = config.display_clock;
    document.getElementById('setting-refresh').value =
      config.image_refresh_interval;
    document.getElementById('setting-transition').value =
      config.image_transition_interval;
    document.getElementById('setting-zoom').checked = config.image_zoom_effect;
    document.getElementById('setting-transition-type').value =
      config.image_transition_type;
    document.getElementById('setting-cache-timeout').value =
      config.image_cache_timeout;
    document.getElementById('setting-timezone').value = config.timezone;
    document.getElementById('setting-fill-mode').value = config.image_fill_mode;
    document.getElementById('setting-force-date-path').checked =
      config.force_date_from_path;

    clearSettingsPlaceholder(modal);
    modal.dataset.configLoaded = 'true';
    if (saveBtn) saveBtn.disabled = false;
  } catch (error) {
    // No settings input carries a server-rendered value, so a failed load
    // leaves every field blank. Saving from that state would submit an empty
    // plugin list and null intervals, so the form is marked unloaded and
    // saving stays blocked until a load succeeds.
    modal.dataset.configLoaded = 'false';
    if (saveBtn) saveBtn.disabled = true;
    reportError(error, {
      channel: 'view',
      fallback: 'Failed to load settings. Close and reopen settings to retry.',
      target: settingsBody(modal),
    });
  }
}

export async function saveConfig() {
  const modal = document.getElementById('settings-modal');
  let configId = modal.dataset.configId;
  const configName = modal.dataset.configName;
  const errorMessage = document.getElementById('error-message');
  const cancelBtn = document.getElementById('cancel-settings');

  // Blank fields from a failed load must never be submitted: the save button is
  // already disabled, and this guard also covers a programmatic call.
  if (modal.dataset.configLoaded === 'false') {
    reportError(new Error('Settings were never loaded'), {
      channel: 'form',
      fallback: 'Settings could not be loaded, so they cannot be saved.',
    });
    return false;
  }

  const configAttributes = {
    display_date: document.getElementById('setting-date').checked,
    display_clock: document.getElementById('setting-clock').checked,
    image_refresh_interval: parseInt(
      document.getElementById('setting-refresh').value,
    ),
    image_transition_interval: parseInt(
      document.getElementById('setting-transition').value,
    ),
    image_zoom_effect: document.getElementById('setting-zoom').checked,
    image_transition_type: document.getElementById('setting-transition-type')
      .value,
    image_cache_timeout: parseInt(
      document.getElementById('setting-cache-timeout').value,
    ),
    timezone: document.getElementById('setting-timezone').value,
    image_fill_mode: document.getElementById('setting-fill-mode').value,
    force_date_from_path: document.getElementById('setting-force-date-path')
      .checked,
    plugins: JSON.parse(modal.dataset.configPlugins || '[]'),
  };

  try {
    // If active config is system-managed, create new custom config via POST
    if (configName && configName.startsWith('smplFrm ')) {
      // POST to create new config with is_active=true
      const createDoc = await fetchJsonApi(buildApiUrl('configs'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/vnd.api+json' },
        body: JSON.stringify(
          buildResourceDocument('configs', null, {
            ...configAttributes,
            is_active: true,
          }),
        ),
      });
      const newConfig = unwrapResource(createDoc);
      if (!newConfig) {
        throw new Error('Failed to create custom config');
      }
      configId = newConfig.id;
      modal.dataset.configId = configId;
      modal.dataset.configName = newConfig.attributes.name;

      console.log('Settings saved successfully');
      modal.dataset.changesSaved = 'true';
      cancelBtn.textContent = 'Reload Now';
      cancelBtn.classList.remove('btn-secondary');
      cancelBtn.classList.add('btn-primary');
      return true;
    }

    configAttributes.name = modal.dataset.configName;

    const response = await resilientFetch(buildApiUrl(`configs/${configId}`), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/vnd.api+json',
      },
      body: JSON.stringify(
        buildResourceDocument('configs', configId, configAttributes),
      ),
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

  // Map old task_type values to JSON:API types
  const typeMapping = {
    reset_image_count: 'reset_image_count_tasks',
    clear_cache: 'clear_cache_tasks',
    rescan_library: 'rescan_library_tasks',
  };
  const jsonApiType = typeMapping[taskType] || taskType;

  try {
    const response = await resilientFetch(buildApiUrl('tasks'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/vnd.api+json' },
      body: JSON.stringify({
        data: {
          type: jsonApiType,
          attributes: {},
        },
      }),
    });
    if (response.status === 429) return null;
    if (response.status === 409) {
      const data = await response.json();
      toast.classList.add('show');
      bar.style.width = '0%';
      text.textContent =
        data.errors?.[0]?.detail || data.detail || 'Task already running';
      setTimeout(() => toast.classList.remove('show'), 3000);
      return null;
    }
    if (!response.ok) throw new Error('Failed to start task');
    const data = await response.json();
    const task = data.data;
    pollTask(task.id, task.attributes.label);
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

// Registry of active poll controllers, keyed by task external ID.
// Prevents duplicate pollers for the same task within one browser page.
const _activePollers = new Map();

// Normal polling cadence after a successful response settles (milliseconds).
const POLL_INTERVAL_MS = 3000;

/**
 * Starts or replaces the poll controller for a given task.
 *
 * Maintains at most one active controller per task identifier. If a controller
 * already exists for the task, it is cancelled before the new one starts,
 * preventing duplicate concurrent pollers for the same task.
 *
 * The controller is self-scheduling: it issues one request, waits for it to
 * settle, then schedules the next iteration — never overlapping. On 429 it
 * schedules exactly one subsequent iteration after the Retry-After delay
 * without an internal retry chain. On a terminal response the controller
 * marks itself terminal before any UI work, cancelling all future scheduling
 * and suppressing stale continuations.
 *
 * @param {string} taskId - The task external identifier
 * @param {string} label  - Human-readable task label for the toast
 */
export function pollTask(taskId, label) {
  const toast = document.getElementById('task-toast');
  const bar = document.getElementById('task-toast-bar');
  const text = document.getElementById('task-toast-text');

  // Cancel any existing controller for this task ID before creating a new one.
  const existing = _activePollers.get(taskId);
  if (existing) {
    existing.cancel();
  }

  // Controller state
  const controller = {
    terminal: false,
    _timerId: null,
    cancel() {
      this.terminal = true;
      if (this._timerId !== null) {
        clearTimeout(this._timerId);
        this._timerId = null;
      }
      _activePollers.delete(taskId);
    },
  };

  _activePollers.set(taskId, controller);

  toast.classList.add('show');
  text.textContent = `${label} 0%`;
  bar.style.width = '0%';

  /**
   * Executes one poll iteration. Checks controller identity and terminal state
   * before issuing the request and before any UI mutation, preventing stale
   * continuations from a replaced or cancelled controller from having effects.
   */
  async function runIteration() {
    // Guard: do nothing if this controller has been superseded or cancelled.
    if (controller.terminal || _activePollers.get(taskId) !== controller) {
      return;
    }

    let response;
    try {
      response = await taskPollFetch(buildApiUrl(`tasks/${taskId}`));
    } catch {
      // Network failure: retain existing toast state, stop polling.
      if (!controller.terminal && _activePollers.get(taskId) === controller) {
        controller.cancel();
        toast.classList.remove('show');
      }
      return;
    }

    // Stale-continuation guard: check identity again after the async boundary.
    if (controller.terminal || _activePollers.get(taskId) !== controller) {
      return;
    }

    if (response.status === 429) {
      // Backoff: one subsequent iteration after Retry-After; no internal retry.
      const waitSeconds = parseRetryAfter(response);
      console.debug(
        `[pollTask:${taskId}] 429 received, scheduling next poll in ${waitSeconds}s`,
      );
      controller._timerId = setTimeout(() => {
        controller._timerId = null;
        runIteration();
      }, waitSeconds * 1000);
      return;
    }

    if (!response.ok) {
      // Unexpected non-429 error: retain current toast state, stop polling.
      controller.cancel();
      return;
    }

    let data;
    try {
      data = await response.json();
    } catch {
      controller.cancel();
      return;
    }

    // Stale-continuation guard: check identity again after JSON parsing.
    if (controller.terminal || _activePollers.get(taskId) !== controller) {
      return;
    }

    const task = data.data.attributes;

    if (task.status === 'completed' || task.status === 'failed') {
      // Mark terminal BEFORE any UI work to block all future scheduling.
      controller.cancel();
      if (task.status === 'completed') {
        bar.style.width = '100%';
        text.textContent = `${label} Done!`;
      } else {
        text.textContent = `${label} Failed: ${task.error}`;
      }
      setTimeout(() => toast.classList.remove('show'), 3000);
      return;
    }

    // Nonterminal success: update progress, schedule next iteration.
    bar.style.width = `${task.progress}%`;
    text.textContent = `${label} ${task.progress}%`;

    controller._timerId = setTimeout(() => {
      controller._timerId = null;
      runIteration();
    }, POLL_INTERVAL_MS);
  }

  // Schedule the first iteration.
  controller._timerId = setTimeout(() => {
    controller._timerId = null;
    runIteration();
  }, POLL_INTERVAL_MS);
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
    const doc = await fetchJsonApi(
      buildApiUrl(`plugins?page[number]=${page}`),
    );
    const { resources, meta, links } = unwrapResourceList(doc);

    body.innerHTML = resources
      .map((r) => {
        const p = { id: r.id, ...r.attributes };
        const isEnabled = enabledPlugins.includes(p.name);
        const checked = isEnabled ? 'checked' : '';
        return `<tr>
                <td>${p.name}</td>
                <td>${p.description || ''}</td>
                <td><button class="btn btn-secondary btn-sm plugin-configure-btn" data-id="${p.id}">Configure</button></td>
                <td><label class="toggle-switch plugin-toggle-wrap"><input type="checkbox" class="plugin-toggle" data-name="${p.name}" ${checked}><span class="slider"></span></label></td>
            </tr>`;
      })
      .join('');

    // Toggles only update local state — Save button does the PUT
    body.querySelectorAll('.plugin-toggle').forEach((toggle) => {
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
    body.querySelectorAll('.plugin-configure-btn').forEach((btn) => {
      btn.addEventListener('click', () => openPluginDetail(btn.dataset.id));
    });

    const count = meta.pagination?.count || resources.length;
    const pageSize = meta.pagination?.page_size || 5;
    const totalPages = Math.ceil(count / pageSize) || 1;
    info.textContent = `Page ${page} of ${totalPages}`;
    prev.disabled = !links.prev;
    next.disabled = !links.next;
  } catch {
    body.innerHTML = '<tr><td colspan="4">Failed to load plugins</td></tr>';
  }
}

export function validateCoordinates(value) {
  const trimmed = value.trim();
  if (trimmed === '') return true;

  const parts = trimmed.split(',');
  if (parts.length !== 2) return false;

  const latStr = parts[0].trim();
  const lonStr = parts[1].trim();
  if (latStr === '' || lonStr === '') return false;

  const lat = Number(latStr);
  const lon = Number(lonStr);
  if (isNaN(lat) || isNaN(lon)) return false;

  return lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
}

export const PLUGIN_ACTION_HANDLERS = {
  geolocation: (input) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'action-btn';
    btn.textContent = '📍';
    btn.title = 'Look up coordinates';
    btn.addEventListener('click', () => {
      window.open('https://www.latlong.net', '_blank');
      btn.textContent = '🌐';
      setTimeout(() => {
        btn.textContent = '📍';
      }, 1500);
    });

    return btn;
  },
};

async function openPluginDetail(pluginId) {
  const listView = document.getElementById('plugin-list-view');
  const detailView = document.getElementById('plugin-detail-view');
  const nameEl = document.getElementById('plugin-detail-name');
  const formEl = document.getElementById('plugin-detail-form');
  const saveBtn = document.getElementById('plugin-detail-save');

  // Reveals the detail region and wires its Back button. Both the loaded form
  // and a load failure need this, so a failure is visible and still escapable.
  const showDetailView = () => {
    listView.style.display = 'none';
    detailView.style.display = '';
    document.getElementById('main-actions').style.display = 'none';
    document.getElementById('plugin-detail-actions').style.display = '';

    const backBtn = document.getElementById('plugin-detail-back');
    const newBack = backBtn.cloneNode(true);
    backBtn.parentNode.replaceChild(newBack, backBtn);
    newBack.addEventListener('click', () => loadPlugins(pluginPage));
  };

  let doc;
  try {
    doc = await fetchJsonApi(buildApiUrl(`plugins/${pluginId}`));
  } catch (error) {
    nameEl.textContent = '';
    formEl.replaceChildren();
    reportError(error, {
      channel: 'view',
      fallback: 'Failed to load plugin settings.',
      target: formEl,
    });
    // Nothing to submit without the schema and current values.
    saveBtn.disabled = true;
    showDetailView();
    return;
  }

  const resource = unwrapResource(doc);
  if (!resource) return;
  const plugin = { id: resource.id, ...resource.attributes };

  saveBtn.disabled = false;
  nameEl.textContent = plugin.name;
  formEl.innerHTML = '';

  (plugin.settings_schema || []).forEach((field) => {
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
      (field.options || []).forEach((opt) => {
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

    if (field.type !== 'password' && field.type !== 'toggle')
      row.appendChild(input);

    if (field.action && PLUGIN_ACTION_HANDLERS[field.action]) {
      row.appendChild(PLUGIN_ACTION_HANDLERS[field.action](input));
    }

    div.appendChild(row);
    formEl.appendChild(div);
  });

  // Save handler
  const newSave = saveBtn.cloneNode(true);
  saveBtn.parentNode.replaceChild(newSave, saveBtn);
  newSave.addEventListener('click', async () => {
    // Validate coordinates field if present (weather plugin)
    const coordInput = formEl.querySelector('[data-key="coords"]');
    if (coordInput && !validateCoordinates(coordInput.value)) {
      const errorMessage = document.getElementById('error-message');
      errorMessage.textContent =
        'Invalid coordinates. Use lat,long format (e.g. 40.7128,-74.0060)';
      errorMessage.classList.add('show');
      newSave.disabled = true;
      setTimeout(() => {
        errorMessage.classList.remove('show');
        newSave.disabled = false;
      }, 3000);
      return;
    }

    const settings = {};
    formEl.querySelectorAll('.plugin-setting-input').forEach((el) => {
      settings[el.dataset.key] = el.type === 'checkbox' ? el.checked : el.value;
    });

    const requestDoc = buildResourceDocument('plugins', pluginId, { settings });
    try {
      await fetchJsonApi(buildApiUrl(`plugins/${pluginId}`), {
        method: 'PUT',
        body: JSON.stringify(requestDoc),
      });
    } catch (error) {
      reportError(error, {
        channel: 'form',
        fallback: 'Failed to save plugin settings.',
        disable: newSave,
      });
      return;
    }

    newSave.textContent = 'Saved!';
    setTimeout(() => {
      newSave.textContent = 'Save';
    }, 1500);

    const modal = document.getElementById('settings-modal');
    modal.dataset.changesSaved = 'true';
    const cancelBtn = document.getElementById('cancel-settings');
    cancelBtn.textContent = 'Reload Now';
    cancelBtn.classList.remove('btn-secondary');
    cancelBtn.classList.add('btn-primary');
  });

  showDetailView();
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
    const doc = await fetchJsonApi(
      buildApiUrl(`configs?page[number]=${page}`),
    );
    const { resources } = unwrapResourceList(doc);
    const configs = resources.map((r) => ({ id: r.id, ...r.attributes }));

    body.innerHTML = configs
      .map((c) => {
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
        const deleteBtn =
          !isManaged && !c.is_active
            ? `<button class="btn btn-secondary btn-sm task-delete-btn preset-delete-btn" data-id="${c.id}">&times;</button>`
            : isManaged
              ? `<span class="delete-disabled" title="System-managed configs cannot be deleted">🔒</span>`
              : `<span class="delete-disabled" title="Active config cannot be deleted">🔒</span>`;
        return `<tr>${nameCell}${descCell}<td>${status}</td><td>${deleteBtn}</td></tr>`;
      })
      .join('');

    body.querySelectorAll('.editable').forEach((cell) => {
      cell.dataset.original = cell.textContent.trim();
      const save = async () => {
        const value = cell.textContent.trim();
        if (value === cell.dataset.original) return;
        const id = cell.dataset.id;
        const field = cell.dataset.field;
        try {
          const getDoc = await fetchJsonApi(buildApiUrl(`configs/${id}`));
          const resource = unwrapResource(getDoc);
          if (!resource) return;
          const config = { id: resource.id, ...resource.attributes };
          config[field] = value;
          delete config.id;
          delete config.is_active;
          await resilientFetch(buildApiUrl(`configs/${id}`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/vnd.api+json' },
            body: JSON.stringify(buildResourceDocument('configs', id, config)),
          });
          cell.dataset.original = value;
        } catch (e) {
          console.error('Failed to save:', e);
        }
      };
      cell.addEventListener('blur', save);
      cell.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          cell.blur();
        }
      });
    });

    body.querySelectorAll('.preset-activate-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-inline"></span>';
        try {
          const configId = btn.dataset.id;
          // Fetch full config then send all attributes with is_active: true
          const getDoc = await fetchJsonApi(buildApiUrl(`configs/${configId}`));
          const resource = unwrapResource(getDoc);
          if (!resource) throw new Error('Config not found');
          const { id, is_active, ...attrs } = resource.attributes;
          const resp = await resilientFetch(buildApiUrl(`configs/${configId}`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/vnd.api+json' },
            body: JSON.stringify(
              buildResourceDocument('configs', configId, {
                ...attrs,
                is_active: true,
              }),
            ),
          });
          if (!resp.ok) throw new Error('Failed to activate');
          location.reload();
        } catch {
          btn.disabled = false;
          btn.textContent = 'Activate';
        }
      });
    });

    body.querySelectorAll('.preset-delete-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        await resilientFetch(buildApiUrl(`configs/${btn.dataset.id}`), {
          method: 'DELETE',
        });
        loadPresets(presetPage);
      });
    });

    const pagination = doc.meta?.pagination || {};
    const totalPages = pagination.pages || Math.ceil((pagination.count || 0) / 5) || 1;
    info.textContent = `Page ${page} of ${totalPages}`;
    prev.disabled = !doc.links?.prev;
    next.disabled = !doc.links?.next;
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
    const response = await resilientFetch(
      buildApiUrl(`tasks?page[number]=${page}`),
    );
    if (!response.ok) throw new Error('Failed to load tasks');
    const data = await response.json();

    body.innerHTML = data.data
      .map((t) => {
        const created = new Date(t.attributes.created).toLocaleString();
        return `<tr data-id="${t.id}"><td>${t.attributes.label}</td><td>${t.attributes.status}</td><td>${t.attributes.progress}%</td><td>${created}</td><td><button class="btn btn-secondary btn-sm task-delete-btn" data-id="${t.id}">&times;</button></td></tr>`;
      })
      .join('');

    body.querySelectorAll('.task-delete-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        await resilientFetch(buildApiUrl(`tasks/${btn.dataset.id}`), {
          method: 'DELETE',
        });
        loadTasks(taskPage);
      });
    });

    const totalPages = data.meta?.pagination?.pages || 1;
    const currentPage = data.meta?.pagination?.page || page;
    info.textContent = `Page ${currentPage} of ${totalPages}`;
    prev.disabled = !data.links?.prev;
    next.disabled = !data.links?.next;
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
    sections.forEach((s) => (s.style.display = 'none'));
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    activeTab.appendChild(spinner);
    await loadConfig();
    spinner.remove();
    sections.forEach((s) => (s.style.display = ''));

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

  tabBtns.forEach((btn) => {
    btn.addEventListener('click', async () => {
      const tabName = btn.dataset.tab;

      tabBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');

      document.querySelectorAll('.tab-content').forEach((content) => {
        content.classList.remove('active');
      });
      document.getElementById(`tab-${tabName}`).classList.add('active');

      // Always restore main action buttons and hide plugin detail when switching tabs
      document.getElementById('main-actions').style.display = '';
      document.getElementById('plugin-detail-actions').style.display = 'none';
      document.getElementById('plugin-detail-view').style.display = 'none';

      if (tabName === 'tasks') {
        const taskTab = document.getElementById('tab-tasks');
        const sections = taskTab.querySelectorAll(
          '.settings-section, .task-pagination',
        );
        sections.forEach((s) => (s.style.display = 'none'));
        const spinner = document.createElement('div');
        spinner.className = 'spinner';
        taskTab.appendChild(spinner);
        await loadTasks();
        spinner.remove();
        sections.forEach((s) => (s.style.display = ''));
      }

      if (tabName === 'presets') {
        const presetsTab = document.getElementById('tab-presets');
        const sections = presetsTab.querySelectorAll(
          '.settings-section, .preset-pagination',
        );
        sections.forEach((s) => (s.style.display = 'none'));
        const spinner = document.createElement('div');
        spinner.className = 'spinner';
        presetsTab.appendChild(spinner);
        await loadPresets();
        spinner.remove();
        sections.forEach((s) => (s.style.display = ''));
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
  document
    .getElementById('task-page-prev')
    .addEventListener('click', () => loadTasks(taskPage - 1));
  document
    .getElementById('task-page-next')
    .addEventListener('click', () => loadTasks(taskPage + 1));

  // Preset pagination buttons
  document
    .getElementById('preset-page-prev')
    .addEventListener('click', () => loadPresets(presetPage - 1));
  document
    .getElementById('preset-page-next')
    .addEventListener('click', () => loadPresets(presetPage + 1));

  // Plugin pagination buttons
  document
    .getElementById('plugin-page-prev')
    .addEventListener('click', () => loadPlugins(pluginPage - 1));
  document
    .getElementById('plugin-page-next')
    .addEventListener('click', () => loadPlugins(pluginPage + 1));

  // Library maintenance buttons
  document.getElementById('task-reset-count').addEventListener('click', () => {
    startTask('reset_image_count');
  });
  document.getElementById('task-clear-cache').addEventListener('click', () => {
    startTask('clear_cache');
  });
  document
    .getElementById('task-rescan-library')
    .addEventListener('click', () => {
      startTask('rescan_library');
    });
}
