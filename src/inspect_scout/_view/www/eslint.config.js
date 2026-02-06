import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import importPlugin from "eslint-plugin-import";
import reactRefreshPlugin from "eslint-plugin-react-refresh";
import prettierConfig from "eslint-config-prettier";

export default tseslint.config(
  {
    ignores: [
      "dist/",
      "node_modules/",
      "build/",
      "scripts/",
      "playwright-report/",
      "test-results/",
      "*.config.?s",
      "*.config.cjs",
      "src/types/generated.ts",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  //...tseslint.configs.strictTypeChecked,
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
      import: importPlugin
    },
    rules: {
      "import/order": [
        "error",
        {
          groups: [
            "builtin",
            "external",
            "internal",
            "parent",
            "sibling",
            "index",
          ],
          "newlines-between": "always",
          alphabetize: {
            order: "asc",
            caseInsensitive: true,
          },
        },
      ],
      // React Hooks rules
      "react-hooks/rules-of-hooks": "warn",
      // "react-hooks/exhaustive-deps": "warn",

      // These are disabled because we didn't have time to fix them, not because they are bad rules
      "no-unused-vars": "off",
      "@typescript-eslint/no-unsafe-call": "off",
      "@typescript-eslint/no-redundant-type-constituents": "off",
      "@typescript-eslint/no-unsafe-assignment": "off",
      "@typescript-eslint/no-unsafe-member-access": "off",
      "@typescript-eslint/no-unsafe-return": "off",
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-base-to-string": "off",
      "@typescript-eslint/unbound-method": "off",
      "@typescript-eslint/no-unsafe-argument": "off",
      "@typescript-eslint/no-unused-vars": "off",
      // "@typescript-eslint/no-unused-vars": [
      //   "error",
      //   { varsIgnorePattern: "^_" },
      // ]
      // ...reactPlugin.configs.recommended.rules,
      // ...reactPlugin.configs["jsx-runtime"].rules,
      // ...reactHooksPlugin.configs.recommended.rules,
      // ...reactRefreshPlugin.configs.recommended.rules,
      // // We may want to remove the disables below as we see fit
      // "@typescript-eslint/restrict-template-expressions": "off",
      // "@typescript-eslint/no-unnecessary-type-parameters": "off",
    },
    // "react/prop-types": "off",
    settings: {
      react: {
        version: "detect",
      },
      "import/resolver": {
        typescript: true,
        node: true,
      },
    },
  },
  prettierConfig
);
