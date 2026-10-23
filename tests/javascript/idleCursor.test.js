// @vitest-environment jsdom
/**
 * Idle cursor.
 *
 * A mouse left over the frame should not sit on the photo, so the cursor is
 * hidden once the pointer has been still for 30 seconds and shown again on
 * the next movement or press. main.js only toggles `body.cursor-idle`;
 * base.css turns that class into `cursor: none` for every theme.
 *
 * The cursor is never hidden while the settings panel is open, because the
 * panel is where the mouse is being used.
 */
import {
  describe,
  it,
  expect,
  beforeAll,
  beforeEach,
  afterEach,
  vi,
} from 'vitest';
import { JSDOM } from 'jsdom';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const MAIN_PATH = '../../src/smplfrm/smplfrm/static/main.js';
const TEMPLATE_PATH = resolve(
  __dirname,
  '../../src/smplfrm/smplfrm/templates/index.html',
);

const SMPL_CONFIG = {
  host: 'http://localhost',
  port: '8321',
  transitionInterval: 1000,
  refreshInterval: 3000,
  displayDate: false,
  displayClock: false,
  imageTransitionType: 'fade',
  imageZoomEffect: false,
  plugins: [],
};

function isHidden() {
  return document.body.classList.contains('cursor-idle');
}

function pointer(type) {
  document.dispatchEvent(new window.Event(type, { bubbles: true }));
}

describe('initIdleCursor', () => {
  let mod;
  let stop;

  beforeAll(async () => {
    // main.js references these DOM elements at the top level
    document.body.innerHTML = `
      <div id="image-container"></div>
      <div id="progress-bar"></div>
      <div id="settings-modal" class="settings-modal"></div>
    `;
    window.SMPL_CONFIG = SMPL_CONFIG;
    mod = await import(MAIN_PATH);
  });

  beforeEach(() => {
    vi.useFakeTimers();
    document.getElementById('settings-modal').classList.remove('open');
    stop = mod.initIdleCursor();
  });

  afterEach(() => {
    stop();
    vi.useRealTimers();
  });

  it('waits a fixed 30 seconds', () => {
    expect(mod.CURSOR_IDLE_MS).toBe(30000);
    expect(mod.CURSOR_IDLE_CLASS).toBe('cursor-idle');
  });

  it('keeps the cursor visible until the pointer has been still for 30 seconds', () => {
    expect(isHidden()).toBe(false);
    vi.advanceTimersByTime(29999);
    expect(isHidden()).toBe(false);
  });

  it('hides the cursor after 30 seconds without pointer activity', () => {
    vi.advanceTimersByTime(30000);
    expect(isHidden()).toBe(true);
  });

  it('shows the cursor on movement and restarts the countdown', () => {
    vi.advanceTimersByTime(30000);
    expect(isHidden()).toBe(true);

    pointer('pointermove');
    expect(isHidden()).toBe(false);

    vi.advanceTimersByTime(29999);
    expect(isHidden()).toBe(false);
    vi.advanceTimersByTime(1);
    expect(isHidden()).toBe(true);
  });

  it('restarts the countdown on a press', () => {
    vi.advanceTimersByTime(20000);
    pointer('pointerdown');
    vi.advanceTimersByTime(20000);
    expect(isHidden()).toBe(false);
    vi.advanceTimersByTime(10000);
    expect(isHidden()).toBe(true);
  });

  it('keeps a single countdown however often the pointer moves', () => {
    for (let i = 0; i < 100; i++) pointer('pointermove');
    expect(vi.getTimerCount()).toBe(1);
  });

  it('never hides the cursor while the settings panel is open', () => {
    const modal = document.getElementById('settings-modal');
    modal.classList.add('open');
    vi.advanceTimersByTime(90000);
    expect(isHidden()).toBe(false);

    modal.classList.remove('open');
    vi.advanceTimersByTime(30000);
    expect(isHidden()).toBe(true);
  });

  it('stops listening and shows the cursor when torn down', () => {
    vi.advanceTimersByTime(30000);
    stop();
    expect(isHidden()).toBe(false);
    expect(vi.getTimerCount()).toBe(0);

    pointer('pointermove');
    vi.advanceTimersByTime(30000);
    expect(isHidden()).toBe(false);
    stop = () => {};
  });
});

describe('idle cursor wiring in init()', () => {
  let window_;
  let document_;

  beforeEach(async () => {
    vi.resetModules();
    vi.useFakeTimers();
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/vnd.api+json' }),
        json: () => Promise.resolve({ data: null }),
      }),
    );
    // Real template markup with Django tags and scripts stripped, so the
    // settings panel and its open control are the ones main.js wires up.
    const html = readFileSync(TEMPLATE_PATH, 'utf-8')
      .replace(/\{%.*?%\}/g, '')
      .replace(/\{\{.*?\}\}/g, '')
      .replace(/<script[\s\S]*?<\/script>/g, '');
    const dom = new JSDOM(html, { url: 'http://localhost' });
    window_ = dom.window;
    document_ = window_.document;
    global.window = window_;
    global.document = document_;
    global.Image = window_.Image;
    global.Headers = window_.Headers;
    window_.SMPL_CONFIG = SMPL_CONFIG;

    const mod = await import(MAIN_PATH);
    mod.init();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.resetModules();
  });

  it('hides the cursor 30 seconds after the frame starts', () => {
    vi.advanceTimersByTime(30000);
    expect(document_.body.classList.contains('cursor-idle')).toBe(true);
  });

  it('shows the cursor when the panel is opened from the keyboard', () => {
    vi.advanceTimersByTime(30000);
    expect(document_.body.classList.contains('cursor-idle')).toBe(true);

    // Enter or Space on a focused button dispatches a click with no
    // pointer event before it.
    document_
      .getElementById('logo-icon')
      .dispatchEvent(new window_.Event('click', { bubbles: true }));
    expect(document_.body.classList.contains('cursor-idle')).toBe(false);

    vi.advanceTimersByTime(90000);
    expect(document_.body.classList.contains('cursor-idle')).toBe(false);
  });
});
