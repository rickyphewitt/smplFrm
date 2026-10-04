import globals from 'globals';
import eslintConfigPrettier from 'eslint-config-prettier';

export default [
  // Local, untracked build and environment output: virtualenvs (they vendor
  // Django admin JS), collectstatic output, and coverage reports.
  {
    ignores: ['.venv/', 'local_venv/', 'src/smplfrm/staticfiles/', 'coverage/'],
  },
  {
    files: [
      'src/**/static/**/*.js',
      'tests/javascript/**/*.js',
      'vitest.config.js',
    ],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
      },
    },
    rules: {
      // ignoreRestSiblings: `const { id, ...rest } = obj` is the idiom for
      // omitting keys from a copy, so the omitted names are not "unused".
      'no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', ignoreRestSiblings: true },
      ],
      'no-undef': 'error',
    },
  },
  {
    files: ['tests/javascript/**/*.js', 'vitest.config.js'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },
  eslintConfigPrettier,
];
