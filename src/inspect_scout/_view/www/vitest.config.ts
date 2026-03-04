import { resolve } from "path";
import { type Plugin, defineConfig } from "vitest/config";

// ---------------------------------------------------------------------------
// BEGIN MONOREPO MIGRATION HACK — remove when www/ moves into ts-mono workspace.
// See vite.config.ts top-of-file comment for full explanation.
// ---------------------------------------------------------------------------
const tsMonoDir = resolve(__dirname, "../ts-mono");
function resolveMonorepoDeps(): Plugin {
  return {
    name: "resolve-monorepo-deps",
    enforce: "pre",
    async resolveId(source, importer, options) {
      if (!importer?.startsWith(tsMonoDir) || source.startsWith(".")) return;
      const resolved = await this.resolve(
        source,
        resolve(__dirname, "src/_virtual.ts"),
        {
          ...options,
          skipSelf: true,
        }
      );
      return resolved;
    },
  };
}
// END MONOREPO MIGRATION HACK

export default defineConfig({
  // BEGIN MONOREPO MIGRATION HACK — see comment above.
  plugins: [resolveMonorepoDeps()],
  resolve: {
    alias: {
      "@tsmono/util": resolve(__dirname, "../ts-mono/packages/util/src"),
      "@tsmono/react": resolve(__dirname, "../ts-mono/packages/react/src"),
      "@tsmono/react/components": resolve(
        __dirname,
        "../ts-mono/packages/react/src/components"
      ),
      "@tsmono/react/hooks": resolve(
        __dirname,
        "../ts-mono/packages/react/src/hooks"
      ),
    },
  },
  esbuild: {
    tsconfigRaw: "{}",
    jsx: "automatic",
  },
  // END MONOREPO MIGRATION HACK
  test: {
    include: ["src/**/*.test.ts"],
    setupFiles: ["src/test/setup-msw.ts"],
  },
});
