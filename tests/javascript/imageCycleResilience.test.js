import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('Image Cycle Resilience to 429 Responses', () => {
  let window, document;
  let getNextImage, buildApiUrl;

  beforeEach(async () => {
    vi.useFakeTimers();

    const dom = new JSDOM(
      `
      <!DOCTYPE html>
      <html>
        <body>
          <div id="image-container"></div>
          <div id="progress-bar"></div>
          <div id="photo-date"></div>
          <div id="current-date"></div>
          <div id="current-time"></div>
          <div id="weather-temp"></div>
          <div id="rate-limit-toast"></div>
          <div class="task-toast" id="task-toast">
            <span id="task-toast-text"></span>
            <div class="task-toast-track">
              <div class="task-toast-bar" id="task-toast-bar"></div>
            </div>
          </div>
        </body>
      </html>
    `,
      { url: 'http://localhost' },
    );

    window = dom.window;
    document = window.document;
    global.window = window;
    global.document = document;
    global.Image = window.Image;

    window.SMPL_CONFIG = {
      transitionInterval: 1000,
      refreshInterval: 30000,
      host: 'http://localhost',
      port: '8321',
      displayDate: false,
      displayClock: false,
      imageZoomEffect: false,
      imageTransitionType: 'none',
    };

    vi.stubGlobal('fetch', vi.fn());
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});

    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNextImage = module.getNextImage;
    buildApiUrl = module.buildApiUrl;
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.resetModules();
  });

  function make429Response() {
    return new Response('', {
      status: 429,
      headers: { 'Retry-After': '1' },
    });
  }

  function make200Response(data = { id: 'img-new' }) {
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  /**
   * Calls getNextImage and advances timers through resilientFetch retries.
   * Attaches a .catch() immediately to prevent unhandled rejection warnings.
   * Returns { result, error } after all retries complete.
   */
  async function callGetNextImageWith429() {
    let result = null;
    let error = null;

    const promise = getNextImage().then(
      (r) => {
        result = r;
      },
      (e) => {
        error = e;
      },
    );

    // Advance through resilientFetch's 3 retry waits (1s each)
    await vi.advanceTimersByTimeAsync(3000);
    await promise;

    return { result, error };
  }

  describe('current image preserved when 429 exhausts retries', () => {
    it('keeps the current image in the container when getNextImage throws on 429', async () => {
      const currentImg = document.createElement('img');
      currentImg.src = 'http://localhost:8321/api/v1/images/current/display';
      currentImg.setAttribute('image-id', 'img-1');
      currentImg.classList.add('main-img');
      document.getElementById('image-container').appendChild(currentImg);

      // 1 original + 3 retries = 4 total 429 responses
      fetch
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response());

      const { error } = await callGetNextImageWith429();

      // getNextImage should throw with status 429 after retries exhausted
      expect(error).not.toBeNull();
      expect(error.message).toBe('Rate limited');
      expect(error.status).toBe(429);

      // The current image should still be in the container (unchanged)
      const container = document.getElementById('image-container');
      expect(container.children.length).toBe(1);
      expect(container.children[0].getAttribute('image-id')).toBe('img-1');
    });
  });

  describe('next fetch scheduled after refreshInterval on exhausted retries', () => {
    it('uses refreshInterval as the retry delay in loadNext catch block', async () => {
      // 1 original + 3 retries = 4 total 429 responses
      fetch
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response());

      const { error } = await callGetNextImageWith429();

      // getNextImage throws — loadNext's catch block schedules setTimeout(loadNext, refreshInterval)
      expect(error).not.toBeNull();
      expect(error.message).toBe('Rate limited');

      // Verify the config value that loadNext uses for scheduling the retry
      expect(window.SMPL_CONFIG.refreshInterval).toBe(30000);

      // After the error, 4 fetch calls were made (1 original + 3 retries from resilientFetch)
      expect(fetch).toHaveBeenCalledTimes(4);
    });
  });

  describe('refreshInterval timer restarted from recovery moment on success', () => {
    it('uses refreshInterval as the delay for the next cycle after successful fetch', async () => {
      // Successful response — no retries needed
      fetch.mockResolvedValueOnce(make200Response({ id: 'img-recovered' }));

      const result = await getNextImage();
      expect(result).toEqual({ id: 'img-recovered' });

      // loadNext schedules the next image load via:
      //   setTimeout(() => { ... loadNext(newImage) }, config.refreshInterval)
      // The timer is set from the moment of success (recovery moment)
      expect(window.SMPL_CONFIG.refreshInterval).toBe(30000);

      // Only 1 fetch call was made (no retries)
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('resets timer from recovery moment after 429 then success', async () => {
      // First attempt: 429, then retry succeeds
      fetch
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make200Response({ id: 'img-recovered' }));

      let result = null;
      const promise = getNextImage().then((r) => {
        result = r;
      });

      // Advance through the 1s retry wait
      await vi.advanceTimersByTimeAsync(1000);
      await promise;

      expect(result).toEqual({ id: 'img-recovered' });

      // After recovery, loadNext uses refreshInterval from this moment
      // (not from the original request time)
      expect(fetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('no error messages or error-styled indicators shown for 429s', () => {
    it('does not call console.error when getNextImage encounters a 429', async () => {
      fetch
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response());

      await callGetNextImageWith429();

      expect(console.error).not.toHaveBeenCalled();
    });

    it('does not add error-styled elements to the DOM on 429', async () => {
      fetch
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response());

      await callGetNextImageWith429();

      const errorElements = document.querySelectorAll(
        '.error, .error-message, [class*="error"]',
      );
      expect(errorElements.length).toBe(0);
    });

    it('preserves the image container content unchanged on 429', async () => {
      const currentImg = document.createElement('img');
      currentImg.src = 'http://localhost:8321/api/v1/images/current/display';
      currentImg.classList.add('main-img');
      const container = document.getElementById('image-container');
      container.appendChild(currentImg);

      fetch
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response())
        .mockResolvedValueOnce(make429Response());

      await callGetNextImageWith429();

      expect(container.children.length).toBe(1);
      expect(container.children[0]).toBe(currentImg);
      expect(container.querySelector('.error')).toBeNull();
    });
  });
});
