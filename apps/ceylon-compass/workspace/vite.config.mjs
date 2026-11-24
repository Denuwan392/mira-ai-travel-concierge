import { defineConfig } from "vite";
import tailwind from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";

const local = (path) => fileURLToPath(new URL(path, import.meta.url));
export default defineConfig({
  root: local("./"),
  publicDir: false,
  base: "/workspace/",
  plugins: [tailwind()],
  resolve: { alias: { "@": local("../src") } },
  build: { outDir: local("../public/workspace"), emptyOutDir: true },
});
