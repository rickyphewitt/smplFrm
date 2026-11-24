import { describe, it, expect } from 'vitest';

import { buildResourceDocument } from '../../src/smplfrm/smplfrm/static/jsonApiClient.js';

describe('buildResourceDocument', () => {
  it('builds a create document without id or relationships', () => {
    expect(buildResourceDocument('widgets', null, { name: 'a' })).toEqual({
      data: { type: 'widgets', attributes: { name: 'a' } },
    });
  });

  it('adds the id for an update', () => {
    expect(buildResourceDocument('widgets', 'w1', { name: 'a' })).toEqual({
      data: { type: 'widgets', id: 'w1', attributes: { name: 'a' } },
    });
  });

  it('adds relationships when given', () => {
    const relationships = {
      owner: { data: { type: 'owners', id: 'o1' } },
    };

    expect(buildResourceDocument('widgets', 'w1', {}, relationships)).toEqual({
      data: {
        type: 'widgets',
        id: 'w1',
        attributes: {},
        relationships,
      },
    });
  });
});
