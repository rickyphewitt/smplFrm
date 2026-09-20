import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const MAIN = '../../src/smplfrm/smplfrm/static/main.js';
const UI_ERRORS = '../../src/smplfrm/smplfrm/static/uiErrors.js';

describe('Unhandled rejection safety net', () => {
  let uiErrors;

  function rejectWith(reason) {
    const event = new Event('unhandledrejection');
    event.reason = reason;
    window.dispatchEvent(event);
  }

  beforeEach(async () => {
    vi.resetModules();
    document.body.innerHTML = '';
    global.fetch = vi.fn();
    global.window = Object.assign(global.window || {}, {
      SMPL_CONFIG: {
        host: 'http://localhost',
        port: '8321',
        refreshInterval: 30000,
        transitionInterval: 10000,
        displayClock: false,
        displayDate: false,
        plugins: [],
      },
    });
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'debug').mockImplementation(() => {});

    uiErrors = await import(UI_ERRORS);
  });

  afterEach(() => {
    uiErrors._resetGlobalRejectionHandler();
    vi.restoreAllMocks();
  });

  it('shows one toast and logs once per rejection', async () => {
    uiErrors.installGlobalRejectionHandler();

    rejectWith(new TypeError('Failed to fetch'));

    const toast = document.getElementById('app-toast');
    expect(toast).not.toBeNull();
    expect(toast.style.opacity).toBe('1');
    expect(toast.textContent).toBe('Something went wrong. Please try again.');
    expect(console.error).toHaveBeenCalledTimes(1);
  });

  it('is installed by init before anything else in startup can fail', async () => {
    const mod = await import(MAIN);

    // The DOM here is deliberately empty, so init() throws as soon as it
    // reaches the settings modal wiring. The safety net must already be in
    // place at that point, which is why init() registers it first.
    expect(() => mod.init()).toThrow();

    rejectWith(new TypeError('Failed to fetch'));

    expect(document.getElementById('app-toast')).not.toBeNull();
    expect(console.error).toHaveBeenCalledTimes(1);
  });

  it('reports each rejection once rather than accumulating listeners', async () => {
    const mod = await import(MAIN);
    expect(() => mod.init()).toThrow();
    expect(() => mod.init()).toThrow();

    rejectWith(new TypeError('Failed to fetch'));

    expect(console.error).toHaveBeenCalledTimes(1);
  });
});
