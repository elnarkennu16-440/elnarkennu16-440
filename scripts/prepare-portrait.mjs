/**
 * Converts a portrait with a plain white/light background into a transparent PNG.
 * Usage: node scripts/prepare-portrait.mjs --source "C:\path\to\photo.jpg"
 */
import { mkdir, writeFile } from "node:fs/promises";
import { basename, resolve } from "node:path";
import sharp from "sharp";

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--source" && argv[index + 1]) {
      args.source = argv[index + 1];
      index += 1;
    }
    if (argv[index] === "--output" && argv[index + 1]) {
      args.output = argv[index + 1];
      index += 1;
    }
    if (argv[index] === "--threshold" && argv[index + 1]) {
      args.threshold = Number(argv[index + 1]);
    }
  }
  return args;
}

async function removeWhiteBackground(sourcePath, outputPath, threshold = 240) {
  const image = sharp(sourcePath).ensureAlpha();
  const { data, info } = await image.raw().toBuffer({ resolveWithObject: true });

  for (let index = 0; index < data.length; index += 4) {
    const red = data[index];
    const green = data[index + 1];
    const blue = data[index + 2];
    const isBackground = red >= threshold && green >= threshold && blue >= threshold;

    if (isBackground) {
      data[index + 3] = 0;
    }
  }

  await sharp(data, {
    raw: {
      width: info.width,
      height: info.height,
      channels: 4
    }
  })
    .png()
    .toFile(outputPath);
}

const args = parseArgs(process.argv.slice(2));

if (!args.source) {
  console.error("Usage: node scripts/prepare-portrait.mjs --source \"C:\\path\\to\\photo.jpg\" [--output output.png] [--threshold 240]");
  process.exit(1);
}

const sourcePath = resolve(args.source);
const outputPath = resolve(
  args.output ?? resolve(process.cwd(), "input", `${basename(sourcePath, sourcePath.slice(sourcePath.lastIndexOf(".")))}-transparent.png`)
);

await mkdir(resolve(outputPath, ".."), { recursive: true });
await removeWhiteBackground(sourcePath, outputPath, args.threshold ?? 240);

console.log(`Saved transparent portrait to:\n  ${outputPath}`);
console.log("\nNext step:");
console.log(`  npm run generate -- --source "${outputPath}"`);
