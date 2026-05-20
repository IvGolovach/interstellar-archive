import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const pagesBase = process.env.GITHUB_ACTIONS ? "/interstellar-archive/" : "/";

export default defineConfig({
  base: pagesBase,
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("artifacts/public/browser_dataset_contract")) {
            return "browser_dataset_contract";
          }
          if (id.includes("artifacts/capsule_risk_budget.v1.json")) {
            return "capsule_risk_budget";
          }
        },
      },
    },
  },
  server: {
    fs: {
      allow: [resolve(__dirname, "..")],
    },
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx", "tests/test_no_math_random_usage.ts"],
  },
});
