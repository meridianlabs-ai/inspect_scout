import react from "@vitejs/plugin-react";
import { resolve } from "path";
import { defineConfig } from "vite";
import dts from "vite-plugin-dts";

export default defineConfig(({ mode }) => {
  const isLibrary = mode === "library";
  const baseConfig = {
    plugins: [
      react({
        jsxRuntime: "automatic",
      }),
    ],
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
              if (id.includes("json-worker")) return "json-worker";
              if (!id.includes("node_modules")) return;
              // Be careful about doing anything with mathxyjax3 since it ships
              // pre-bundled chunks that communicate via globalThis.MathJax;
              // forcing them into a single rollup chunk breaks the internal
              // dynamic imports and global references.
              if (/ag-grid|apache-arrow|arquero|flechette|acorn/.test(id))
                return "vendor-grid";
              if (/asciinema/.test(id)) return "vendor-asciinema";
              if (/prismjs/.test(id)) return "vendor-prism";
              if (/@tanstack/.test(id)) return "vendor-tanstack";
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
