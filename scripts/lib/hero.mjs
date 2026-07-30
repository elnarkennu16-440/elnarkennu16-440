import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, unlink, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import sharp from "sharp";
import { clamp, escapeXml } from "./xml.mjs";

const GENERATOR_VERSION = "agent-console-v1";

const paletteDefinitions = {
  signal: {
    dark: { backgroundStart: "#020617", backgroundEnd: "#11152F", panel: "#07111F", primary: "#E5E7EB", muted: "#64748B", cyan: "#22D3EE", blue: "#38BDF8", violet: "#7C3AED", green: "#10B981", red: "#F87171", scanBlend: "screen" },
    light: { backgroundStart: "#F8FBFF", backgroundEnd: "#F5F3FF", panel: "#FFFFFF", primary: "#172554", muted: "#64748B", cyan: "#0891B2", blue: "#2563EB", violet: "#6D28D9", green: "#047857", red: "#DC2626", scanBlend: "multiply" }
  },
  ocean: {
    dark: { backgroundStart: "#02131A", backgroundEnd: "#111827", panel: "#061A22", primary: "#E5F6F8", muted: "#6B8791", cyan: "#2DD4BF", blue: "#38BDF8", violet: "#6366F1", green: "#34D399", red: "#FB7185", scanBlend: "screen" },
    light: { backgroundStart: "#F4FCFC", backgroundEnd: "#F4F7FF", panel: "#FFFFFF", primary: "#123047", muted: "#64748B", cyan: "#0F766E", blue: "#0284C7", violet: "#4F46E5", green: "#047857", red: "#BE123C", scanBlend: "multiply" }
  },
  solar: {
    dark: { backgroundStart: "#090D14", backgroundEnd: "#1D1720", panel: "#10141C", primary: "#F3F4F6", muted: "#7C8495", cyan: "#22D3EE", blue: "#60A5FA", violet: "#F59E0B", green: "#34D399", red: "#FB7185", scanBlend: "screen" },
    light: { backgroundStart: "#FBFCFE", backgroundEnd: "#FFF8ED", panel: "#FFFFFF", primary: "#292524", muted: "#78716C", cyan: "#0891B2", blue: "#2563EB", violet: "#B45309", green: "#047857", red: "#BE123C", scanBlend: "multiply" }
  }
};

const layouts = {
  desktop: {
    width: 1180,
    height: 610,
    outerRadius: 18,
    titlebar: { x: 3, y: 3, width: 1174, height: 34, radius: 16 },
    visualPanel: { x: 14, y: 64, width: 488, height: 468, radius: 14 },
    infoPanel: { x: 508, y: 48, width: 655, height: 500, radius: 14 },
    visualTitle: { x: 30, y: 62 },
    infoTitle: { x: 524, y: 62 },
    portrait: { columns: 96, rows: 64, x: 78, y: 90, lineHeight: 6.65, fontSize: 6.5 },
    portraitClip: { x: 24, y: 82, width: 470, height: 438, radius: 12 },
    system: { x: 528, y: 82, width: 620, lineHeight: 21.5, fontSize: 14 },
    footerY: 585
  },
  mobile: {
    width: 720,
    height: 1080,
    outerRadius: 22,
    titlebar: { x: 20, y: 20, width: 680, height: 42, radius: 14 },
    visualPanel: { x: 48, y: 94, width: 624, height: 350, radius: 14 },
    infoPanel: { x: 48, y: 470, width: 624, height: 526, radius: 14 },
    visualTitle: { x: 66, y: 116 },
    infoTitle: { x: 66, y: 492 },
    portrait: { columns: 84, rows: 54, x: 180, y: 132, lineHeight: 5.7, fontSize: 6.6 },
    portraitClip: { x: 58, y: 122, width: 604, height: 312, radius: 12 },
    system: { x: 72, y: 520, width: 574, lineHeight: 21, fontSize: 13 },
    footerY: 1045
  }
};

function buildProfileLines(config) {
  const lines = [
    { type: "header", value: `@${config.profile.username}` },
    { type: "row", key: "Subject", value: config.profile.name },
    { type: "row", key: "Role", value: config.profile.headline },
    { type: "row", key: "Affiliation", value: config.profile.affiliation },
    { type: "row", key: "Base", value: config.profile.location },
    { type: "row", key: "Status", value: config.profile.status },
    { type: "blank" },
    { type: "section", value: "RESEARCH.NODE" },
    { type: "row", key: "Primary", value: config.research.primary },
    { type: "row", key: "Direction", value: config.research.direction },
    { type: "row", key: "Themes", value: config.research.themes },
    { type: "blank" },
    { type: "section", value: "BUILD.LOG" }
  ];

  config.projects.slice(0, 4).forEach((project) => {
    lines.push({ type: "row", key: project.name, value: project.heroLabel });
  });

  lines.push({ type: "blank" }, { type: "section", value: "GRID.LINKS" });
  config.links.slice(0, 2).forEach((link) => {
    lines.push({ type: "row", key: link.label, value: link.value });
  });
  lines.push({ type: "footer", value: "signal.locked > PROFILE / BUILD / SHARE" });

  return lines;
}

async function validatePortrait(sourceBuffer, sourcePath) {
  const metadata = await sharp(sourceBuffer).metadata();
  if (!metadata.hasAlpha) {
    throw new Error(`Portrait must have a transparent background. ${sourcePath} does not contain an alpha channel.`);
  }

  const { channels } = await sharp(sourceBuffer).ensureAlpha().extractChannel("alpha").stats();
  if (channels[0].min === 255) {
    throw new Error(`Portrait must contain transparent pixels. Remove the background from ${sourcePath} before generating.`);
  }
}

async function samplePortrait(sourceBuffer, columns, rows) {
  const trimOptions = { background: { r: 0, g: 0, b: 0, alpha: 0 }, threshold: 8 };
  const resizeOptions = { fit: "fill", kernel: sharp.kernel.lanczos3 };
  const luminancePipeline = sharp(sourceBuffer)
    .ensureAlpha()
    .trim(trimOptions)
    .flatten({ background: "#FFFFFF" })
    .greyscale()
    .normalise()
    .gamma(1.05)
    .sharpen()
    .resize(columns, rows, resizeOptions)
    .raw()
    .toBuffer({ resolveWithObject: true });
  const alphaPipeline = sharp(sourceBuffer)
    .ensureAlpha()
    .trim(trimOptions)
    .extractChannel("alpha")
    .resize(columns, rows, resizeOptions)
    .raw()
    .toBuffer({ resolveWithObject: true });
  const [{ data: luminance, info }, { data: alpha }] = await Promise.all([luminancePipeline, alphaPipeline]);
  const pixels = Buffer.alloc(luminance.length);

  for (let index = 0; index < luminance.length; index += 1) {
    const opacity = alpha[index] / 255;
    pixels[index] = Math.round(255 - opacity * (255 - luminance[index]));
  }

  return { pixels, width: info.width, height: info.height };
}

function createAsciiTspans({ pixels, width, height }, placement) {
  const characters = " .:-=+*#%@";
  const rows = [];

  for (let row = 0; row < height; row += 1) {
    let line = "";
    for (let column = 0; column < width; column += 1) {
      const index = row * width + column;
      const pixel = pixels[index];
      const left = pixels[row * width + Math.max(column - 1, 0)];
      const right = pixels[row * width + Math.min(column + 1, width - 1)];
      const above = pixels[Math.max(row - 1, 0) * width + column];
      const below = pixels[Math.min(row + 1, height - 1) * width + column];
      const darkness = (255 - pixel) / 255;
      const edge = (Math.abs(right - left) + Math.abs(below - above)) / 510;
      if (darkness < 0.045 && edge < 0.04) {
        line += " ";
        continue;
      }
      const ink = clamp(darkness * 1.02 + edge * 0.5 - 0.025, 0, 1);
      line += characters[Math.round(ink * (characters.length - 1))];
    }

    rows.push(`<tspan x="${placement.x}" y="${(placement.y + row * placement.lineHeight).toFixed(2)}" xml:space="preserve">${escapeXml(line)}</tspan>`);
  }

  return rows.join("\n");
}

function buildSystemLayer(profileLines, { x, y, width, lineHeight, fontSize }, colors) {
  const clips = [];
  const rows = [];

  profileLines.forEach((line, index) => {
    if (line.type === "blank") return;
    const id = `system-line-${index}`;
    const lineY = y + index * lineHeight;
    const begin = (0.68 + index * 0.105).toFixed(2);

    clips.push(`<clipPath id="${id}"><rect x="${x - 3}" y="${(lineY - fontSize - 2).toFixed(2)}" width="0" height="${fontSize + 8}"><animate attributeName="width" from="0" to="${width}" dur="0.36s" begin="${begin}s" fill="freeze"/></rect></clipPath>`);

    if (line.type === "header") {
      rows.push(`<g clip-path="url(#${id})"><text x="${x}" y="${lineY}" class="system-head"><tspan fill="${colors.violet}">${escapeXml(line.value)}</tspan><tspan fill="${colors.muted}"> ------------------------------------------</tspan></text></g>`);
    } else if (line.type === "section") {
      rows.push(`<g clip-path="url(#${id})"><text x="${x}" y="${lineY}" class="system-section" fill="${colors.green}">- ${escapeXml(line.value)} -----------------------------------</text></g>`);
    } else if (line.type === "footer") {
      rows.push(`<g clip-path="url(#${id})"><text x="${x}" y="${lineY}" class="system-footer" fill="${colors.blue}">${escapeXml(line.value)}</text></g>`);
    } else {
      const dots = ".".repeat(Math.max(3, 14 - line.key.length));
      rows.push(`<g clip-path="url(#${id})"><text x="${x}" y="${lineY}" class="system-row"><tspan fill="${colors.muted}">. </tspan><tspan class="system-key" fill="${colors.cyan}">${escapeXml(line.key)}</tspan><tspan fill="${colors.muted}">: ${dots} </tspan><tspan fill="${colors.primary}">${escapeXml(line.value)}</tspan></text></g>`);
    }
  });

  return { clips: clips.join("\n"), rows: rows.join("\n") };
}

function buildAmbientPortraitLayer(layout, colors, size) {
  const clip = layout.portraitClip;
  const isDesktop = size === "desktop";
  const centerX = clip.x + clip.width * (isDesktop ? 0.52 : 0.5);
  const centerY = clip.y + clip.height * (isDesktop ? 0.48 : 0.43);
  const orbitWidth = clip.width * (isDesktop ? 0.9 : 0.82);
  const orbitHeight = clip.height * (isDesktop ? 0.58 : 0.62);
  const left = clip.x + (isDesktop ? 28 : 34);
  const right = clip.x + clip.width - (isDesktop ? 28 : 34);
  const top = clip.y + (isDesktop ? 46 : 38);
  const bottom = clip.y + clip.height - (isDesktop ? 42 : 30);

  return `<g clip-path="url(#portrait-clip)" aria-hidden="true">
  <rect x="${clip.x}" y="${clip.y}" width="${clip.width}" height="${clip.height}" fill="url(#portrait-grid)"/>
  <ellipse cx="${centerX.toFixed(1)}" cy="${centerY.toFixed(1)}" rx="${(orbitWidth * 0.54).toFixed(1)}" ry="${(orbitHeight * 0.54).toFixed(1)}" fill="url(#portrait-halo)"/>
  <ellipse cx="${centerX.toFixed(1)}" cy="${centerY.toFixed(1)}" rx="${(orbitWidth * 0.5).toFixed(1)}" ry="${(orbitHeight * 0.5).toFixed(1)}" fill="none" stroke="${colors.blue}" stroke-width="1" stroke-dasharray="3 14" opacity="0.13"><animateTransform attributeName="transform" type="rotate" from="0 ${centerX.toFixed(1)} ${centerY.toFixed(1)}" to="360 ${centerX.toFixed(1)} ${centerY.toFixed(1)}" dur="42s" repeatCount="indefinite"/></ellipse>
  <ellipse cx="${centerX.toFixed(1)}" cy="${centerY.toFixed(1)}" rx="${(orbitWidth * 0.4).toFixed(1)}" ry="${(orbitHeight * 0.38).toFixed(1)}" fill="none" stroke="${colors.violet}" stroke-width="1" stroke-dasharray="28 24" opacity="0.1"><animateTransform attributeName="transform" type="rotate" from="360 ${centerX.toFixed(1)} ${centerY.toFixed(1)}" to="0 ${centerX.toFixed(1)} ${centerY.toFixed(1)}" dur="34s" repeatCount="indefinite"/></ellipse>
  <path d="M ${left} ${top} H ${left + (isDesktop ? 42 : 62)} M ${left} ${top} V ${top + (isDesktop ? 42 : 54)} M ${right} ${bottom} H ${right - (isDesktop ? 42 : 62)} M ${right} ${bottom} V ${bottom - (isDesktop ? 42 : 54)}" fill="none" stroke="${colors.cyan}" stroke-width="1.2" opacity="0.2"/>
  <path d="M ${left} ${(centerY + 42).toFixed(1)} C ${left + 32} ${(centerY + 8).toFixed(1)}, ${(centerX - orbitWidth * 0.3).toFixed(1)} ${(centerY + 58).toFixed(1)}, ${(centerX - orbitWidth * 0.19).toFixed(1)} ${(centerY + 27).toFixed(1)}" fill="none" stroke="${colors.blue}" opacity="0.12"/>
  <path d="M ${right} ${(centerY - 52).toFixed(1)} C ${right - 38} ${(centerY - 18).toFixed(1)}, ${(centerX + orbitWidth * 0.31).toFixed(1)} ${(centerY - 70).toFixed(1)}, ${(centerX + orbitWidth * 0.2).toFixed(1)} ${(centerY - 30).toFixed(1)}" fill="none" stroke="${colors.green}" opacity="0.11"/>
  <g fill="${colors.cyan}"><circle cx="${left}" cy="${top}" r="2.2" opacity="0.42"><animate attributeName="opacity" values="0.2;0.58;0.2" dur="5.6s" repeatCount="indefinite"/></circle><circle cx="${right}" cy="${bottom}" r="2.2" opacity="0.42"><animate attributeName="opacity" values="0.58;0.2;0.58" dur="6.4s" repeatCount="indefinite"/></circle><circle cx="${left + (isDesktop ? 12 : 18)}" cy="${(centerY + 48).toFixed(1)}" r="1.7" opacity="0.32"/><circle cx="${right - (isDesktop ? 10 : 16)}" cy="${(centerY - 58).toFixed(1)}" r="1.7" opacity="0.28"/></g>
</g>`;
}

function createHeroSvg(config, colors, size, portrait) {
  const layout = layouts[size];
  const titlebar = layout.titlebar;
  const visual = layout.visualPanel;
  const info = layout.infoPanel;
  const clip = layout.portraitClip;
  const profileLines = buildProfileLines(config);
  const ascii = createAsciiTspans(portrait, layout.portrait);
  const system = buildSystemLayer(profileLines, layout.system, colors);
  const ambientPortrait = buildAmbientPortraitLayer(layout, colors, size);
  const isDesktop = size === "desktop";
  const titleCenter = titlebar.x + titlebar.width / 2;
  const liveX = titlebar.x + titlebar.width - 138;
  const cursorY = layout.system.y + (profileLines.length - 1) * layout.system.lineHeight - 15;
  const terminalUser = config.profile.username.slice(0, isDesktop ? 22 : 14);
  const footerLabel = config.focus.slice(0, 3).map((item) => item.name.toUpperCase()).join(" / ").slice(0, 64);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${layout.width}" height="${layout.height}" viewBox="0 0 ${layout.width} ${layout.height}" role="img" aria-labelledby="title description">
<title id="title">${escapeXml(config.profile.name)} - ${escapeXml(config.profile.headline)}</title>
<desc id="description">An animated profile console with an ASCII portrait, professional focus, featured projects, and public links.</desc>
<defs>
  <linearGradient id="background" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${colors.backgroundStart}"/><stop offset="1" stop-color="${colors.backgroundEnd}"/></linearGradient>
  <linearGradient id="ascii-signal" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${colors.cyan}"><animate attributeName="stop-color" values="${colors.cyan};${colors.violet};${colors.blue};${colors.cyan}" dur="9s" repeatCount="indefinite"/></stop><stop offset="1" stop-color="${colors.violet}"><animate attributeName="stop-color" values="${colors.violet};${colors.blue};${colors.cyan};${colors.violet}" dur="9s" repeatCount="indefinite"/></stop></linearGradient>
  <linearGradient id="border" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${colors.violet}"/><stop offset="0.48" stop-color="${colors.cyan}"/><stop offset="1" stop-color="${colors.green}"/></linearGradient>
  <linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${colors.cyan}" stop-opacity="0"/><stop offset="0.5" stop-color="${colors.cyan}" stop-opacity="0.46"/><stop offset="1" stop-color="${colors.violet}" stop-opacity="0"/></linearGradient>
  <radialGradient id="portrait-halo"><stop offset="0" stop-color="${colors.cyan}" stop-opacity="0.12"/><stop offset="0.48" stop-color="${colors.blue}" stop-opacity="0.055"/><stop offset="1" stop-color="${colors.violet}" stop-opacity="0"/></radialGradient>
  <pattern id="scanlines" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="${colors.cyan}" opacity="0.052"/></pattern>
  <pattern id="portrait-grid" width="44" height="44" patternUnits="userSpaceOnUse"><path d="M 44 0 H 0 V 44" fill="none" stroke="${colors.blue}" stroke-width="0.65" opacity="0.085"/><circle cx="0" cy="0" r="1.2" fill="${colors.cyan}" opacity="0.13"/></pattern>
  <clipPath id="portrait-clip"><rect x="${clip.x}" y="${clip.y}" width="${clip.width}" height="${clip.height}" rx="${clip.radius}"/></clipPath>
  <mask id="portrait-reveal"><rect x="${clip.x}" y="${clip.y}" width="${clip.width}" height="0" rx="${clip.radius}" fill="white"><animate attributeName="height" from="0" to="${clip.height}" dur="2.1s" begin="0.12s" fill="freeze"/></rect></mask>
  ${system.clips}
  <style>
    .mono { font-family: 'Courier New', Consolas, monospace; }
    .ascii { font-family: 'Courier New', Consolas, monospace; font-size: ${layout.portrait.fontSize}px; letter-spacing: -0.15px; fill: url(#ascii-signal); }
    .panel-title { font-family: 'Courier New', Consolas, monospace; font-size: ${isDesktop ? 11 : 12}px; letter-spacing: 2px; fill: ${colors.blue}; opacity: 0.78; }
    .terminal-label { font-family: 'Courier New', Consolas, monospace; font-size: ${isDesktop ? 12 : 11}px; letter-spacing: 0.5px; fill: ${colors.muted}; }
    .live-label { font-family: 'Courier New', Consolas, monospace; font-size: 10px; letter-spacing: 1px; fill: ${colors.red}; }
    .system-head { font-family: 'Courier New', Consolas, monospace; font-size: ${layout.system.fontSize + 2}px; font-weight: 700; }
    .system-section, .system-footer, .system-row { font-family: 'Courier New', Consolas, monospace; font-size: ${layout.system.fontSize}px; }
    .system-section, .system-key { font-weight: 700; }
    text, tspan { white-space: pre; }
  </style>
</defs>
<rect width="${layout.width}" height="${layout.height}" rx="${layout.outerRadius}" fill="url(#background)"/>
<rect width="${layout.width}" height="${layout.height}" rx="${layout.outerRadius}" fill="url(#scanlines)"/>
<rect x="${titlebar.x}" y="${titlebar.y}" width="${titlebar.width}" height="${titlebar.height}" rx="${titlebar.radius}" fill="${colors.panel}" fill-opacity="0.84"/>
<circle cx="${titlebar.x + 21}" cy="${titlebar.y + titlebar.height / 2}" r="5" fill="#EF4444"/><circle cx="${titlebar.x + 39}" cy="${titlebar.y + titlebar.height / 2}" r="5" fill="#F59E0B"/><circle cx="${titlebar.x + 57}" cy="${titlebar.y + titlebar.height / 2}" r="5" fill="${colors.green}"/>
<text x="${titleCenter}" y="${titlebar.y + titlebar.height / 2 + 5}" text-anchor="middle" class="terminal-label">${escapeXml(terminalUser)}@profile ~ % ./profile --live</text>
${isDesktop ? `<circle cx="${liveX}" cy="${titlebar.y + titlebar.height / 2}" r="4" fill="${colors.red}"><animate attributeName="opacity" values="1;0.15;1" dur="1.1s" repeatCount="indefinite"/></circle><text x="${liveX + 10}" y="${titlebar.y + titlebar.height / 2 + 4}" class="live-label">SCANNING</text>` : ""}
<rect x="${visual.x}" y="${visual.y}" width="${visual.width}" height="${visual.height}" rx="${visual.radius}" fill="${colors.panel}" fill-opacity="0.38" stroke="url(#border)" stroke-opacity="0.42"/>
<rect x="${info.x}" y="${info.y}" width="${info.width}" height="${info.height}" rx="${info.radius}" fill="${colors.panel}" fill-opacity="0.42" stroke="url(#border)" stroke-opacity="0.42"/>
<text x="${layout.visualTitle.x}" y="${layout.visualTitle.y}" class="panel-title">VISUAL.MAP / PORTRAIT.SIGNAL</text>
<text x="${layout.infoTitle.x}" y="${layout.infoTitle.y}" class="panel-title">SYSTEM.INFO / RESEARCH.BUILDER</text>
${ambientPortrait}
<g clip-path="url(#portrait-clip)" mask="url(#portrait-reveal)"><text class="ascii">${ascii}</text></g>
${system.rows}
<rect x="${layout.system.x + 2}" y="${cursorY}" width="9" height="${layout.system.fontSize + 2}" fill="${colors.cyan}" opacity="0"><animate attributeName="opacity" values="0;0;1;0;1;0;1;0" keyTimes="0;0.03;0.06;0.32;0.5;0.68;0.84;1" dur="1.4s" begin="3.3s" repeatCount="indefinite"/></rect>
<text x="${layout.width / 2}" y="${layout.footerY}" text-anchor="middle" class="mono" font-size="10" letter-spacing="1.5" fill="${colors.muted}">${escapeXml(footerLabel)}</text>
<rect x="0" y="-70" width="${layout.width}" height="70" fill="url(#scan)" opacity="0.72" style="mix-blend-mode:${colors.scanBlend}"><animateTransform attributeName="transform" type="translate" from="0 -70" to="0 ${layout.height + 70}" dur="4.5s" repeatCount="indefinite"/></rect>
<rect x="3" y="3" width="${layout.width - 6}" height="${layout.height - 6}" rx="${layout.outerRadius - 2}" fill="none" stroke="url(#border)" stroke-width="2" opacity="0.76"><animate attributeName="opacity" values="0.5;0.94;0.5" dur="3.4s" repeatCount="indefinite"/></rect>
</svg>`;
}

async function cleanOldAssets(outputDirectory, currentFiles) {
  const entries = await readdir(outputDirectory).catch(() => []);
  const generatedPattern = /^agent-console-[a-f0-9]{8}-(?:mobile-)?(?:dark|light)\.svg$/;
  await Promise.all(entries
    .filter((entry) => generatedPattern.test(entry) && !currentFiles.includes(entry))
    .map((entry) => unlink(resolve(outputDirectory, entry))));
}

export async function generateHeroAssets({ config, sourcePath, outputDirectory }) {
  const sourceBuffer = await readFile(sourcePath);
  await validatePortrait(sourceBuffer, sourcePath);

  const version = createHash("sha256")
    .update(GENERATOR_VERSION)
    .update(JSON.stringify(config))
    .update(sourceBuffer)
    .digest("hex")
    .slice(0, 8);
  const palette = paletteDefinitions[config.appearance.palette];
  const desktopPortrait = await samplePortrait(sourceBuffer, layouts.desktop.portrait.columns, layouts.desktop.portrait.rows);
  const mobilePortrait = await samplePortrait(sourceBuffer, layouts.mobile.portrait.columns, layouts.mobile.portrait.rows);
  const assets = {
    desktopDark: `agent-console-${version}-dark.svg`,
    desktopLight: `agent-console-${version}-light.svg`,
    mobileDark: `agent-console-${version}-mobile-dark.svg`,
    mobileLight: `agent-console-${version}-mobile-light.svg`
  };

  await mkdir(outputDirectory, { recursive: true });
  await Promise.all([
    writeFile(resolve(outputDirectory, assets.desktopDark), createHeroSvg(config, palette.dark, "desktop", desktopPortrait)),
    writeFile(resolve(outputDirectory, assets.desktopLight), createHeroSvg(config, palette.light, "desktop", desktopPortrait)),
    writeFile(resolve(outputDirectory, assets.mobileDark), createHeroSvg(config, palette.dark, "mobile", mobilePortrait)),
    writeFile(resolve(outputDirectory, assets.mobileLight), createHeroSvg(config, palette.light, "mobile", mobilePortrait))
  ]);
  await cleanOldAssets(outputDirectory, Object.values(assets));

  const manifest = { generator: GENERATOR_VERSION, version, assets };
  await writeFile(resolve(outputDirectory, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  return manifest;
}
