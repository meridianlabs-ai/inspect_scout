import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    react({
      jsxRuntime: "automatic",
    }),
  ],
  base: "",
  build: {
    outDir: "dist",
    minify: false,
    rollupOptions: {
      output: {
        entryFileNames: `assets/index.js`,
        chunkFileNames: `assets/[name].js`,
        assetFileNames: `assets/[name].[ext]`,
      },
    },
    sourcemap: true,
  },
  define: {
    __DEV_WATCH__: JSON.stringify(process.env.DEV_LOGGING === "true"),
    __LOGGING_FILTER__: JSON.stringify(
      process.env.DEV_LOGGING_NAMESPACES || "*"
    ),
  },
});
