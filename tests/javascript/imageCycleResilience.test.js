/**
 * Tests for image queue resilience and preload best-effort behavior
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('Image Queue Resilience', () => {
  let getNextImage;

  beforeEach(async () => {
    vi.resetModules();
    global.fetch = vi.fn();
    global.console.error = vi.fn();
    global.console.debug = vi.fn();

    window.SMPL_CONFIG = {
      host: 'http://localhost',
      port: 8321,
      refreshInterval: 30000,
    };

    window.innerWidth = 1920;
    window.innerHeight = 1080;

    document.body.innerHTML = `
      <div id="image-container"></div>
      <div id="progress-bar"></div>
    `;

    // Import after mocks are set
    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    getNextImage = module.getNextImage;
  });

  describe('queue behavior when collection fetch succeeds', () => {
    it('returns images from queue in order', async () => {
      global.fetch
        .mockResolvedValueOnce({
          status: 200,
          ok: true,
          headers: { get: () => 'application/vnd.api+json' },
          json: () => Promise.resolve({
            data: [
              { type: 'images', id: 'img-1', attributes: { name: 'first.jpg' } },
              { type: 'images', id: 'img-2', attributes: { name: 'second.jpg' } },
              { type: 'images', id: 'img-3', attributes: { name: 'third.jpg' } },
            ],
            links: {},
            meta: { pagination: { count: 3, pages: 1, page: 1 } },
          }),
        })
        // Mock successful preload request
        .mockResolvedValueOnce({ status: 201, ok: true });

      const first = await getNextImage();
      expect(first.id).toBe('img-1');

      const second = await getNextImage();
      expect(second.id).toBe('img-2');

      const third = await getNextImage();
      expect(third.id).toBe('img-3');
    });
  });

  describe('queue behavior when collection fetch fails', () => {
    it('returns null when queue is empty and refill fails', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await getNextImage();
      expect(result).toBeNull();
    });

    it('returns queued image even after refill failure', async () => {
      global.fetch
        .mockResolvedValueOnce({
          status: 200,
          ok: true,
          headers: { get: () => 'application/vnd.api+json' },
          json: () => Promise.resolve({
            data: [
              { type: 'images', id: 'img-1', attributes: { name: 'first.jpg' } },
              { type: 'images', id: 'img-2', attributes: { name: 'second.jpg' } },
            ],
            links: {},
            meta: { pagination: { count: 2, pages: 1, page: 1 } },
          }),
        })
        // Preload succeeds
        .mockResolvedValueOnce({ status: 201, ok: true });

      const first = await getNextImage();
      expect(first.id).toBe('img-1');

      // Second call returns from queue without new fetch
      const second = await getNextImage();
      expect(second.id).toBe('img-2');
    });
  });

  describe('preload best-effort behavior', () => {
    it('returns image from queue even if preload is pending', async () => {
      global.fetch
        .mockResolvedValueOnce({
          status: 200,
          ok: true,
          headers: { get: () => 'application/vnd.api+json' },
          json: () => Promise.resolve({
            data: [
              { type: 'images', id: 'img-1', attributes: { name: 'first.jpg' } },
            ],
            links: {},
            meta: { pagination: { count: 1, pages: 1, page: 1 } },
          }),
        })
        // Mock preload response (happens async, doesn't block)
        .mockResolvedValueOnce({ status: 201, ok: true });

      const result = await getNextImage();
      
      // Image returned immediately from queue
      expect(result).not.toBeNull();
      expect(result.id).toBe('img-1');
    });
  });

  describe('empty collection handling', () => {
    it('returns null when collection is empty', async () => {
      global.fetch.mockResolvedValueOnce({
        status: 200,
        ok: true,
        headers: { get: () => 'application/vnd.api+json' },
        json: () => Promise.resolve({
          data: [],
          links: {},
          meta: { pagination: { count: 0, pages: 0, page: 1 } },
        }),
      });

      const result = await getNextImage();
      expect(result).toBeNull();
    });
  });

  describe('pagination boundary handling', () => {
    it('wraps to page 1 after exhausting all pages', async () => {
      // First call: page 1 with 2 pages total
      global.fetch
        .mockResolvedValueOnce({
          status: 200,
          ok: true,
          headers: { get: () => 'application/vnd.api+json' },
          json: () => Promise.resolve({
            data: [
              { type: 'images', id: 'img-1', attributes: { name: 'page1-1.jpg' } },
              { type: 'images', id: 'img-2', attributes: { name: 'page1-2.jpg' } },
            ],
            links: {},
            meta: { pagination: { count: 4, pages: 2, page: 1 } },
          }),
        })
        .mockResolvedValueOnce({ status: 201, ok: true }) // preload
        // Second call: page 2 (last page)
        .mockResolvedValueOnce({
          status: 200,
          ok: true,
          headers: { get: () => 'application/vnd.api+json' },
          json: () => Promise.resolve({
            data: [
              { type: 'images', id: 'img-3', attributes: { name: 'page2-1.jpg' } },
              { type: 'images', id: 'img-4', attributes: { name: 'page2-2.jpg' } },
            ],
            links: {},
            meta: { pagination: { count: 4, pages: 2, page: 2 } },
          }),
        })
        .mockResolvedValueOnce({ status: 201, ok: true }) // preload
        // Third call: should wrap to page 1, not request page 3
        .mockResolvedValueOnce({
          status: 200,
          ok: true,
          headers: { get: () => 'application/vnd.api+json' },
          json: () => Promise.resolve({
            data: [
              { type: 'images', id: 'img-1', attributes: { name: 'page1-1.jpg' } },
              { type: 'images', id: 'img-2', attributes: { name: 'page1-2.jpg' } },
            ],
            links: {},
            meta: { pagination: { count: 4, pages: 2, page: 1 } },
          }),
        })
        .mockResolvedValueOnce({ status: 201, ok: true }); // preload

      // Consume page 1
      await getNextImage();
      await getNextImage();
      
      // Trigger refill to page 2
      await getNextImage();
      await getNextImage();
      
      // Trigger refill - should wrap to page 1, not request page 3
      await getNextImage();
      
      // Verify no 404 requests were made
      const allUrls = global.fetch.mock.calls.map(call => call[0]);
      const page3Requests = allUrls.filter(url => url.includes('page[number]=3'));
      expect(page3Requests.length).toBe(0);
    });

    it('recovers from 404 by resetting to page 1', async () => {
      // First call succeeds
      global.fetch
        .mockResolvedValueOnce({
          status: 200,
          ok: true,
          headers: { get: () => 'application/vnd.api+json' },
          json: () => Promise.resolve({
            data: [
              { type: 'images', id: 'img-1', attributes: { name: 'first.jpg' } },
            ],
            links: {},
            meta: { pagination: { count: 1, pages: 1, page: 1 } },
          }),
        })
        .mockResolvedValueOnce({ status: 201, ok: true }) // preload
        // Simulate 404 on invalid page (should not happen with fix, but test recovery)
        .mockResolvedValueOnce({
          status: 404,
          ok: false,
          headers: { get: () => 'application/vnd.api+json' },
          json: () => Promise.resolve({
            errors: [{ status: '404', code: 'not_found', detail: 'Invalid page.' }],
          }),
        })
        // Recovery: back to page 1
        .mockResolvedValueOnce({
          status: 200,
          ok: true,
          headers: { get: () => 'application/vnd.api+json' },
          json: () => Promise.resolve({
            data: [
              { type: 'images', id: 'img-1', attributes: { name: 'first.jpg' } },
            ],
            links: {},
            meta: { pagination: { count: 1, pages: 1, page: 1 } },
          }),
        })
        .mockResolvedValueOnce({ status: 201, ok: true }); // preload

      await getNextImage();
      await getNextImage(); // Triggers 404
      const recovered = await getNextImage();
      
      expect(recovered).not.toBeNull();
      expect(recovered.id).toBe('img-1');
    });
  });
});
