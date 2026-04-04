import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('updateSeparators', () => {
  let document, updateSeparators;

  function setupDOM(groupDisplayValues = {}) {
    const dom = new JSDOM(`
      <!DOCTYPE html>
      <html><body>
        <div id="bottom-bar" class="text-box" style="display: none;">
          <div class="info-group" id="photo-date-group"><span id="photo-date"></span></div>
          <div class="group-separator"></div>
          <div class="info-group" id="current-date-group"><span id="current-date"></span></div>
          <div class="group-separator"></div>
          <div class="info-group" id="current-time-group"><span id="current-time"></span></div>
          <div class="group-separator"></div>
          <div class="info-group" id="weather-group"><span id="weather-temp"></span></div>
        </div>
        <div id="image-container"></div>
        <div id="progress-bar"></div>
        <div class="task-toast" id="task-toast">
          <span id="task-toast-text"></span>
          <div class="task-toast-track"><div class="task-toast-bar" id="task-toast-bar"></div></div>
        </div>
      </body></html>
    `, { url: 'http://localhost' });

    global.window = dom.window;
    global.document = dom.window.document;
    global.Image = dom.window.Image;
    document = dom.window.document;

    dom.window.SMPL_CONFIG = {
      transitionInterval: 1000, refreshInterval: 3000,
      host: 'http://localhost', port: '8321',
      displayDate: true, displayClock: true,
      imageZoomEffect: false, imageTransitionType: 'fade',
      plugins: []
    };

    // Apply group visibility before importing
    Object.entries(groupDisplayValues).forEach(([id, display]) => {
      document.getElementById(id).style.display = display;
    });
  }

  async function loadModule() {
    const module = await import('../../src/smplfrm/smplfrm/static/main.js');
    updateSeparators = module.updateSeparators;
  }

  beforeEach(() => {
    vi.resetModules();
  });

  it('bottom bar starts hidden before updateSeparators runs', async () => {
    setupDOM();
    await loadModule();

    const bottomBar = document.getElementById('bottom-bar');
    expect(bottomBar.style.display).toBe('none');
  });

  it('hides bottom bar when all groups are hidden', async () => {
    setupDOM({
      'photo-date-group': 'none',
      'current-date-group': 'none',
      'current-time-group': 'none',
      'weather-group': 'none',
    });
    await loadModule();

    updateSeparators();

    const bottomBar = document.getElementById('bottom-bar');
    expect(bottomBar.style.display).toBe('none');
  });

  it('shows bottom bar when at least one group is visible', async () => {
    setupDOM({
      'photo-date-group': 'none',
      'current-date-group': 'none',
      'current-time-group': 'none',
      'weather-group': '',
    });
    await loadModule();

    updateSeparators();

    const bottomBar = document.getElementById('bottom-bar');
    expect(bottomBar.style.display).toBe('flex');
  });

  it('shows no separators when only one group is visible', async () => {
    setupDOM({
      'photo-date-group': 'none',
      'current-date-group': 'none',
      'current-time-group': 'none',
      'weather-group': '',
    });
    await loadModule();

    updateSeparators();

    const separators = document.querySelectorAll('.group-separator');
    separators.forEach(sep => {
      expect(sep.style.display).toBe('none');
    });
  });

  it('shows separator only between two visible groups', async () => {
    setupDOM({
      'photo-date-group': '',
      'current-date-group': 'none',
      'current-time-group': 'none',
      'weather-group': '',
    });
    await loadModule();

    updateSeparators();

    // Separator after photo-date-group should be visible (next visible is weather)
    const photoGroup = document.getElementById('photo-date-group');
    const sepAfterPhoto = photoGroup.nextElementSibling;
    expect(sepAfterPhoto.style.display).toBe('');

    // Other separators should be hidden
    const allSeps = document.querySelectorAll('.group-separator');
    const visibleSeps = Array.from(allSeps).filter(s => s.style.display !== 'none');
    expect(visibleSeps.length).toBe(1);
  });
});
