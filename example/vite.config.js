import fs from "node:fs";
import path from "node:path";
import { defineConfig, loadEnv } from "vite";

function walk(dir) {
  const output = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      output.push(...walk(full));
      continue;
    }
    output.push(full);
  }
  return output;
}

function discoverInputs(baseDirs) {
  const entries = {};
  for (const baseDir of baseDirs) {
    if (!fs.existsSync(baseDir)) {
      continue;
    }
    for (const file of walk(baseDir)) {
      const name = path.basename(file);
      const isEntry =
        name === "entry.ts" ||
        name === "entry.js" ||
        name === "entry.head.ts" ||
        name === "entry.head.js" ||
        name.endsWith(".entry.ts") ||
        name.endsWith(".entry.js");
      if (!isEntry) {
        continue;
      }
      const rel = path.relative(process.cwd(), file).replace(/\\/g, "/");
      entries[rel] = file;
    }
  }
  return entries;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  const routesRoot = path.resolve("./hyper/routes");
  const layoutsRoot = path.resolve("./hyper/layouts");
  const sharedRoot = path.resolve("./hyper/shared");
  const inputs = discoverInputs([routesRoot, layoutsRoot, sharedRoot]);

  return {
    root: ".",
    resolve: {
      alias: {
        "@routes": routesRoot,
        "@layouts": layoutsRoot,
        "@shared": sharedRoot,
      },
    },
    build: {
      outDir: env.VITE_APP_OUTPUT_DIR || "../dist",
      emptyOutDir: true,
      manifest: true,
      rollupOptions: {
        input: inputs,
      },
    },
  };
});
