import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['tests/javascript/**/*.test.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'html'],
      include: ['src/smplfrm/smplfrm/static/**/*.js'],
      exclude: ['**/*.test.js']
    }
  }
});
