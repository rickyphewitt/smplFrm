import {
  resilientFetch,
  taskPollFetch,
  parseRetryAfter,
} from './resilientFetch.js';
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
const CLOCK_REFRESH_MS = 1000;
const SPOTIFY_REFRESH_MS = 5000;
// Weather cadence. The backend refreshes on a 1800s beat and get_for_display()
// selects the sample for the current hour, so 5 minutes bounds hour-boundary
// lag, backend-refresh lag, and recovery from the degraded indicator to five
// minutes each. That is 12 attempts per hour per frame: one request each, or up
// to four while the endpoint is rate limited and resilientFetch retries
// internally. Doubles as the abort deadline for a single attempt, which is far
// longer than any retry chain a healthy backend produces.
export const WEATHER_REFRESH_MS = 300000;
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

/**
 * Replaces an element's content with an icon glyph followed by text.
 *
 * Builds the icon as a real `<i>` element and the text as a text node rather
 * than interpolating into `innerHTML`, so dynamic text (a formatted date, a
 * temperature string) is never parsed as markup regardless of its contents.
 *
 * @param {Element} element - The element to replace the contents of
 * @param {string} iconClass - Iconoir class, e.g. 'iconoir-camera'
 * @param {string} [text] - Text to render after the icon; omitted when falsy
 */
export function setIconText(element, iconClass, text) {
  const icon = document.createElement('i');
  icon.className = iconClass;
  if (text) {
    element.replaceChildren(icon, document.createTextNode(` ${text}`));
  } else {
    element.replaceChildren(icon);
  }
}

export function buildApiUrl(endpoint) {
  return `${config.host}:${config.port}/api/v1/${endpoint}`;
}

/** Body class replayed on every photo change; a styling hook for themes. */
export const PHOTO_CHANGED_CLASS = 'photo-changed';

/**
 * Replays the `photo-changed` class on `<body>` so a theme can animate the
 * frame overlay each time a new photo is shown, e.g.
 * `body.photo-changed #bottom-bar { animation: ... }`.
 *
 * CSS restarts an animation only when its selector stops and starts
 * matching, so the class is removed, a reflow is forced, and the class is
 * added back. The same hook fires for every theme; a theme that ignores the
 * class sees no change.
 */
export function markPhotoChanged() {
  const { body } = document;
  body.classList.remove(PHOTO_CHANGED_CLASS);
  void body.offsetWidth;
  body.classList.add(PHOTO_CHANGED_CLASS);
}

/** Body class set once the pointer has been still for CURSOR_IDLE_MS. */
export const CURSOR_IDLE_CLASS = 'cursor-idle';
export const CURSOR_IDLE_MS = 30000;

/**
 * Hides the mouse cursor once the pointer has been still for
 * CURSOR_IDLE_MS, so a mouse left over the frame does not sit on the photo.
 * Any movement or press shows it again and restarts the countdown, and so
 * does a click, which also covers opening the settings panel from the
 * keyboard. The cursor is never hidden while the settings panel is open.
 *
 * Only the `cursor-idle` class on `<body>` is toggled; base.css turns it
 * into `cursor: none`, so every theme gets the same behaviour.
 *
 * Returns a function that removes the listeners and the pending timer and
 * shows the cursor again.
 */
export function initIdleCursor() {
  const { body } = document;
  const events = ['pointermove', 'pointerdown', 'click'];
  let timer;

  const hide = () => {
    const modal = document.getElementById('settings-modal');
    if (modal && modal.classList.contains('open')) {
      timer = setTimeout(hide, CURSOR_IDLE_MS);
      return;
    }
    body.classList.add(CURSOR_IDLE_CLASS);
  };

  const wake = () => {
    body.classList.remove(CURSOR_IDLE_CLASS);
    clearTimeout(timer);
    timer = setTimeout(hide, CURSOR_IDLE_MS);
  };

  events.forEach((type) =>
    document.addEventListener(type, wake, { passive: true }),
  );
  wake();

  return () => {
    clearTimeout(timer);
    events.forEach((type) => document.removeEventListener(type, wake));
    body.classList.remove(CURSOR_IDLE_CLASS);
  };
}

export function startProgress() {
  let width = 100;
  const interval = setInterval(() => {
    width -= 1;
    if (width <= 0) {
      clearInterval(interval);
      width = 0;
    }
    progressBar.style.setProperty('--progress', width / 100);
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
      buildApiUrl(`images?sort=display_priority&page[number]=${currentPage}`),
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
      .map((r) => ({ id: r.id, ...r.attributes }))
      .filter((img) => !imageQueue.find((q) => q.id === img.id));

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
    const imageIds = newImages.map((img) => img.id);
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
      currentPage = 1;
    }
    reportError(error, {
      channel: 'silent',
      fallback: 'Image queue refill failed, will retry.',
    });
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
        Accept: 'application/vnd.api+json',
      },
      body: JSON.stringify(payload),
    });

    // Preload is best-effort: a conflict, a capacity limit, a rate limit, or any
    // other rejection all mean the display carries on with uncached images.
    if (!response.ok) {
      reportError(new JsonApiError(response.status, []), {
        channel: 'silent',
        fallback: 'Preload request failed, continuing without preload.',
      });
    }
  } catch (error) {
    // Non-critical failure - display continues with uncached images
    reportError(error, {
      channel: 'silent',
      fallback: 'Preload request failed, continuing without preload.',
    });
  }
}

async function displayMetadata(imageId) {
  if (!config.displayDate) return;

  try {
    const response = await resilientFetch(
      buildApiUrl(`images_metadata?filter[image]=${imageId}`),
    );
    if (!response.ok) {
      // Rate limiting is already reported globally, and the date is left as-is
      // so the next image can try again.
      if (response.status === 429) return;
      throw new JsonApiError(response.status, []);
    }

    const data = await response.json();
    // Unwrap JSON:API response
    const { resources } = unwrapResourceList(data);
    if (resources.length === 0) {
      setIconText(document.getElementById('photo-date'), 'iconoir-camera');
      return;
    }

    const takenDate = Date.parse(resources[0].attributes.taken);

    if (isNaN(takenDate)) {
      setIconText(document.getElementById('photo-date'), 'iconoir-camera');
    } else {
      const prettyDate = new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'long',
      }).format(takenDate);
      setIconText(
        document.getElementById('photo-date'),
        'iconoir-camera',
        prettyDate,
      );
    }
  } catch (error) {
    reportError(error, {
      channel: 'silent',
      fallback: 'Image metadata unavailable.',
    });
    setIconText(document.getElementById('photo-date'), 'iconoir-camera');
  }
}

/**
 * Updates the overlay for a newly shown photo, then signals the change.
 *
 * The `photo-changed` hook is replayed only once the photo date is in place,
 * so a theme's entrance animation never reveals the previous photo's date.
 * displayMetadata() handles its own errors, so the hook fires on every photo.
 *
 * @param {string} imageId - External id of the photo now on screen
 * @returns {Promise<void>}
 */
export function refreshPhotoOverlay(imageId) {
  return displayMetadata(imageId).finally(markPhotoChanged);
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
        refreshPhotoOverlay(newImage.getAttribute(IMAGE_ID_ATTR));
        startProgress();
        loadNext(newImage);
      }, config.refreshInterval);
    };
  } catch {
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
      refreshPhotoOverlay(newImage.getAttribute(IMAGE_ID_ATTR));
      startProgress();
      loadNext(newImage);
    };
  } catch {
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
  setIconText(
    document.getElementById('current-date'),
    'iconoir-calendar',
    currentDate,
  );

  // Display current time without seconds
  const timeString = now.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
  setIconText(
    document.getElementById('current-time'),
    'iconoir-clock',
    timeString,
  );

  setTimeout(displayClock, CLOCK_REFRESH_MS);
}

/**
 * Performs one weather fetch and renders the result.
 *
 * Returns the underlying promise so a caller can wait for the attempt to
 * settle before scheduling another one. Resolves either way: a failure is
 * reported through the indicator channel rather than propagated.
 *
 * @param {Object} [options]
 * @param {AbortSignal} [options.signal] - Cancels the in-flight request. An
 *   abort is reported like any other failure, so the slot degrades.
 * @returns {Promise<void>|undefined} Settles when the attempt completes;
 *   undefined when the weather plugin is disabled and no request is made.
 */
export function displayWeather({ signal } = {}) {
  const weatherGroup = document.getElementById('weather-group');
  if (!config.plugins || !config.plugins.includes('weather')) {
    weatherGroup.style.display = 'none';
    return;
  }
  // Fetch weather data from plugin API (JSON:API format)
  return fetchJsonApi(buildApiUrl('plugins/weather/current'), { signal })
    .then((jsonApiDoc) => {
      const resource = unwrapResource(jsonApiDoc);
      if (resource && resource.attributes) {
        const { temperature, temperature_scale } = resource.attributes;
        const formatted = formatWeatherTemp(temperature, temperature_scale);
        setIconText(
          document.getElementById('weather-temp'),
          'iconoir-temperature-high',
          formatted,
        );
      }
    })
    .catch((error) => {
      // A failure leaves the slot in an unavailable state rather than blank,
      // which is indistinguishable from the plugin being disabled. The refresh
      // loop clears it on the next successful attempt. The group stays visible
      // for the same reason.
      reportError(error, {
        channel: 'indicator',
        fallback: 'Weather is unavailable.',
        onDegrade: () => {
          const target = document.getElementById('weather-temp');
          const tempIcon = document.createElement('i');
          tempIcon.className = 'iconoir-temperature-high';
          const warnIcon = document.createElement('i');
          warnIcon.className = 'iconoir-warning-triangle weather-warning-icon';
          target.replaceChildren(
            tempIcon,
            document.createTextNode(' '),
            warnIcon,
          );
        },
      });
    });
}

// Whether a refresh chain already owns the weather slot. Since a chain
// schedules its next attempt only after the current one settles, this flag is
// the whole guard: without it, two synchronous entries would each fire an
// immediate request and leave two permanent chains.
let _weatherLoopRunning = false;

/**
 * Starts the weather refresh loop, or does nothing if it is already running.
 *
 * Self-scheduling and non-overlapping: the next attempt is scheduled only once
 * the current one settles, so resilientFetch's internal 429 retry chain is
 * never outrun and a failing endpoint is never amplified. Because settlement
 * drives scheduling, an attempt that never settles on its own would stall the
 * loop for the life of the page; each attempt is therefore aborted after
 * WEATHER_REFRESH_MS, which caps the gap a stalled request can open at two
 * intervals rather than forever. Failures, including that abort, do not end the
 * loop. Does not start when the weather plugin is disabled, in which case the
 * single displayWeather() call still hides the group before updateSeparators()
 * measures it.
 */
export function refreshWeather() {
  if (_weatherLoopRunning) {
    return;
  }

  const controller = new AbortController();
  const attempt = displayWeather({ signal: controller.signal });
  if (!attempt) {
    // Plugin disabled: the group is hidden and there is nothing to poll.
    return;
  }

  _weatherLoopRunning = true;

  const deadlineId = setTimeout(() => controller.abort(), WEATHER_REFRESH_MS);

  const scheduleNext = () => {
    clearTimeout(deadlineId);
    setTimeout(() => {
      _weatherLoopRunning = false;
      refreshWeather();
    }, WEATHER_REFRESH_MS);
  };

  // Both settlement paths schedule. displayWeather resolves even on failure, so
  // a rejection here means its own reporting threw; the loop has to outlive
  // that, and the rejection must not reach the global handler as a user toast.
  attempt.then(scheduleNext, (error) => {
    console.debug('[weather] refresh attempt rejected unexpectedly', error);
    scheduleNext();
  });
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
  const label = reconnect ? 'Expired - Reconnect Spotify' : 'Connect Spotify';
  const tooltip = reconnect
    ? 'Spotify connection expired - Click to reconnect'
    : 'Connect Spotify';
  const link = document.createElement('a');
  link.href = authUrl;
  link.title = tooltip;
  link.className = reconnect
    ? 'spotify-reconnect-link'
    : 'spotify-connect-link';

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
    // Any failure here (429, 500, 503) leaves the bar in its icon-only state.
    // The render is unconditional rather than driven by the reporter, because a
    // suppressed 429 must not leave stale track text on the bar.
    reportError(error, {
      channel: 'indicator',
      fallback: 'Spotify authorization is unavailable.',
    });
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

    reportError(error, {
      channel: 'indicator',
      fallback: 'Spotify is unavailable.',
      onDegrade: () => {
        if (!spotifyAuthLinkActive) {
          showSpotifyBar(`<i class="iconoir-spotify spotify-icon"></i>`);
        }
      },
    });
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
  initIdleCursor();
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

  refreshWeather();

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

/**
 * Theme control state, scoped to the module so loadConfig() and
 * loadThemeOptions() can settle in either order without deciding the
 * selected value by timing.
 *
 * The stored theme travels through `_pendingStoredTheme` until options
 * exist; applying `.value` to a <select> with no matching <option> silently
 * leaves the first option selected, and a later save would then persist
 * that as the user's choice. `_themeOptionsLoaded` guards against applying
 * the stored value before any option exists at all, and
 * `_themesFetchFailed` records that the registry is unknown so the stored
 * id can still be offered as the sole option whenever it arrives.
 */
let _pendingStoredTheme = null;
let _themeOptionsLoaded = false;
let _themesFetchFailed = false;

/**
 * Applies the stored theme to #setting-theme once options exist.
 *
 * Safe to call from either loadConfig() or loadThemeOptions(), in either
 * order: the first call to supply both a stored value and a populated
 * select wins, and later calls are no-ops once applied.
 *
 * When the themes fetch failed, this also builds the degraded single-option
 * control. That has to happen here rather than only in the fetch's catch
 * block: the failure can settle before the config response, and at that
 * point the stored id is not known yet. Leaving the select empty in that
 * ordering would make every save submit `theme: ""`, which the serializer
 * rejects, blocking saves of unrelated settings.
 */
function applyPendingStoredTheme() {
  if (!_themeOptionsLoaded || _pendingStoredTheme == null) {
    return;
  }
  const select = document.getElementById('setting-theme');
  const hasOption = Array.from(select.options).some(
    (opt) => opt.value === _pendingStoredTheme,
  );
  if (hasOption) {
    select.value = _pendingStoredTheme;
    return;
  }
  if (_themesFetchFailed) {
    // The only id we can offer is the one the config already stores, so a
    // save cannot change the theme by accident even though the control
    // still "works". The id is shown alongside the label because it is the
    // only name available without the registry.
    const option = document.createElement('option');
    option.value = _pendingStoredTheme;
    option.textContent = `Current theme (${_pendingStoredTheme})`;
    select.replaceChildren(option);
    select.value = _pendingStoredTheme;
  }
}

/**
 * Fetches the themes collection and populates #setting-theme.
 *
 * Follows `links.next` until exhausted so the dropdown is complete
 * regardless of page size, capped at ten pages so a pathological response
 * cannot hammer a throttled endpoint. On failure, degrades to a single
 * option showing the currently stored theme and reports through the
 * view-placeholder channel; a themes failure never blocks saving unrelated
 * settings.
 */
export async function loadThemeOptions() {
  const select = document.getElementById('setting-theme');
  const modal = document.getElementById('settings-modal');
  const MAX_PAGES = 10;

  const themes = [];
  let url = buildApiUrl('themes');
  let pagesFetched = 0;

  try {
    while (url && pagesFetched < MAX_PAGES) {
      const doc = await fetchJsonApi(url);
      const { resources, links } = unwrapResourceList(doc);
      themes.push(...resources.map((r) => ({ id: r.id, ...r.attributes })));
      pagesFetched++;
      url = links.next || null;
    }
    if (url && pagesFetched >= MAX_PAGES) {
      console.debug(
        '[loadThemeOptions] stopped at the ten-page cap with more pages remaining',
      );
    }

    select.replaceChildren(
      ...themes.map((theme) => {
        const option = document.createElement('option');
        option.value = theme.id;
        option.textContent = theme.label;
        if (theme.description) {
          option.title = theme.description;
        }
        return option;
      }),
    );
    _themeOptionsLoaded = true;
    _themesFetchFailed = false;
    applyPendingStoredTheme();
  } catch (error) {
    // Degraded state: the stored theme becomes the only option, applied here
    // if it is already known and by the next applyPendingStoredTheme() call
    // if the config load has not settled yet.
    select.replaceChildren();
    _themeOptionsLoaded = true;
    _themesFetchFailed = true;
    applyPendingStoredTheme();
    reportError(error, {
      channel: 'view',
      fallback: 'Failed to load themes.',
      target: settingsBody(modal),
    });
  }
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
    _pendingStoredTheme = config.theme;
    applyPendingStoredTheme();

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
    theme: document.getElementById('setting-theme').value,
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

    await fetchJsonApi(buildApiUrl(`configs/${configId}`), {
      method: 'PUT',
      body: JSON.stringify(
        buildResourceDocument('configs', configId, configAttributes),
      ),
    });

    console.log('Settings saved successfully');

    // Mark that changes were saved
    modal.dataset.changesSaved = 'true';

    // Change cancel button to reload button
    cancelBtn.textContent = 'Reload Now';
    cancelBtn.classList.remove('btn-secondary');
    cancelBtn.classList.add('btn-primary');

    return true;
  } catch (error) {
    reportError(error, {
      channel: 'form',
      fallback: 'Failed to save settings.',
      disable: document.getElementById('save-settings'),
    });

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
    const data = await fetchJsonApi(buildApiUrl('tasks'), {
      method: 'POST',
      body: JSON.stringify({
        data: {
          type: jsonApiType,
          attributes: {},
        },
      }),
    });
    const task = data.data;
    pollTask(task.id, task.attributes.label);
    return task;
  } catch (error) {
    // A conflict means a task of this type is already pending or running, so
    // the reason belongs on the task toast next to that task's progress.
    if (error instanceof JsonApiError && error.status === 409) {
      toast.classList.add('show');
      bar.style.width = '0%';
      text.textContent = error.errors?.[0]?.detail || 'Task already running';
      setTimeout(() => toast.classList.remove('show'), 3000);
      return null;
    }

    reportError(error, {
      channel: 'action',
      fallback: 'Failed to start task',
    });
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
    const doc = await fetchJsonApi(buildApiUrl(`plugins?page[number]=${page}`));
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
  } catch (error) {
    reportError(error, {
      channel: 'view',
      fallback: 'Failed to load plugins',
      target: body,
      colspan: 4,
    });
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
  geolocation: (_input) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'action-btn';
    setIconText(btn, 'iconoir-map-pin');
    btn.title = 'Look up coordinates';
    btn.setAttribute('aria-label', 'Look up coordinates');
    btn.addEventListener('click', () => {
      window.open('https://www.latlong.net', '_blank');
      setIconText(btn, 'iconoir-globe');
      setTimeout(() => {
        setIconText(btn, 'iconoir-map-pin');
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
        setIconText(reveal, 'iconoir-eye');
        reveal.setAttribute('aria-label', 'Show password');
        reveal.addEventListener('click', () => {
          const nowVisible = input.type === 'password';
          input.type = nowVisible ? 'text' : 'password';
          reveal.setAttribute(
            'aria-label',
            nowVisible ? 'Hide password' : 'Show password',
          );
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

/**
 * Builds one preset table cell, editable for custom configs only.
 *
 * The value is set with `textContent`, so a config name or description is
 * never parsed as markup — these strings come back from the API and are
 * writable through PUT /configs/{id}.
 */
function buildPresetCell(config, field, value, isManaged) {
  const cell = document.createElement('td');
  cell.textContent = value;
  if (!isManaged) {
    cell.className = 'editable';
    cell.setAttribute('contenteditable', 'true');
    cell.dataset.id = config.id;
    cell.dataset.field = field;
  }
  return cell;
}

/** Builds the Status cell: an Active badge, or an Activate button. */
function buildPresetStatusCell(config) {
  const cell = document.createElement('td');
  if (config.is_active) {
    const badge = document.createElement('span');
    badge.className = 'badge-active';
    badge.textContent = 'Active';
    cell.appendChild(badge);
    return cell;
  }
  const activate = document.createElement('button');
  activate.className = 'btn btn-secondary btn-sm preset-activate-btn';
  activate.dataset.id = config.id;
  activate.textContent = 'Activate';
  cell.appendChild(activate);
  return cell;
}

/** Builds the Delete cell: a delete button, or a lock glyph with a reason. */
function buildPresetDeleteCell(config, isManaged) {
  const cell = document.createElement('td');

  if (!isManaged && !config.is_active) {
    const button = document.createElement('button');
    button.className =
      'btn btn-secondary btn-sm task-delete-btn preset-delete-btn';
    button.dataset.id = config.id;
    button.textContent = '\u00d7';
    button.setAttribute('aria-label', `Delete preset ${config.name}`);
    cell.appendChild(button);
    return cell;
  }

  const locked = document.createElement('span');
  locked.className = 'delete-disabled';
  locked.title = isManaged
    ? 'System-managed configs cannot be deleted'
    : 'Active config cannot be deleted';
  const icon = document.createElement('i');
  icon.className = 'iconoir-lock';
  locked.appendChild(icon);
  cell.appendChild(locked);
  return cell;
}

export async function loadPresets(page = 1) {
  presetPage = page;
  const body = document.getElementById('preset-list-body');
  const prev = document.getElementById('preset-page-prev');
  const next = document.getElementById('preset-page-next');
  const info = document.getElementById('preset-page-info');

  try {
    const doc = await fetchJsonApi(buildApiUrl(`configs?page[number]=${page}`));
    const { resources } = unwrapResourceList(doc);
    const configs = resources.map((r) => ({ id: r.id, ...r.attributes }));

    body.replaceChildren(
      ...configs.map((c) => {
        const isManaged = c.name.startsWith('smplFrm ');
        const row = document.createElement('tr');
        row.append(
          buildPresetCell(c, 'name', c.name, isManaged),
          buildPresetCell(c, 'description', c.description || '', isManaged),
          buildPresetStatusCell(c),
          buildPresetDeleteCell(c, isManaged),
        );
        return row;
      }),
    );

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
          await fetchJsonApi(buildApiUrl(`configs/${id}`), {
            method: 'PUT',
            body: JSON.stringify(buildResourceDocument('configs', id, config)),
          });
          cell.dataset.original = value;
        } catch (error) {
          // The cell holds the rejected text, so it has to go back to the last
          // value the server accepted or the row would misreport the config.
          cell.textContent = cell.dataset.original;
          reportError(error, {
            channel: 'form',
            fallback: 'Failed to save the change.',
          });
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
          await fetchJsonApi(buildApiUrl(`configs/${configId}`), {
            method: 'PUT',
            body: JSON.stringify(
              buildResourceDocument('configs', configId, {
                ...attrs,
                is_active: true,
              }),
            ),
          });
          location.reload();
        } catch (error) {
          btn.disabled = false;
          btn.textContent = 'Activate';
          reportError(error, {
            channel: 'action',
            fallback: 'Failed to activate the preset.',
          });
        }
      });
    });

    body.querySelectorAll('.preset-delete-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        try {
          await fetchJsonApi(buildApiUrl(`configs/${btn.dataset.id}`), {
            method: 'DELETE',
          });
        } catch (error) {
          // Reloading here would redraw the same row and imply the delete
          // worked, so the list is left as-is on failure.
          reportError(error, {
            channel: 'action',
            fallback: 'Failed to delete the preset.',
          });
          return;
        }
        loadPresets(presetPage);
      });
    });

    const pagination = doc.meta?.pagination || {};
    const totalPages =
      pagination.pages || Math.ceil((pagination.count || 0) / 5) || 1;
    info.textContent = `Page ${page} of ${totalPages}`;
    prev.disabled = !doc.links?.prev;
    next.disabled = !doc.links?.next;
  } catch (error) {
    reportError(error, {
      channel: 'view',
      fallback: 'Failed to load presets',
      target: body,
      colspan: 4,
    });
  }
}

export async function loadTasks(page = 1) {
  taskPage = page;
  const body = document.getElementById('task-list-body');
  const prev = document.getElementById('task-page-prev');
  const next = document.getElementById('task-page-next');
  const info = document.getElementById('task-page-info');

  try {
    const data = await fetchJsonApi(buildApiUrl(`tasks?page[number]=${page}`));

    body.replaceChildren(
      ...data.data.map((t) => {
        const { label, status, progress, created } = t.attributes;
        const row = document.createElement('tr');
        row.dataset.id = t.id;

        // textContent for every value: the label is server-supplied text,
        // not markup.
        const cells = [
          label,
          status,
          `${progress}%`,
          new Date(created).toLocaleString(),
        ];
        cells.forEach((text) => {
          const cell = document.createElement('td');
          cell.textContent = text;
          row.appendChild(cell);
        });

        const deleteCell = document.createElement('td');
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-secondary btn-sm task-delete-btn';
        deleteBtn.dataset.id = t.id;
        deleteBtn.textContent = '\u00d7';
        deleteBtn.setAttribute('aria-label', `Delete task ${label}`);
        deleteCell.appendChild(deleteBtn);
        row.appendChild(deleteCell);

        return row;
      }),
    );

    body.querySelectorAll('.task-delete-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        try {
          await fetchJsonApi(buildApiUrl(`tasks/${btn.dataset.id}`), {
            method: 'DELETE',
          });
        } catch (error) {
          // Same reasoning as preset delete: no reload on failure, or the row
          // reappears and looks like a successful delete that did not happen.
          reportError(error, {
            channel: 'action',
            fallback: 'Failed to delete the task.',
          });
          return;
        }
        loadTasks(taskPage);
      });
    });

    const totalPages = data.meta?.pagination?.pages || 1;
    const currentPage = data.meta?.pagination?.page || page;
    info.textContent = `Page ${currentPage} of ${totalPages}`;
    prev.disabled = !data.links?.prev;
    next.disabled = !data.links?.next;
  } catch (error) {
    reportError(error, {
      channel: 'view',
      fallback: 'Failed to load tasks',
      target: body,
      colspan: 5,
    });
  }
}

/**
 * Returns the focusable elements inside a container, in DOM order.
 *
 * Used to build the Tab-cycling focus trap for the settings modal. Scoped to
 * a conservative, commonly-focusable selector set rather than every possible
 * focusable element, which is sufficient for the modal's actual content
 * (buttons, inputs, selects, links, and the close control).
 *
 * Two hiding mechanisms have to be honoured, and neither can be read from a
 * computed style: jsdom does not resolve stylesheet rules, and
 * `offsetParent` requires a layout engine.
 *
 * - Inactive tab panels are hidden by the `.tab-content { display: none }`
 *   class rule in base.css, so their controls are excluded by panel
 *   membership: an element inside a `.tab-content` that lacks `.active` is
 *   not reachable.
 * - The plugin detail view, its action bar, and the main action bar are
 *   toggled with inline `style.display`, so those are excluded by walking
 *   ancestors for an inline `display: none` or a `hidden` attribute.
 *
 * @param {Element} container
 * @returns {Element[]}
 */
export function getFocusableElements(container) {
  const selector = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(',');

  const isInInactiveTabPanel = (el) => {
    const panel = el.closest('.tab-content');
    return panel !== null && !panel.classList.contains('active');
  };

  const isVisible = (el) => {
    let node = el;
    while (node && node !== container.parentElement) {
      if (node.style && node.style.display === 'none') {
        return false;
      }
      if (node.hasAttribute && node.hasAttribute('hidden')) {
        return false;
      }
      node = node.parentElement;
    }
    return true;
  };

  return Array.from(container.querySelectorAll(selector)).filter(
    (el) => !isInInactiveTabPanel(el) && isVisible(el),
  );
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

    // Focus moves into the panel on open, immediately rather than after the
    // config load below settles. The close button is always present and
    // visible regardless of which tab or load state is active, so it is a
    // safe first-focus target.
    closeBtn.focus();

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
    // Reset per-open theme-control state so a stale value from a previous
    // open cannot leak into this one; the stored theme and the themes
    // collection are fetched in parallel and may settle in either order.
    _pendingStoredTheme = null;
    _themeOptionsLoaded = false;
    _themesFetchFailed = false;
    await Promise.all([loadConfig(), loadThemeOptions()]);
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
      // Focus returns to the control that opened the modal.
      logoIcon.focus();
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
    if (!modal.classList.contains('open')) {
      return;
    }

    if (e.key === 'Escape') {
      closeModal();
      return;
    }

    // Focus trap: Tab and Shift+Tab cycle within the modal's focusable
    // elements instead of escaping to the rest of the page.
    if (e.key === 'Tab') {
      const focusable = getFocusableElements(modal);
      if (focusable.length === 0) {
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
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
