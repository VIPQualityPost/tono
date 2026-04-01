import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  js.configs.recommended,
  {
    files: ['src/**/*.{js,jsx}'],
    plugins: { 'react-hooks': reactHooks },
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: {
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
        ClipboardItem: 'readonly',
        CSS: 'readonly',
        ResizeObserver: 'readonly',
        MutationObserver: 'readonly',
        IntersectionObserver: 'readonly',
        atob: 'readonly',
        btoa: 'readonly',
        performance: 'readonly',
        structuredClone: 'readonly',
        queueMicrotask: 'readonly',
      },
    },
    rules: {
      // Prevent the TDZ bug
      'no-use-before-define': ['error', { functions: false, classes: false, variables: true }],

      // React hooks correctness
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',

      // Turn off rules that are noisy without adding safety
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-empty': 'off',
      'no-prototype-builtins': 'off',
    },
  },
];
