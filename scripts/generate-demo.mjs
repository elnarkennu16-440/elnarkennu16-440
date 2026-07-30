#!/usr/bin/env node

import { copyFile, rm } from "node:fs/promises";
import { resolve } from "node:path";
import { loadConfig, readFlag, repositoryRoot } from "./lib/config.mjs";
import { generateHeroAssets } from "./lib/hero.mjs";

const source = readFlag("--source");
if (!source) {
  console.error("Usage: npm run generate:demo -- --source /absolute/path/to/private-demo-portrait.png");
  process.exit(1);
}

try {
  const outputDirectory = resolve(repositoryRoot, "docs/assets");
  const config = await loadConfig(resolve(repositoryRoot, "examples/wildan.config.json"));
  const manifest = await generateHeroAssets({ config, sourcePath: resolve(source), outputDirectory });
  const stableNames = {
    desktopDark: "demo-dark.svg",
    desktopLight: "demo-light.svg",
    mobileDark: "demo-mobile-dark.svg",
    mobileLight: "demo-mobile-light.svg"
  };

  await Promise.all(Object.entries(stableNames).map(([key, filename]) => copyFile(
    resolve(outputDirectory, manifest.assets[key]),
    resolve(outputDirectory, filename)
  )));
  await Promise.all([...Object.values(manifest.assets).map((filename) => rm(resolve(outputDirectory, filename))), rm(resolve(outputDirectory, "manifest.json"))]);
  console.log("Generated stable public demo assets without copying the source portrait.");
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
