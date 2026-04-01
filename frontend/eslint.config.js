import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import tseslint from 'typescript-eslint';

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.{js,jsx,ts,tsx}'],
    plugins: {
      react,
      'react-hooks': reactHooks,
    },
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parser: tseslint.parser,
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: {
        // Browser APIs
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        requestAnimationFrame: 'readonly',
        cancelAnimationFrame: 'readonly',
        navigator: 'readonly',
        crypto: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        Blob: 'readonly',
        File: 'readonly',
        FileReader: 'readonly',
        FormData: 'readonly',
        Headers: 'readonly',
        Image: 'readonly',
        WebSocket: 'readonly',
        HTMLElement: 'readonly',
        Element: 'readonly',
        ClipboardItem: 'readonly',
        CSS: 'readonly',
        ResizeObserver: 'readonly',
        MutationObserver: 'readonly',
        IntersectionObserver: 'readonly',
        TextEncoder: 'readonly',
        TextDecoder: 'readonly',
        Buffer: 'readonly',
        atob: 'readonly',
        btoa: 'readonly',
        performance: 'readonly',
        structuredClone: 'readonly',
        queueMicrotask: 'readonly',
      },
    },
    settings: {
      react: { version: 'detect' },
    },
    rules: {
      // Prevent the TDZ bug
      'no-use-before-define': ['error', { functions: false, classes: false, variables: true }],

      // React hooks correctness
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',

      // React JSX correctness
      'react/jsx-key': 'error',
      'react/jsx-no-duplicate-props': 'error',
      'react/no-children-prop': 'error',
      'react/no-danger-with-children': 'error',
      'react/no-direct-mutation-state': 'error',
      'react/no-unescaped-entities': 'warn',

      // Turn off rules that are noisy without adding safety
      'react/react-in-jsx-scope': 'off',       // not needed with React 17+ JSX transform
      'react/prop-types': 'off',                // no PropTypes in this codebase
      'react/no-unknown-property': 'off',       // false positives with Three.js / custom attrs
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-require-imports': 'off',
      'no-empty': 'off',
      'no-prototype-builtins': 'off',
    },
    linterOptions: {
      reportUnusedDisableDirectives: 'off',
    },
  },
];
