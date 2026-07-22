import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Keep local browser configuration beside the Vite application source.
  const envDir = dirname(fileURLToPath(import.meta.url));
  const localApiTarget = loadEnv(
    mode,
    envDir,
    "",
  ).VITE_DEV_API_PROXY_TARGET;

  return {
    plugins: [react()],
    envDir,
    // The proxy is deliberately opt-in for local development only. Vercel
    // receives the Render URL from VITE_API_URL and never uses this setting.
    server: localApiTarget && mode === "development"
      ? {
          proxy: {
            "/api": {
              target: localApiTarget,
              changeOrigin: true,
            },
          },
        }
      : undefined,
  };
});
