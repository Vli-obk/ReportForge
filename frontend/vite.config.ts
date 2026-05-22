import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 4028,
    proxy: {
      "/api": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
});
