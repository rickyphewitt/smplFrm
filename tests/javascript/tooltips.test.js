import { describe, it, expect, beforeAll } from 'vitest';
import { JSDOM } from 'jsdom';
import { readFileSync } from 'fs';
import { resolve } from 'path';

describe('settings modal tooltips', () => {
  let document;

  beforeAll(() => {
    const templatePath = resolve(__dirname, '../../src/smplfrm/smplfrm/templates/index.html');
    // Strip Django template tags so JSDOM can parse the HTML
    const raw = readFileSync(templatePath, 'utf-8').replace(/\{%.*?%\}/g, '').replace(/\{\{.*?\}\}/g, '');
    const dom = new JSDOM(raw);
    document = dom.window.document;
  });

  const tabs = {
    'tab-display': [
      'Show Photo Date',
      'Photo Date From File Path',
      'Show Date And Time',
      'Timezone',
    ],
    'tab-images': [
      'Refresh Interval',
      'Transition Time',
      'Zoom Effect',
      'Transition Type',
      'Fill Mode',
    ],
    'tab-library': [
      'Cache Timeout',
      'Reset Image Count',
      'Clear Cache',
      'Rescan Library',
    ],
  };

  Object.entries(tabs).forEach(([tabId, labels]) => {
    labels.forEach((labelText) => {
      it(`${tabId} label "${labelText}" has a title attribute`, () => {
        const tab = document.getElementById(tabId);
        const label = Array.from(tab.querySelectorAll('label')).find(
          (el) => el.textContent.trim() === labelText
        );
        expect(label, `label "${labelText}" not found in #${tabId}`).toBeTruthy();
        expect(label.getAttribute('title'), `label "${labelText}" missing title`).toBeTruthy();
      });
    });
  });

  const tableHeaders = {
    'tab-presets': ['Name', 'Description', 'Status', 'Delete'],
    'tab-plugins': ['Name', 'Description', 'Enabled'],
    'tab-tasks': ['Type', 'Status', 'Progress', 'Created', 'Delete'],
  };

  Object.entries(tableHeaders).forEach(([tabId, headers]) => {
    headers.forEach((headerText) => {
      it(`${tabId} column header "${headerText}" has a title attribute`, () => {
        const tab = document.getElementById(tabId);
        const th = Array.from(tab.querySelectorAll('th')).find(
          (el) => el.textContent.trim() === headerText
        );
        expect(th, `th "${headerText}" not found in #${tabId}`).toBeTruthy();
        expect(th.getAttribute('title'), `th "${headerText}" missing title`).toBeTruthy();
      });
    });
  });
});
