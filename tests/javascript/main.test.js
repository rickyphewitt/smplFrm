import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('main.js', () => {
  let window, document;
  let buildApiUrl, getWindowDimensions, fadeInImage, getNextImage;

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
      imageZoomEffect: true
    };

    // Import functions after setting up globals
    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    buildApiUrl = module.buildApiUrl;
    getWindowDimensions = module.getWindowDimensions;
    fadeInImage = module.fadeInImage;
    getNextImage = module.getNextImage;
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

    it('increments opacity gradually', () => {
      const img = document.createElement('img');
      fadeInImage(img);

      vi.advanceTimersByTime(100);
      const opacity1 = parseFloat(img.style.opacity);
      expect(opacity1).toBeGreaterThan(0);
      expect(opacity1).toBeLessThan(1);

      vi.advanceTimersByTime(900);
      expect(parseFloat(img.style.opacity)).toBe(1);
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
});
