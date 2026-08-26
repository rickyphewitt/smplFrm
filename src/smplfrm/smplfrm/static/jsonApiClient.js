/**
 * JSON:API client wrapper for smplFrm.
 *
 * Provides utilities for consuming JSON:API endpoints:
 * - fetchJsonApi: fetch with proper Accept header and error handling
 * - unwrapResource: extract resource from data envelope
 * - unwrapResourceList: extract resource array from data envelope with pagination
 * - unwrapErrors: extract errors array
 * - buildResourceDocument: build JSON:API request document for create/update
 * - formatWeatherTemp: concatenate value + "°" + scale
 */

import { resilientFetch } from './resilientFetch.js';

/**
 * JSON:API media type.
 */
export const JSONAPI_MEDIA_TYPE = 'application/vnd.api+json';

/**
 * Custom error class for JSON:API errors.
 */
export class JsonApiError extends Error {
  constructor(status, errors) {
    super(errors[0]?.detail || 'An error occurred');
    this.name = 'JsonApiError';
    this.status = status;
    this.errors = errors;
  }
}

/**
 * Fetch a JSON:API endpoint with proper headers and error handling.
 *
 * Uses resilientFetch under the hood to preserve 429/Retry-After handling.
 *
 * @param {string} url - The request URL
 * @param {RequestInit} [options] - Standard fetch options (headers will be merged)
 * @returns {Promise<Object>} - Parsed JSON response
 * @throws {JsonApiError} - On non-ok responses with JSON:API errors
 */
export async function fetchJsonApi(url, options = {}) {
  const headers = {
    Accept: JSONAPI_MEDIA_TYPE,
    ...options.headers,
  };

  // Add Content-Type for requests with body
  if (options.body) {
    headers['Content-Type'] = JSONAPI_MEDIA_TYPE;
  }

  const response = await resilientFetch(url, {
    ...options,
    headers,
  });

  // Parse JSON body
  const data = await response.json();

  // Handle non-ok responses
  if (!response.ok) {
    const errors = unwrapErrors(data);
    throw new JsonApiError(response.status, errors);
  }

  return data;
}

/**
 * Extract the resource object from a JSON:API document.
 *
 * @param {Object} document - JSON:API document with top-level 'data'
 * @returns {Object|null} - The resource object (with type, id, attributes) or null
 */
export function unwrapResource(document) {
  if (!document || document.data === null || document.data === undefined) {
    return null;
  }
  return document.data;
}

/**
 * Extract the resource array and pagination info from a JSON:API list document.
 *
 * @param {Object} document - JSON:API document with top-level 'data' array
 * @returns {Object} - { resources: Array, meta: Object, links: Object }
 */
export function unwrapResourceList(document) {
  if (!document) {
    return { resources: [], meta: {}, links: {} };
  }
  return {
    resources: document.data || [],
    meta: document.meta || {},
    links: document.links || {},
  };
}

/**
 * Extract the errors array from a JSON:API error response.
 *
 * @param {Object} document - JSON:API document with top-level 'errors'
 * @returns {Array} - Array of error objects, empty if no errors key
 */
export function unwrapErrors(document) {
  if (!document || !document.errors) {
    return [];
  }
  return document.errors;
}

/**
 * Build a JSON:API request document for create/update operations.
 *
 * @param {string} type - Resource type (e.g., "plugins")
 * @param {string} [id] - Resource id (required for update, omit for create)
 * @param {Object} attributes - Resource attributes
 * @returns {Object} - JSON:API document with data.type, data.id, data.attributes
 */
export function buildResourceDocument(type, id, attributes) {
  const doc = {
    data: {
      type,
      attributes,
    },
  };
  if (id) {
    doc.data.id = id;
  }
  return doc;
}

/**
 * Format a temperature value and scale for display.
 *
 * @param {string} value - The temperature value (e.g., "72", "N/A")
 * @param {string} scale - The temperature scale (e.g., "F", "C")
 * @returns {string} - Formatted temperature (e.g., "72°F")
 */
export function formatWeatherTemp(value, scale) {
  return `${value}°${scale}`;
}
