import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('main.js', () => {
  let window, document;
  let buildApiUrl, getWindowDimensions, fadeInImage, getNextImage, applyTransition, getRandomTransition, startTask;

  beforeEach(async () => {
    const dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="image-container"></div>
          <div id="progress-bar"></div>
          <div id="photo-date"></div>
          <div id="current-date"></div>
          <div id="current-time"></div>
          <div id="weather-temp"></div>
          <div class="task-toast" id="task-toast">
            <span id="task-toast-text"></span>
            <div class="task-toast-track">
              <div class="task-toast-bar" id="task-toast-bar"></div>
            </div>
          </div>
        </body>
      </html>
    `, { url: 'http://localhost' });

    window = dom.window;
    document = window.document;
    global.window = window;
    global.document = document;
    global.Image = window.Image;

    window.SMPL_CONFIG = {
      transitionInterval: 1000,
      refreshInterval: 3000,
      host: 'http://localhost',
      port: '8321',
      displayDate: true,
      displayClock: false,
      pluginSpotifyEnabled: false,
      weatherCurrentTemp: '72°F',
      imageZoomEffect: true,
      imageTransitionType: 'fade'
    };

    // Import functions after setting up globals
    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    buildApiUrl = module.buildApiUrl;
    getWindowDimensions = module.getWindowDimensions;
    fadeInImage = module.fadeInImage;
    getNextImage = module.getNextImage;
    applyTransition = module.applyTransition;
    getRandomTransition = module.getRandomTransition;
    startTask = module.startTask;
  });

  describe('buildApiUrl', () => {
    it('constructs correct API URL', () => {
      const url = buildApiUrl('images/next');
      expect(url).toBe('http://localhost:8321/api/v1/images/next');
    });

    it('handles endpoints with query params', () => {
      const url = buildApiUrl('images/next?width=1920&height=1080');
      expect(url).toBe('http://localhost:8321/api/v1/images/next?width=1920&height=1080');
    });
  });

  describe('getWindowDimensions', () => {
    it('returns window dimensions', () => {
      window.innerWidth = 1920;
      window.innerHeight = 1080;
      const dims = getWindowDimensions();
      expect(dims).toEqual({ width: 1920, height: 1080 });
    });
  });

  describe('fadeInImage', () => {
    beforeEach(() => {
      vi.useFakeTimers();
      // Reset config
      window.SMPL_CONFIG.imageZoomEffect = true;
    });

    it('applies zoom animation after fade completes when enabled', () => {
      const img = document.createElement('img');
      img.style.opacity = '0';
      let completed = false;

      fadeInImage(img, () => {
        completed = true;
      });

      // Fast-forward through fade-in
      vi.advanceTimersByTime(1000);

      expect(img.style.animation).toContain('zoomIn');
      expect(img.style.animation).toContain('3s');
      expect(completed).toBe(true);
    });

    it('applies fade transition with CSS animation', () => {
      const img = document.createElement('img');
      fadeInImage(img);

      // Should have fade animation applied
      expect(img.style.animation).toContain('fadeIn');
      expect(img.style.opacity).toBe('1');
    });
  });

  describe('getNextImage', () => {
    it('fetches next image with window dimensions', async () => {
      window.innerWidth = 1920;
      window.innerHeight = 1080;

      global.fetch = vi.fn(() =>
        Promise.resolve({
          json: () => Promise.resolve({ id: 'test-123', url: '/test.jpg' })
        })
      );

      const result = await getNextImage();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8321/api/v1/images/next?width=1920&height=1080'
      );
      expect(result).toEqual({ id: 'test-123', url: '/test.jpg' });
    });
  });

  describe('transitions', () => {
    it('applies fade transition by default', () => {
      vi.useFakeTimers();
      const img = document.createElement('img');
      const result = applyTransition(img, 'fade');
      
      expect(result).toBe('fade');
    });

    it('applies slide-left transition', () => {
      const img = document.createElement('img');
      const result = applyTransition(img, 'slide-left');
      
      expect(result).toBe('slide-left');
      expect(img.style.animation).toContain('slideInLeft');
      expect(img.style.opacity).toBe('1');
    });

    it('applies slide-right transition', () => {
      const img = document.createElement('img');
      const result = applyTransition(img, 'slide-right');
      
      expect(result).toBe('slide-right');
      expect(img.style.animation).toContain('slideInRight');
      expect(img.style.opacity).toBe('1');
    });

    it('applies zoom transition', () => {
      const img = document.createElement('img');
      const result = applyTransition(img, 'zoom');
      
      expect(result).toBe('zoom');
      expect(img.style.animation).toContain('zoomInTransition');
      expect(img.style.opacity).toBe('1');
    });

    it('applies no transition when set to none', () => {
      const img = document.createElement('img');
      const result = applyTransition(img, 'none');
      
      expect(result).toBe('none');
      expect(img.style.opacity).toBe('1');
    });

    it('applies random transition', () => {
      const img = document.createElement('img');
      const result = applyTransition(img, 'random');
      
      // Random should return one of the valid transitions
      expect(['fade', 'slide-left', 'slide-right', 'zoom']).toContain(result);
    });

    it('getRandomTransition returns valid transition', () => {
      const result = getRandomTransition();
      expect(['fade', 'slide-left', 'slide-right', 'zoom']).toContain(result);
    });
  });

  describe('startTask', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('shows task label in toast after starting task', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 201,
          json: () => Promise.resolve({ id: 'task-1', task_type_label: 'Clear Cache', progress: 0, status: 'pending' })
        })
      );

      await startTask('clear_cache');

      const text = document.getElementById('task-toast-text');
      expect(text.textContent).toBe('Clear Cache 0%');
      expect(document.getElementById('task-toast').classList.contains('show')).toBe(true);
    });

    it('updates toast with label and percentage during polling', async () => {
      let callCount = 0;
      global.fetch = vi.fn(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.resolve({
            ok: true, status: 201,
            json: () => Promise.resolve({ id: 'task-1', task_type_label: 'Rescan Library', progress: 0, status: 'pending' })
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ id: 'task-1', task_type_label: 'Rescan Library', progress: 50, status: 'running' })
        });
      });

      await startTask('rescan_library');
      await vi.advanceTimersByTimeAsync(1000);

      const text = document.getElementById('task-toast-text');
      expect(text.textContent).toBe('Rescan Library 50%');
      expect(document.getElementById('task-toast-bar').style.width).toBe('50%');
    });

    it('shows label with Done on completion', async () => {
      let callCount = 0;
      global.fetch = vi.fn(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.resolve({
            ok: true, status: 201,
            json: () => Promise.resolve({ id: 'task-1', task_type_label: 'Reset Image Count', progress: 0, status: 'pending' })
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ id: 'task-1', task_type_label: 'Reset Image Count', progress: 100, status: 'completed' })
        });
      });

      await startTask('reset_image_count');
      await vi.advanceTimersByTimeAsync(1000);

      expect(document.getElementById('task-toast-text').textContent).toBe('Reset Image Count Done!');
    });

    it('shows label with error on failure', async () => {
      let callCount = 0;
      global.fetch = vi.fn(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.resolve({
            ok: true, status: 201,
            json: () => Promise.resolve({ id: 'task-1', task_type_label: 'Clear Cache', progress: 0, status: 'pending' })
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ id: 'task-1', task_type_label: 'Clear Cache', progress: 30, status: 'failed', error: 'disk full' })
        });
      });

      await startTask('clear_cache');
      await vi.advanceTimersByTimeAsync(1000);

      expect(document.getElementById('task-toast-text').textContent).toBe('Clear Cache Failed: disk full');
    });

    it('shows conflict message on 409', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 409,
          json: () => Promise.resolve({ detail: 'A Clear Cache task is already pending or running.' })
        })
      );

      const result = await startTask('clear_cache');

      expect(result).toBeNull();
      expect(document.getElementById('task-toast-text').textContent).toBe('A Clear Cache task is already pending or running.');
      expect(document.getElementById('task-toast').classList.contains('show')).toBe(true);
    });

    it('shows generic error on network failure', async () => {
      global.fetch = vi.fn(() => Promise.reject(new Error('Network error')));

      const result = await startTask('clear_cache');

      expect(result).toBeNull();
      expect(document.getElementById('task-toast-text').textContent).toBe('Failed to start task');
    });
  });
});
