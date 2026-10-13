/**
 * Accessibility behaviour of the settings modal: dialog semantics, focus
 * moving into the panel on open, Tab-cycling trap, and focus returning to
 * #logo-icon on close.
 *
 * Builds the real template markup (Django tags stripped) rather than a hand
 * written fixture, so the test exercises the actual dialog hooks main.js
 * reads.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const TEMPLATE_PATH = resolve(
  __dirname,
  '../../src/smplfrm/smplfrm/templates/index.html',
);
const MAIN_PATH = '../../src/smplfrm/smplfrm/static/main.js';

function loadTemplateHtml() {
  const raw = readFileSync(TEMPLATE_PATH, 'utf-8')
    .replace(/\{%.*?%\}/g, '')
    .replace(/\{\{.*?\}\}/g, '');
  // Drop the two <script> blocks at the end: the inline SMPL_CONFIG script
  // and the module script that calls init() itself. The test calls init()
  // explicitly after wiring its own fetch mocks.
  return raw.replace(/<script[\s\S]*?<\/script>/g, '');
}

describe('settings modal accessibility', () => {
  let window, document, mod;

  beforeEach(async () => {
    vi.resetModules();
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/vnd.api+json' }),
        json: () => Promise.resolve({ data: null }),
      }),
    );

    const dom = new JSDOM(loadTemplateHtml(), { url: 'http://localhost' });
    window = dom.window;
    document = window.document;
    global.window = window;
    global.document = document;
    global.Image = window.Image;
    global.Headers = window.Headers;

    window.SMPL_CONFIG = {
      transitionInterval: 1000,
      refreshInterval: 3000,
      host: 'http://localhost',
      port: '8321',
      displayDate: false,
      displayClock: false,
      imageZoomEffect: false,
      imageTransitionType: 'fade',
      plugins: [],
    };

    mod = await import(MAIN_PATH);
    mod.init();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
  });

  function openModal() {
    document
      .getElementById('logo-icon')
      .dispatchEvent(new window.Event('click', { bubbles: true }));
  }

  it('has dialog semantics and an accessible name', () => {
    const modal = document.getElementById('settings-modal');
    expect(modal.getAttribute('role')).toBe('dialog');
    expect(modal.getAttribute('aria-modal')).toBe('true');
    const labelledBy = modal.getAttribute('aria-labelledby');
    expect(labelledBy).toBeTruthy();
    expect(document.getElementById(labelledBy)).not.toBeNull();
  });

  it('moves focus into the panel on open', async () => {
    openModal();
    await Promise.resolve();
    await Promise.resolve();

    expect(document.getElementById('settings-modal').classList).toContain(
      'open',
    );
    expect(document.activeElement.id).toBe('close-modal');
  });

  it('returns focus to #logo-icon on close via Escape', async () => {
    openModal();
    await Promise.resolve();
    await Promise.resolve();

    document.dispatchEvent(
      new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }),
    );

    expect(
      document.getElementById('settings-modal').classList.contains('open'),
    ).toBe(false);
    expect(document.activeElement.id).toBe('logo-icon');
  });

  it('traps Tab within the modal: Tab from the last element wraps to the first', async () => {
    openModal();
    await Promise.resolve();
    await Promise.resolve();

    const modal = document.getElementById('settings-modal');
    const focusable = mod.getFocusableElements(modal);
    const last = focusable[focusable.length - 1];
    const first = focusable[0];

    last.focus();
    const event = new window.KeyboardEvent('keydown', {
      key: 'Tab',
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(event);

    expect(document.activeElement).toBe(first);
  });

  it('traps Shift+Tab within the modal: Shift+Tab from the first element wraps to the last', async () => {
    openModal();
    await Promise.resolve();
    await Promise.resolve();

    const modal = document.getElementById('settings-modal');
    const focusable = mod.getFocusableElements(modal);
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    first.focus();
    const event = new window.KeyboardEvent('keydown', {
      key: 'Tab',
      shiftKey: true,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(event);

    expect(document.activeElement).toBe(last);
  });

  it('excludes controls in inactive tab panels from the trap', () => {
    const modal = document.getElementById('settings-modal');
    const ids = mod.getFocusableElements(modal).map((el) => el.id);

    // Active panel and always-visible chrome are reachable.
    expect(ids).toContain('setting-theme');
    expect(ids).toContain('close-modal');
    expect(ids).toContain('cancel-settings');

    // Panels hidden by `.tab-content { display: none }` are not. These are
    // skipped by the browser's own sequential navigation, so including them
    // would put the trap's wrap boundaries on unreachable elements.
    expect(ids).not.toContain('setting-refresh');
    expect(ids).not.toContain('task-page-next');
    expect(ids).not.toContain('plugin-page-next');

    // Inline-hidden action bars stay excluded too.
    expect(ids).not.toContain('plugin-detail-save');

    expect(ids[0]).toBe('close-modal');
    expect(ids[ids.length - 1]).toBe('cancel-settings');
  });

  it('does not trap Tab when the modal is closed', async () => {
    const outsideFocusable = document.getElementById('logo-icon');
    outsideFocusable.focus();

    const event = new window.KeyboardEvent('keydown', {
      key: 'Tab',
      bubbles: true,
      cancelable: true,
    });
    const prevented = !document.dispatchEvent(event);

    // No trap logic should run (and therefore nothing should be prevented)
    // while the modal is closed.
    expect(prevented).toBe(false);
  });
});
