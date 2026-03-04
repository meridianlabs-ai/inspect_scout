import react from "@vitejs/plugin-react";
import { resolve } from "path";
import { defineConfig, type Plugin } from "vite";
import dts from "vite-plugin-dts";

// ---------------------------------------------------------------------------
// BEGIN MONOREPO MIGRATION HACK — remove when www/ moves into ts-mono workspace.
//
// We alias @tsmono/* to ts-mono/packages/*/src so www/ can consume shared
// code before the full migration. Because those source files live outside
// www/, two problems arise:
//   1. Rollup resolves their bare imports (json5, react, …) relative to the
//      source file's location, where no node_modules exists.
//   2. esbuild walks up to ts-mono's tsconfig.json which extends a workspace
//      package (@tsmono/tsconfig) that isn't installed.
//
// resolveMonorepoDeps() fixes (1); esbuild.tsconfigRaw fixes (2).
// ---------------------------------------------------------------------------
const tsMonoDir = resolve(__dirname, "../ts-mono");
function resolveMonorepoDeps(): Plugin {
  return {
    name: "resolve-monorepo-deps",
    enforce: "pre",
    async resolveId(source, importer, options) {
      if (!importer?.startsWith(tsMonoDir) || source.startsWith(".")) return;
      const resolved = await this.resolve(source, resolve(__dirname, "src/_virtual.ts"), {
        ...options,
        skipSelf: true,
      });
      return resolved;
    },
  };
}
// END MONOREPO MIGRATION HACK

export default defineConfig(({ mode }) => {
  const isLibrary = mode === "library";
  const baseConfig = {
    // BEGIN MONOREPO MIGRATION HACK — see comment at top of file.
    resolve: {
      alias: {
        "@tsmono/util": resolve(__dirname, "../ts-mono/packages/util/src"),
        "@tsmono/react": resolve(__dirname, "../ts-mono/packages/react/src"),
      },
    },
    // END MONOREPO MIGRATION HACK
    plugins: [
      resolveMonorepoDeps(), // MONOREPO MIGRATION HACK
      react({
        jsxRuntime: "automatic",
      }),
    ],
    // BEGIN MONOREPO MIGRATION HACK — see comment at top of file.
    esbuild: {
      tsconfigRaw: "{}",
    },
    // END MONOREPO MIGRATION HACK
    define: {
      __DEV_WATCH__: JSON.stringify(process.env.DEV_LOGGING === "true"),
      __LOGGING_FILTER__: JSON.stringify(
        process.env.DEV_LOGGING_NAMESPACES || "*"
      ),
      __SCOUT_RUN_SCAN__: JSON.stringify(process.env.SCOUT_RUN_SCAN === "true"),
    },
  };
  if (isLibrary) {
    // Library build configuration
    return {
      ...baseConfig,
      plugins: [
        ...baseConfig.plugins,
        dts({
          insertTypesEntry: true,
          exclude: ["**/*.test.ts", "**/*.test.tsx", "src/tests/**/*"],
        }),
      ],
      build: {
        outDir: "lib",
        lib: {
          entry: resolve(__dirname, "src/index.ts"),
          name: "InspectScoutLogViewer",
          fileName: "index",
          formats: ["es"],
        },
        rollupOptions: {
          external: ["react", "react-dom", "@tanstack/react-query"],
          output: {
            globals: {
              react: "React",
              "react-dom": "ReactDOM",
            },
            assetFileNames: (assetInfo) => {
              if (assetInfo.name && assetInfo.name.endsWith(".css")) {
                return "styles/[name].[ext]";
              }
              return "assets/[name].[ext]";
            },
          },
        },
        cssCodeSplit: false,
        sourcemap: true,
        minify: false,
      },
    };
  } else {
    // App build configuration
    return {
      ...baseConfig,
      base: "",
      server: {
        proxy: {
          "/api": {
            target: "http://127.0.0.1:7576",
            changeOrigin: true,
          },
        },
      },
      build: {
        outDir: "dist",
        emptyOutDir: true,
        minify: mode !== "development",
        rollupOptions: {
          output: {
            manualChunks(id) {
              // Let mathxyjax3's pre-built chunks stay separate —
              // they use a global MathJax object set up by their entry
              // and break if inlined out of order.
              if (id.includes("mathxyjax3/dist/") && !id.endsWith("index.js")) {
                return undefined;
              }
              // Everything else goes into the main bundle
            },
            entryFileNames: `assets/[name]-[hash].js`,
            chunkFileNames: `assets/[name]-[hash].js`,
            assetFileNames: `assets/[name]-[hash].[ext]`,
          },
        },
        sourcemap: true,
      },
    };
  }
});
