import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import reactRefreshPlugin from "eslint-plugin-react-refresh";
import prettierConfig from "eslint-config-prettier";

export default tseslint.config(
  {
    ignores: ["dist/", "node_modules/", "build/", "*.config.?s"],
  },
  js.configs.recommended,
  // ...tseslint.configs.recommendedTypeChecked,
  ...tseslint.configs.strictTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: {
          allowDefaultProject: ["*.config.js", "*.config.ts", "*.config.cjs"],
        },
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    files: ["**/*.{ts,tsx}"],
    plugins: {
      react: reactPlugin,
      "react-hooks": reactHooksPlugin,
      "react-refresh": reactRefreshPlugin,
    },
    rules: {
      ...reactPlugin.configs.recommended.rules,
      ...reactPlugin.configs["jsx-runtime"].rules,
      ...reactHooksPlugin.configs.recommended.rules,
      ...reactRefreshPlugin.configs.recommended.rules,
      // We may want to remove the disables below as we see fit
      "@typescript-eslint/restrict-template-expressions": "off",
      "@typescript-eslint/no-unnecessary-type-parameters": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { varsIgnorePattern: "^_" },
      ],
    },
    settings: {
      react: {
        version: "detect",
      },
    },
  },
  prettierConfig
);
