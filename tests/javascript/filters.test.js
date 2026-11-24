/**
 * Filters tab: the filtering switch, the filter list, the filter detail view,
 * and the rule editor.
 *
 * Uses the real template markup (Django tags stripped) and a small in-memory
 * fake of the library filter API, so each test drives the UI the way an
 * operator would and checks both the DOM and the requests sent.
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
const PAGE_SIZE = 5;

function loadTemplateHtml() {
  const raw = readFileSync(TEMPLATE_PATH, 'utf-8')
    .replace(/\{%.*?%\}/g, '')
    .replace(/\{\{.*?\}\}/g, '');
  return raw.replace(/<script[\s\S]*?<\/script>/g, '');
}

/** In-memory stand-in for the parts of the API the Filters tab uses. */
function createFakeApi() {
  const state = {
    settings: { id: 'settings00000001', enabled: false },
    filters: [],
    rules: [],
    tags: [],
    calls: [],
    // (method, path) -> {status, code, detail} to fail one matching request
    failures: [],
    nextId: 1,
  };

  const newId = (prefix) =>
    `${prefix}${String(state.nextId++).padStart(16 - prefix.length, '0')}`;

  const ruleType = 'tag_library_filter_rules';

  const filterResource = (f) => ({
    type: 'library_filters',
    id: f.id,
    attributes: {
      name: f.name,
      description: f.description,
      is_active: f.is_active,
      created: '2026-11-23T00:00:00Z',
      updated: '2026-11-23T00:00:00Z',
    },
    relationships: {
      rules: {
        data: state.rules
          .filter((r) => r.filterId === f.id)
          .map((r) => ({ type: ruleType, id: r.id })),
      },
    },
  });

  const ruleResource = (r) => ({
    type: ruleType,
    id: r.id,
    attributes: { created: '2026-11-23T00:00:00Z' },
    relationships: {
      library_filter: { data: { type: 'library_filters', id: r.filterId } },
      tag: { data: { type: 'tags', id: r.tagId } },
    },
  });

  const tagResource = (t) => ({
    type: 'tags',
    id: t.id,
    attributes: {
      value: t.value,
      display_value: t.display_value,
      usage_count: t.usage_count,
    },
  });

  const page = (items, pageNumber, toResource) => {
    const pages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
    const start = (pageNumber - 1) * PAGE_SIZE;
    return {
      data: items.slice(start, start + PAGE_SIZE).map(toResource),
      links: {
        prev: pageNumber > 1 ? 'prev' : null,
        next: pageNumber < pages ? 'next' : null,
      },
      meta: { pagination: { page: pageNumber, pages, count: items.length } },
    };
  };

  const error = (status, code, detail) => ({
    status,
    body: { errors: [{ status: String(status), code, detail }] },
  });

  const forbidden = () => error(403, 'forbidden', 'Access denied');

  function handle(method, path, params, body) {
    const [resource, id] = path.split('/');
    const pageNumber = Number(params.get('page[number]') || 1);
    const attrs = body?.data?.attributes || {};
    const rels = body?.data?.relationships || {};

    if (resource === 'library_filter_settings') {
      if (method === 'GET') {
        return {
          status: 200,
          body: page([state.settings], 1, (s) => ({
            type: 'library_filter_settings',
            id: s.id,
            attributes: { enabled: s.enabled },
          })),
        };
      }
      if (method === 'PUT') {
        state.settings.enabled = attrs.enabled;
        return {
          status: 200,
          body: {
            data: {
              type: 'library_filter_settings',
              id: state.settings.id,
              attributes: { enabled: state.settings.enabled },
            },
          },
        };
      }
    }

    if (resource === 'library_filters') {
      const hasRules = (fid) => state.rules.some((r) => r.filterId === fid);
      if (method === 'GET' && !id) {
        return {
          status: 200,
          body: page(state.filters, pageNumber, filterResource),
        };
      }
      const filter = state.filters.find((f) => f.id === id);
      if (method === 'GET') {
        return filter
          ? { status: 200, body: { data: filterResource(filter) } }
          : forbidden();
      }
      if (method === 'POST' || method === 'PUT') {
        if (!attrs.name) {
          return error(400, 'validation_error', 'This field is required.');
        }
        if (method === 'PUT' && !filter) return forbidden();
        const target = filter || { id: newId('filter') };
        if (attrs.is_active && !(filter && hasRules(filter.id))) {
          return error(
            400,
            'rule_required',
            'A library filter needs at least one rule before it can be active',
          );
        }
        if (attrs.is_active) {
          state.filters.forEach((f) => (f.is_active = false));
        }
        Object.assign(target, {
          name: attrs.name,
          description: attrs.description ?? '',
          is_active: !!attrs.is_active,
        });
        if (!filter) state.filters.push(target);
        return {
          status: method === 'POST' ? 201 : 200,
          body: { data: filterResource(target) },
        };
      }
      if (method === 'DELETE') {
        if (!filter) return forbidden();
        state.filters = state.filters.filter((f) => f !== filter);
        state.rules = state.rules.filter((r) => r.filterId !== filter.id);
        return { status: 204 };
      }
    }

    if (resource === 'library_filter_rules') {
      if (method === 'GET' && !id) {
        const fid = params.get('filter[library_filter]');
        const rules = state.rules.filter((r) => !fid || r.filterId === fid);
        return { status: 200, body: page(rules, pageNumber, ruleResource) };
      }
      const rule = state.rules.find((r) => r.id === id);
      if (method === 'POST' || method === 'PUT') {
        if (method === 'PUT' && !rule) return forbidden();
        const filterId = rels.library_filter?.data?.id;
        const tagId = rels.tag?.data?.id;
        if (!tagId)
          return error(400, 'tag_required', 'A tag rule must reference a tag');
        const duplicate = state.rules.some(
          (r) => r !== rule && r.filterId === filterId && r.tagId === tagId,
        );
        if (duplicate) {
          return error(
            400,
            'duplicate_rule',
            'This library filter already has a rule for that tag',
          );
        }
        const target = rule || { id: newId('rule'), filterId };
        target.tagId = tagId;
        if (!rule) state.rules.push(target);
        return {
          status: method === 'POST' ? 201 : 200,
          body: { data: ruleResource(target) },
        };
      }
      if (method === 'DELETE') {
        if (!rule) return forbidden();
        state.rules = state.rules.filter((r) => r !== rule);
        if (!state.rules.some((r) => r.filterId === rule.filterId)) {
          const parent = state.filters.find((f) => f.id === rule.filterId);
          if (parent) parent.is_active = false;
        }
        return { status: 204 };
      }
    }

    if (resource === 'tags') {
      if (!id)
        return { status: 200, body: page(state.tags, pageNumber, tagResource) };
      const tag = state.tags.find((t) => t.id === id);
      return tag
        ? { status: 200, body: { data: tagResource(tag) } }
        : forbidden();
    }

    if (resource === 'images') {
      return { status: 200, body: page([], 1, (x) => x) };
    }

    return { status: 200, body: { data: null } };
  }

  async function fetchImpl(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const parsed = new URL(url);
    const path = parsed.pathname.replace(/^\/api\/v1\//, '');
    const body = options.body ? JSON.parse(options.body) : undefined;
    state.calls.push({ method, path, params: parsed.searchParams, body });

    const failureIndex = state.failures.findIndex(
      (f) => f.method === method && path.startsWith(f.path),
    );
    let result;
    if (failureIndex >= 0) {
      const [f] = state.failures.splice(failureIndex, 1);
      result = error(f.status, f.code, f.detail);
    } else {
      result = handle(method, path, parsed.searchParams, body);
    }

    return {
      ok: result.status >= 200 && result.status < 300,
      status: result.status,
      headers: new Headers({ 'Content-Type': 'application/vnd.api+json' }),
      json: () => Promise.resolve(result.body),
    };
  }

  const helpers = {
    addTag(value, usage = 0) {
      const tag = {
        id: newId('tag'),
        value: value.toLowerCase(),
        display_value: value,
        usage_count: usage,
      };
      state.tags.push(tag);
      return tag;
    },
    addFilter(name, { description = '', isActive = false, tags = [] } = {}) {
      const filter = {
        id: newId('filter'),
        name,
        description,
        is_active: isActive,
      };
      state.filters.push(filter);
      tags.forEach((tag) =>
        state.rules.push({
          id: newId('rule'),
          filterId: filter.id,
          tagId: tag.id,
        }),
      );
      return filter;
    },
    fail(method, path, status, code = 'error', detail = 'Request failed') {
      state.failures.push({ method, path, status, code, detail });
    },
    callsTo(method, path) {
      return state.calls.filter((c) => c.method === method && c.path === path);
    },
  };

  return { state, fetchImpl, ...helpers };
}

describe('Filters tab', () => {
  let window, document, api;

  const $ = (id) => document.getElementById(id);
  const visible = (id) => $(id).style.display !== 'none';
  const click = (el) =>
    el.dispatchEvent(new window.Event('click', { bubbles: true }));
  const toggle = (input, checked) => {
    input.checked = checked;
    input.dispatchEvent(new window.Event('change', { bubbles: true }));
  };
  const listNames = () =>
    Array.from($('filter-list-body').querySelectorAll('tr')).map(
      (row) => row.cells[0].textContent,
    );
  const rowFor = (name) =>
    Array.from($('filter-list-body').querySelectorAll('tr')).find(
      (row) => row.cells[0].textContent === name,
    );
  const ruleTags = () =>
    Array.from($('filter-rule-list-body').querySelectorAll('tr')).map(
      (row) => row.cells[0].textContent,
    );
  const changesSaved = () =>
    $('settings-modal').dataset.changesSaved === 'true';

  async function openFiltersTab() {
    click(document.querySelector('.tab-btn[data-tab="filters"]'));
    await vi.waitFor(() => {
      expect(document.querySelector('#tab-filters .spinner')).toBeNull();
      expect(visible('filter-list-view')).toBe(true);
    });
  }

  async function openDetail(name) {
    click(rowFor(name).querySelector('.filter-edit-btn'));
    await vi.waitFor(() => {
      expect(visible('filter-detail-view')).toBe(true);
      expect($('filter-name').value).toBe(name);
    });
  }

  beforeEach(async () => {
    vi.resetModules();
    api = createFakeApi();
    global.fetch = vi.fn(api.fetchImpl);

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

    vi.spyOn(console, 'error').mockImplementation(() => {});
    const mod = await import(MAIN_PATH);
    mod.init();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
  });

  describe('tab', () => {
    it('sits between Library and Presets', () => {
      const tabs = Array.from(document.querySelectorAll('.tab-btn')).map(
        (b) => b.dataset.tab,
      );

      expect(tabs.indexOf('filters')).toBe(tabs.indexOf('library') + 1);
      expect(tabs.indexOf('presets')).toBe(tabs.indexOf('filters') + 1);
      expect(
        document.querySelector('.tab-btn[data-tab="filters"]').textContent,
      ).toBe('Filters');
    });

    it('loads the filter list and the switch when opened', async () => {
      api.addFilter('Frame');

      await openFiltersTab();

      expect($('tab-filters').classList.contains('active')).toBe(true);
      expect(listNames()).toEqual(['Frame']);
      expect(
        api.callsTo('GET', 'library_filters')[0].params.get('page[number]'),
      ).toBe('1');
      expect(api.callsTo('GET', 'library_filter_settings')).toHaveLength(1);
    });

    it('returns to the list view when the tab is left and reopened', async () => {
      api.addFilter('Frame');
      await openFiltersTab();
      await openDetail('Frame');

      click(document.querySelector('.tab-btn[data-tab="presets"]'));
      expect(visible('filter-detail-actions')).toBe(false);
      expect(visible('main-actions')).toBe(true);

      await openFiltersTab();
      expect(visible('filter-detail-view')).toBe(false);
      expect(visible('filter-rule-view')).toBe(false);
    });
  });

  describe('filtering switch', () => {
    it('shows the stored value', async () => {
      api.state.settings.enabled = true;

      await openFiltersTab();

      expect($('filter-enabled-toggle').checked).toBe(true);
      expect($('filter-enabled-toggle').disabled).toBe(false);
    });

    it('saves a change immediately', async () => {
      await openFiltersTab();

      toggle($('filter-enabled-toggle'), true);

      await vi.waitFor(() => expect(changesSaved()).toBe(true));
      expect(api.state.settings.enabled).toBe(true);
      const [put] = api.callsTo(
        'PUT',
        'library_filter_settings/settings00000001',
      );
      expect(put.body.data).toMatchObject({
        type: 'library_filter_settings',
        id: 'settings00000001',
        attributes: { enabled: true },
      });
    });

    it('reverts and shows a toast when saving fails', async () => {
      await openFiltersTab();
      api.fail('PUT', 'library_filter_settings', 500);

      toggle($('filter-enabled-toggle'), true);

      await vi.waitFor(() =>
        expect($('filter-enabled-toggle').checked).toBe(false),
      );
      expect(document.getElementById('app-toast').textContent).toBe(
        'Failed to change filtering.',
      );
      expect(changesSaved()).toBe(false);
    });

    it('is disabled with a message when it cannot load', async () => {
      api.fail('GET', 'library_filter_settings', 500);

      await openFiltersTab();

      expect($('filter-enabled-toggle').disabled).toBe(true);
      expect($('filter-switch-item').textContent).toContain(
        'Failed to load the filtering setting',
      );
    });
  });

  describe('list view', () => {
    it('renders each filter with its rule count, status, and actions', async () => {
      const frame = api.addTag('Frame');
      const beach = api.addTag('Beach');
      api.addFilter('Active one', {
        description: 'shown',
        isActive: true,
        tags: [frame, beach],
      });
      api.addFilter('Ready', { tags: [frame] });
      api.addFilter('Empty');

      await openFiltersTab();

      const active = rowFor('Active one');
      expect(active.cells[1].textContent).toBe('shown');
      expect(active.cells[2].textContent).toBe('2');
      expect(active.querySelector('.badge-active').textContent).toBe('Active');
      expect(active.querySelector('.filter-delete-btn')).toBeNull();
      expect(active.querySelector('.delete-disabled').title).toBe(
        'Active filter cannot be deleted',
      );

      const ready = rowFor('Ready');
      expect(ready.querySelector('.filter-activate-btn').disabled).toBe(false);
      expect(ready.querySelector('.filter-delete-btn')).not.toBeNull();

      const empty = rowFor('Empty');
      const activate = empty.querySelector('.filter-activate-btn');
      expect(activate.disabled).toBe(true);
      expect(activate.title).toBe('Add a rule before activating this filter');
      expect(empty.cells[2].textContent).toBe('0');
    });

    it('renders names as text, not markup', async () => {
      api.addFilter('<img src=x onerror=alert(1)>');

      await openFiltersTab();

      expect($('filter-list-body').querySelector('img')).toBeNull();
      expect(listNames()).toEqual(['<img src=x onerror=alert(1)>']);
    });

    it('paginates', async () => {
      for (let i = 1; i <= 6; i++) api.addFilter(`F${i}`);

      await openFiltersTab();

      expect($('filter-page-info').textContent).toBe('Page 1 of 2');
      expect($('filter-page-prev').disabled).toBe(true);
      expect($('filter-page-next').disabled).toBe(false);

      click($('filter-page-next'));
      await vi.waitFor(() => expect(listNames()).toEqual(['F6']));
      expect($('filter-page-info').textContent).toBe('Page 2 of 2');
    });

    it('shows a placeholder when the list cannot load', async () => {
      api.fail('GET', 'library_filters', 500);

      await openFiltersTab();

      expect($('filter-list-body').textContent).toContain(
        'Failed to load filters',
      );
    });

    it('activates a filter with a full update', async () => {
      const frame = api.addTag('Frame');
      api.addFilter('Old', { isActive: true, tags: [frame] });
      const ready = api.addFilter('Ready', { description: 'd', tags: [frame] });
      await openFiltersTab();

      click(rowFor('Ready').querySelector('.filter-activate-btn'));

      await vi.waitFor(() =>
        expect(rowFor('Ready').querySelector('.badge-active')).not.toBeNull(),
      );
      const [put] = api.callsTo('PUT', `library_filters/${ready.id}`);
      expect(put.body.data.attributes).toEqual({
        name: 'Ready',
        description: 'd',
        is_active: true,
      });
      expect(rowFor('Old').querySelector('.badge-active')).toBeNull();
      expect(changesSaved()).toBe(true);
    });

    it('shows a toast when activation fails', async () => {
      const frame = api.addTag('Frame');
      api.addFilter('Ready', { tags: [frame] });
      await openFiltersTab();
      api.fail('PUT', 'library_filters', 400, 'rule_required', 'Needs a rule');

      click(rowFor('Ready').querySelector('.filter-activate-btn'));

      await vi.waitFor(() =>
        expect(document.getElementById('app-toast').textContent).toBe(
          'Needs a rule',
        ),
      );
      expect($('error-message').classList.contains('show')).toBe(false);
      expect(
        rowFor('Ready').querySelector('.filter-activate-btn').disabled,
      ).toBe(false);
    });

    it('deletes a filter', async () => {
      const gone = api.addFilter('Gone');
      api.addFilter('Kept');
      await openFiltersTab();

      click(rowFor('Gone').querySelector('.filter-delete-btn'));

      await vi.waitFor(() => expect(listNames()).toEqual(['Kept']));
      expect(api.callsTo('DELETE', `library_filters/${gone.id}`)).toHaveLength(
        1,
      );
      expect(changesSaved()).toBe(true);
    });

    it('keeps the row and shows a toast when delete fails', async () => {
      api.addFilter('Stuck');
      await openFiltersTab();
      api.fail('DELETE', 'library_filters', 500);

      click(rowFor('Stuck').querySelector('.filter-delete-btn'));

      await vi.waitFor(() =>
        expect(document.getElementById('app-toast').textContent).toBe(
          'Failed to delete the filter.',
        ),
      );
      expect(listNames()).toEqual(['Stuck']);
    });
  });

  describe('detail view', () => {
    it('opens empty in create mode', async () => {
      await openFiltersTab();

      click($('filter-new'));

      expect(visible('filter-detail-view')).toBe(true);
      expect(visible('filter-list-view')).toBe(false);
      expect(visible('main-actions')).toBe(false);
      expect(visible('filter-detail-actions')).toBe(true);
      expect($('filter-detail-title').textContent).toBe('New Filter');
      expect($('filter-name').value).toBe('');
      expect($('filter-description').value).toBe('');
      expect($('filter-active').checked).toBe(false);
      expect($('filter-active').disabled).toBe(true);
      expect(visible('filter-rules-section')).toBe(false);
    });

    it('creates a filter and switches to edit mode', async () => {
      await openFiltersTab();
      click($('filter-new'));
      $('filter-name').value = '  Frame  ';
      $('filter-description').value = 'For the frame';

      click($('filter-detail-save'));

      await vi.waitFor(() =>
        expect(visible('filter-rules-section')).toBe(true),
      );
      const [post] = api.callsTo('POST', 'library_filters');
      expect(post.body.data).toEqual({
        type: 'library_filters',
        attributes: {
          name: 'Frame',
          description: 'For the frame',
          is_active: false,
        },
      });
      expect($('filter-detail-title').textContent).toBe('Frame');
      expect($('filter-active').disabled).toBe(true);
      expect(changesSaved()).toBe(true);
    });

    it('shows a server validation error in the form', async () => {
      await openFiltersTab();
      click($('filter-new'));

      click($('filter-detail-save'));

      await vi.waitFor(() =>
        expect($('error-message').classList.contains('show')).toBe(true),
      );
      expect($('error-message').textContent).toBe('This field is required.');
      expect(document.getElementById('app-toast')).toBeNull();
      expect(visible('filter-rules-section')).toBe(false);
    });

    it('loads a filter with its rules and tag names', async () => {
      const frame = api.addTag('Frame');
      const beach = api.addTag('Beach');
      api.addFilter('Mine', {
        description: 'd',
        isActive: true,
        tags: [frame, beach],
      });
      await openFiltersTab();

      await openDetail('Mine');

      expect($('filter-detail-title').textContent).toBe('Mine');
      expect($('filter-description').value).toBe('d');
      expect($('filter-active').checked).toBe(true);
      expect($('filter-active').disabled).toBe(false);
      expect(ruleTags()).toEqual(['Frame', 'Beach']);
    });

    it('saves edits with a full update', async () => {
      const frame = api.addTag('Frame');
      const mine = api.addFilter('Mine', { description: 'old', tags: [frame] });
      await openFiltersTab();
      await openDetail('Mine');
      $('filter-name').value = 'Renamed';
      $('filter-description').value = '';
      toggle($('filter-active'), true);

      click($('filter-detail-save'));

      await vi.waitFor(() =>
        expect(api.callsTo('PUT', `library_filters/${mine.id}`)).toHaveLength(
          1,
        ),
      );
      const [put] = api.callsTo('PUT', `library_filters/${mine.id}`);
      expect(put.body.data).toEqual({
        type: 'library_filters',
        id: mine.id,
        attributes: { name: 'Renamed', description: '', is_active: true },
      });
      await vi.waitFor(() =>
        expect($('filter-detail-title').textContent).toBe('Renamed'),
      );
      expect(changesSaved()).toBe(true);
    });

    it('shows rule_required in the form, not as a toast', async () => {
      const frame = api.addTag('Frame');
      api.addFilter('Mine', { tags: [frame] });
      await openFiltersTab();
      await openDetail('Mine');
      api.fail(
        'PUT',
        'library_filters',
        400,
        'rule_required',
        'Add a rule first',
      );
      toggle($('filter-active'), true);

      click($('filter-detail-save'));

      await vi.waitFor(() =>
        expect($('error-message').textContent).toBe('Add a rule first'),
      );
      expect($('error-message').classList.contains('show')).toBe(true);
      expect(document.getElementById('app-toast')).toBeNull();
    });

    it('shows a placeholder when the filter cannot load', async () => {
      api.addFilter('Mine');
      await openFiltersTab();
      api.fail('GET', 'library_filters/', 500);

      click(rowFor('Mine').querySelector('.filter-edit-btn'));

      await vi.waitFor(() =>
        expect($('filter-detail-view').textContent).toContain(
          'Failed to load the filter.',
        ),
      );
      expect($('filter-detail-save').disabled).toBe(true);
      expect(visible('filter-detail-actions')).toBe(true);
    });

    it('deletes a rule', async () => {
      const frame = api.addTag('Frame');
      const beach = api.addTag('Beach');
      api.addFilter('Mine', { isActive: true, tags: [frame, beach] });
      await openFiltersTab();
      await openDetail('Mine');
      const [firstRule] = api.state.rules;

      click(
        $('filter-rule-list-body').querySelector('.filter-rule-delete-btn'),
      );

      await vi.waitFor(() => expect(ruleTags()).toEqual(['Beach']));
      expect(
        api.callsTo('DELETE', `library_filter_rules/${firstRule.id}`),
      ).toHaveLength(1);
      expect($('filter-active').checked).toBe(true);
      expect(changesSaved()).toBe(true);
    });

    it('turns the active toggle off and disables it after the last rule is deleted', async () => {
      const frame = api.addTag('Frame');
      api.addFilter('Mine', { isActive: true, tags: [frame] });
      await openFiltersTab();
      await openDetail('Mine');

      click(
        $('filter-rule-list-body').querySelector('.filter-rule-delete-btn'),
      );

      await vi.waitFor(() => expect(ruleTags()).toEqual([]));
      expect($('filter-active').checked).toBe(false);
      expect($('filter-active').disabled).toBe(true);
    });

    it('shows a toast when a rule delete fails', async () => {
      const frame = api.addTag('Frame');
      api.addFilter('Mine', { tags: [frame] });
      await openFiltersTab();
      await openDetail('Mine');
      api.fail('DELETE', 'library_filter_rules', 500);

      click(
        $('filter-rule-list-body').querySelector('.filter-rule-delete-btn'),
      );

      await vi.waitFor(() =>
        expect(document.getElementById('app-toast').textContent).toBe(
          'Failed to delete the rule.',
        ),
      );
      expect(ruleTags()).toEqual(['Frame']);
    });

    it('goes back to a refreshed list', async () => {
      api.addFilter('Mine');
      await openFiltersTab();
      await openDetail('Mine');
      api.addFilter('Added elsewhere');

      click($('filter-detail-back'));

      await vi.waitFor(() =>
        expect(listNames()).toEqual(['Mine', 'Added elsewhere']),
      );
      expect(visible('filter-detail-view')).toBe(false);
      expect(visible('filter-detail-actions')).toBe(false);
      expect(visible('main-actions')).toBe(true);
    });
  });

  describe('rule editor', () => {
    let mine;

    const tagLabels = () =>
      Array.from($('filter-tag-list-body').querySelectorAll('tr')).map(
        (row) => row.cells[0].textContent,
      );
    const radioFor = (label) =>
      Array.from($('filter-tag-list-body').querySelectorAll('tr'))
        .find((row) => row.cells[0].textContent === label)
        .querySelector('input[type="radio"]');

    async function openRuleEditor(trigger) {
      click(trigger);
      await vi.waitFor(() => {
        expect(visible('filter-rule-view')).toBe(true);
        expect($('filter-rule-view').getAttribute('aria-busy')).toBeNull();
      });
    }

    beforeEach(async () => {
      mine = api.addFilter('Mine');
    });

    it('lists tags and adds a rule for the chosen one', async () => {
      api.addTag('Frame', 12);
      const beach = api.addTag('Beach', 3);
      await openFiltersTab();
      await openDetail('Mine');

      await openRuleEditor($('filter-rule-add'));

      expect($('filter-rule-title').textContent).toBe('Add Rule');
      expect(visible('filter-detail-view')).toBe(false);
      expect(tagLabels()).toEqual(['Frame', 'Beach']);
      expect(
        Array.from($('filter-tag-list-body').querySelectorAll('tr')).map(
          (row) => row.cells[1].textContent,
        ),
      ).toEqual(['12', '3']);
      expect($('filter-detail-save').disabled).toBe(true);

      radioFor('Beach').checked = true;
      radioFor('Beach').dispatchEvent(
        new window.Event('change', { bubbles: true }),
      );
      expect($('filter-detail-save').disabled).toBe(false);
      click($('filter-detail-save'));

      await vi.waitFor(() => expect(visible('filter-detail-view')).toBe(true));
      const [post] = api.callsTo('POST', 'library_filter_rules');
      expect(post.body.data).toEqual({
        type: 'tag_library_filter_rules',
        attributes: {},
        relationships: {
          library_filter: { data: { type: 'library_filters', id: mine.id } },
          tag: { data: { type: 'tags', id: beach.id } },
        },
      });
      await vi.waitFor(() => expect(ruleTags()).toEqual(['Beach']));
      expect($('filter-active').disabled).toBe(false);
      expect(changesSaved()).toBe(true);
    });

    it('falls back to the canonical value when a tag has no display value', async () => {
      const tag = api.addTag('Frame');
      tag.display_value = '';
      await openFiltersTab();
      await openDetail('Mine');

      await openRuleEditor($('filter-rule-add'));

      expect(tagLabels()).toEqual(['frame']);
    });

    it('pages through tags', async () => {
      for (let i = 1; i <= 6; i++) api.addTag(`T${i}`);
      await openFiltersTab();
      await openDetail('Mine');
      await openRuleEditor($('filter-rule-add'));

      expect($('filter-tag-page-info').textContent).toBe('Page 1 of 2');
      click($('filter-tag-page-next'));

      await vi.waitFor(() => expect(tagLabels()).toEqual(['T6']));
      expect($('filter-tag-page-prev').disabled).toBe(false);
    });

    it('keeps the choice when paging away and back', async () => {
      for (let i = 1; i <= 6; i++) api.addTag(`T${i}`);
      await openFiltersTab();
      await openDetail('Mine');
      await openRuleEditor($('filter-rule-add'));
      radioFor('T2').checked = true;
      radioFor('T2').dispatchEvent(
        new window.Event('change', { bubbles: true }),
      );

      click($('filter-tag-page-next'));
      await vi.waitFor(() => expect(tagLabels()).toEqual(['T6']));
      click($('filter-tag-page-prev'));
      await vi.waitFor(() => expect(tagLabels()).toHaveLength(5));

      expect(radioFor('T2').checked).toBe(true);
      expect($('filter-detail-save').disabled).toBe(false);
    });

    it('edits a rule to use a different tag', async () => {
      const frame = api.addTag('Frame');
      const beach = api.addTag('Beach');
      api.state.rules.push({
        id: 'rule000000000099',
        filterId: mine.id,
        tagId: frame.id,
      });
      await openFiltersTab();
      await openDetail('Mine');

      await openRuleEditor(
        $('filter-rule-list-body').querySelector('.filter-rule-edit-btn'),
      );

      expect($('filter-rule-title').textContent).toBe('Edit Rule');
      expect(radioFor('Frame').checked).toBe(true);
      expect($('filter-detail-save').disabled).toBe(false);

      radioFor('Beach').checked = true;
      radioFor('Beach').dispatchEvent(
        new window.Event('change', { bubbles: true }),
      );
      click($('filter-detail-save'));

      await vi.waitFor(() => expect(ruleTags()).toEqual(['Beach']));
      const [put] = api.callsTo('PUT', 'library_filter_rules/rule000000000099');
      expect(put.body.data).toMatchObject({
        type: 'tag_library_filter_rules',
        id: 'rule000000000099',
        relationships: {
          library_filter: { data: { type: 'library_filters', id: mine.id } },
          tag: { data: { type: 'tags', id: beach.id } },
        },
      });
    });

    it('shows duplicate_rule in the form and stays in the editor', async () => {
      const frame = api.addTag('Frame');
      api.state.rules.push({
        id: 'rule000000000099',
        filterId: mine.id,
        tagId: frame.id,
      });
      await openFiltersTab();
      await openDetail('Mine');
      await openRuleEditor($('filter-rule-add'));

      radioFor('Frame').checked = true;
      radioFor('Frame').dispatchEvent(
        new window.Event('change', { bubbles: true }),
      );
      click($('filter-detail-save'));

      await vi.waitFor(() =>
        expect($('error-message').textContent).toBe(
          'This library filter already has a rule for that tag',
        ),
      );
      expect(visible('filter-rule-view')).toBe(true);
      expect(document.getElementById('app-toast')).toBeNull();
    });

    it('explains how to get tags when there are none', async () => {
      await openFiltersTab();
      await openDetail('Mine');

      await openRuleEditor($('filter-rule-add'));

      expect(visible('filter-tag-empty')).toBe(true);
      expect($('filter-tag-empty').textContent).toBe(
        'No tags yet. Run Rescan Library.',
      );
      expect(visible('filter-tag-table')).toBe(false);
      expect($('filter-detail-save').disabled).toBe(true);
    });

    it('shows a placeholder when tags cannot load', async () => {
      await openFiltersTab();
      await openDetail('Mine');
      api.fail('GET', 'tags', 500);

      await openRuleEditor($('filter-rule-add'));

      expect($('filter-tag-list-body').textContent).toContain(
        'Failed to load tags',
      );
      expect($('filter-detail-save').disabled).toBe(true);
    });

    it('goes back to the filter without saving', async () => {
      api.addTag('Frame');
      await openFiltersTab();
      await openDetail('Mine');
      await openRuleEditor($('filter-rule-add'));

      click($('filter-detail-back'));

      expect(visible('filter-detail-view')).toBe(true);
      expect(visible('filter-rule-view')).toBe(false);
      expect(api.callsTo('POST', 'library_filter_rules')).toHaveLength(0);
    });

    it('offers no way to create a tag', async () => {
      api.addTag('Frame');
      await openFiltersTab();
      await openDetail('Mine');
      await openRuleEditor($('filter-rule-add'));

      expect(
        $('filter-rule-view').querySelector('input[type="text"]'),
      ).toBeNull();
      expect(
        api.state.calls.some((c) => c.method === 'POST' && c.path === 'tags'),
      ).toBe(false);
    });
  });
});
