import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const localApiTarget = loadEnv(
    mode,
    process.cwd(),
    "",
  ).VITE_DEV_API_PROXY_TARGET;

  return {
    plugins: [react()],
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
