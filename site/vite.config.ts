import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { realpathSync } from "node:fs";

export default defineConfig({
  base: "/robot-arm/",
  plugins: [react()],
  // Worktrees may share dependencies through a symlink; allow their resolved assets.
  server: { fs: { allow: [__dirname, realpathSync(resolve(__dirname, "node_modules"))] } },
  build: {
    assetsInlineLimit: 0,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        simulator: resolve(__dirname, "simulator/index.html"),
      },
    },
  },
});
