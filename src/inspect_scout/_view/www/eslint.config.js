import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import reactRefreshPlugin from 'eslint-plugin-react-refresh';
import prettierConfig from 'eslint-config-prettier';

export default tseslint.config(
  {
    ignores: ['dist/', 'node_modules/', 'build/', '*.config.?s'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: {
          allowDefaultProject: ['*.config.js', '*.config.ts'],
        },
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    plugins: {
      react: reactPlugin,
      'react-hooks': reactHooksPlugin,
      'react-refresh': reactRefreshPlugin,
    },
    rules: {
      ...reactPlugin.configs.recommended.rules,
      ...reactPlugin.configs['jsx-runtime'].rules,
      ...reactHooksPlugin.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      'react/prop-types': 'off',
      // These are disabled because we didn't have time to fix them, not because they are bad rules
      'no-unused-vars': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unsafe-return': 'off',
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
  },
  prettierConfig
);
