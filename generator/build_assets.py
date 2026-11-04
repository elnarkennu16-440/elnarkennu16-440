#!/usr/bin/env python3
"""
Kennu Elnar - GitHub profile asset generator.

Run locally:   python3 generator/build_assets.py   (needs Python 3 and: pip install fonttools, only for Kaushan titles)
No GitHub Actions needed. Edit PROFILE / PROJECTS / STACK below, run it, then upload the new assets/ folder.

Writes every SVG into ../assets/
Edit the DATA sections (PROJECTS, STACK, texts) then run again.
"""
import base64, datetime, html, json, math, os, re, textwrap, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "..", "assets")
os.makedirs(os.path.join(OUT, "projects"), exist_ok=True)

PORTFOLIO = "elnarkennu.vercel.app"

with open(os.path.join(ROOT, "KE-LOGO.png"), "rb") as f:
    LOGO_B64 = base64.b64encode(f.read()).decode()
LOGO_W, LOGO_H = 212, 235
ICONS = json.load(open(os.path.join(ROOT, "icons.json"), encoding="utf-8"))

# ---------------------------------------------------------------- palette
BG, PANEL, LINE, SOFT = "#0a0a0b", "#111113", "#26262a", "#8e8e96"
SANS = "'Segoe UI',-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif"
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
SERIF = "Georgia,'Times New Roman',serif"
esc = lambda s: html.escape(s, quote=False)

# ---------------------------------------------------------------- Kaushan Script (text -> vector paths)
FONT = None
FONT_PATH = os.environ.get("TITLE_FONT") or os.path.join(ROOT, "fonts", "KaushanScript-Regular.ttf")


def load_font():
    global FONT
    if os.path.exists(FONT_PATH):
        try:
            from fontTools.ttLib import TTFont
            FONT = TTFont(FONT_PATH)
            glyph_path("Kennu Elnar & Test", 20)  # make sure the font really works
            print("font: loaded", os.path.basename(FONT_PATH))
        except Exception as e:  # never break the build because of a font
            FONT = None
            print("font: could not use it, falling back to serif italic:", e)
    else:
        print("font: Kaushan Script not found, using fallback serif italic titles")


def glyph_path(text, size):
    """Return (svg path data at origin, advance width) for text using the loaded font."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    gs, cmap = FONT.getGlyphSet(), FONT.getBestCmap()
    s = size / FONT["head"].unitsPerEm
    x, parts = 0.0, []
    num = lambda v: ("%.1f" % v).rstrip("0").rstrip(".")
    for ch in text:
        name = cmap.get(ord(ch)) or cmap.get(32)
        if name is None:
            continue
        g = gs[name]
        pen = SVGPathPen(gs, ntos=num)
        g.draw(TransformPen(pen, (s, 0, 0, -s, x, 0)))
        cmds = pen.getCommands()
        if cmds:
            parts.append(cmds)
        x += g.width * s
    return " ".join(parts), x


_uid = [0]
USED = set()


def title(text, x, y, size, anchor="start", depth=6, front="#ffffff", max_w=None, step=0.85, fb_size=None):
    """Title text in Kaushan Script (vector paths). Falls back to serif italic if the font is missing."""
    if FONT:
        d, w = glyph_path(text, size)
        if max_w and w > max_w:
            size = size * max_w / w
            d, w = glyph_path(text, size)
        ox = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
        if depth <= 0:
            return f'<path transform="translate({ox:.1f},{y})" d="{d}" fill="{front}"/>'
        _uid[0] += 1
        pid = f"t{_uid[0]}"
        out = [f'<defs><path id="{pid}" d="{d}"/></defs>']
        for i in range(depth, 0, -1):
            t = (depth - i) / max(depth - 1, 1)
            v = int(0x24 + (0x66 - 0x24) * t)
            out.append(f'<use href="#{pid}" x="{ox + i*step:.2f}" y="{y + i*step:.2f}" fill="#%02x%02x%02x"/>' % (v, v, v + 3))
        out.append(f'<use href="#{pid}" x="{ox:.2f}" y="{y}" fill="{front}"/>')
        return "".join(out)
    return extruded(text, x, y, fb_size or round(size * 0.8), "serif", depth=depth, anchor=anchor,
                    extra='font-style="italic" font-weight="700"', front=front)


COMMON_CSS = f"""
.sans{{font-family:{SANS}}} .mono{{font-family:{MONO}}} .serif{{font-family:{SERIF}}}
@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-6px)}}}}
@keyframes bobS{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-8px)}}}}
@keyframes bobM{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-14px)}}}}
@keyframes bobL{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-22px)}}}}
@keyframes shd{{0%,100%{{transform:scale(1);opacity:.5}}50%{{transform:scale(.84);opacity:.28}}}}
.fl{{animation:bob 4.8s ease-in-out infinite}}
.sh{{transform-box:fill-box;transform-origin:center;animation:shd 4.8s ease-in-out infinite}}
.b1{{animation:bobS 6s ease-in-out infinite}} .b2{{animation:bobM 7.5s ease-in-out infinite}} .b3{{animation:bobL 9s ease-in-out infinite}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
"""

TILE_DEFS = """<linearGradient id="gt" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4c4c53"/><stop offset="1" stop-color="#2b2b30"/></linearGradient>"""


def icon_defs():
    out = []
    for k in sorted(USED):
        ic = ICONS[k]
        rule = ' fill-rule="evenodd"' if ic.get("rule") == "evenodd" else ""
        out.append(f'<path id="ic-{k}" d="{ic["d"]}"{rule}/>')
    USED.clear()
    return "".join(out)


def svg(w, h, body, ttl, desc, defs="", css=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{esc(ttl)}">'
        f"<title>{esc(ttl)}</title><desc>{esc(desc)}</desc>"
        f"<style>{COMMON_CSS}{css}</style><defs>{TILE_DEFS}{defs}{icon_defs()}</defs>{body}</svg>"
    )


def save(path, content):
    with open(os.path.join(OUT, path), "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", path, f"{len(content)/1024:.1f} KB")


# ---------------------------------------------------------------- primitives
def extruded(text, x, y, size, cls, depth=7, anchor="start", extra="", front="#ffffff", step=0.85):
    parts = []
    for i in range(depth, 0, -1):
        t = (depth - i) / max(depth - 1, 1)
        v = int(0x24 + (0x66 - 0x24) * t)
        parts.append(
            f'<text x="{x + i*step:.2f}" y="{y + i*step:.2f}" font-size="{size}" class="{cls}" '
            f'text-anchor="{anchor}" fill="#%02x%02x%02x" {extra}>{esc(text)}</text>' % (v, v, v + 3)
        )
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" class="{cls}" text-anchor="{anchor}" fill="{front}" {extra}>{esc(text)}</text>')
    return "".join(parts)


def cube(cx, cy, a, cls="", delay=0.0):
    h = a * 0.866
    top = f"0,{-a:.2f} {h:.2f},{-a/2:.2f} 0,0 {-h:.2f},{-a/2:.2f}"
    left = f"{-h:.2f},{-a/2:.2f} 0,0 0,{a:.2f} {-h:.2f},{a/2:.2f}"
    right = f"0,0 {h:.2f},{-a/2:.2f} {h:.2f},{a/2:.2f} 0,{a:.2f}"
    st = 'stroke="#6a6a72" stroke-width=".7" stroke-linejoin="round"'
    style = f' style="animation-delay:-{delay}s"' if cls else ""
    return (
        f'<g transform="translate({cx},{cy})"><g class="{cls}"{style}>'
        f'<polygon points="{top}" fill="#55555c" {st}/><polygon points="{left}" fill="#2a2a2e" {st}/>'
        f'<polygon points="{right}" fill="#17171a" {st}/></g></g>'
    )


def glyph(g):
    """Artwork on the top face of an isometric tile: a real logo (raised, with depth) or a text fallback."""
    ic = ICONS.get(g)
    if not ic:
        size = 17 if len(g) <= 2 else 12.5 if len(g) == 3 else 10
        return (f'<text y="{size*0.36:.2f}" font-size="{size}" font-weight="800" text-anchor="middle" '
                f'class="sans" fill="#f2f2f4">{esc(g)}</text>')
    USED.add(g)
    vb = ic["vb"]
    s = 19.5 / max(vb[2], vb[3])
    tx, ty = -(vb[0] + vb[2] / 2) * s, -(vb[1] + vb[3] / 2) * s
    out = []
    for i, col in ((4, "#0e0e10"), (3, "#1f1f23"), (2, "#38383e"), (1, "#5c5c63")):
        o = i * 0.6
        out.append(f'<use href="#ic-{g}" transform="translate({tx+o:.2f},{ty+o:.2f}) scale({s:.4f})" fill="{col}"/>')
    out.append(f'<use href="#ic-{g}" transform="translate({tx:.2f},{ty:.2f}) scale({s:.4f})" fill="#f4f4f6"/>')
    return "".join(out)


def tile(cx, cy, g, k=1.0, delay=0.0):
    top, left, right = "0,-15 26,0 0,15 -26,0", "-26,0 0,15 0,25 -26,10", "0,15 26,0 26,10 0,25"
    return (
        f'<g transform="translate({cx},{cy}) scale({k})">'
        f'<ellipse class="sh" cx="0" cy="26" rx="26" ry="6" fill="#000" style="animation-delay:-{delay}s"/>'
        f'<g class="fl" style="animation-delay:-{delay}s">'
        f'<polygon points="{left}" fill="#1d1d20" stroke="#4a4a50" stroke-width=".6" stroke-linejoin="round"/>'
        f'<polygon points="{right}" fill="#131315" stroke="#4a4a50" stroke-width=".6" stroke-linejoin="round"/>'
        f'<polygon points="{top}" fill="url(#gt)" stroke="#5a5a61" stroke-width=".7" stroke-linejoin="round"/>'
        f'<polyline points="-26,0 0,-15 26,0" fill="none" stroke="#7a7a82" stroke-width=".9" stroke-linejoin="round"/>'
        f'<g transform="matrix(.866 .5 -.866 .5 0 0)">{glyph(g)}</g></g></g>'
    )


def pill(text, size=12.5):
    w = len(text) * (size * 0.6) + 30
    return (f'<rect width="{w:.1f}" height="28" rx="14" fill="#141416" stroke="#34343a"/>'
            f'<text x="{w/2:.1f}" y="18.5" font-size="{size}" text-anchor="middle" class="sans" fill="#b4b4bb">{esc(text)}</text>'), w


def wrap(t, n):
    return textwrap.wrap(t, n)


# ---------------------------------------------------------------- HERO
import random


def floating_icons(W, H, zones, seed=11):
    """All stack logos as small extruded 3D shapes (no boxes, no text) scattered at random but never overlapping."""
    keys = []
    for col in STACK:
        for _, items in col:
            for k, _ in items:
                if k not in keys:
                    keys.append(k)
    rnd = random.Random(seed)
    rnd.shuffle(keys)
    sizes = sorted((rnd.uniform(18, 31) for _ in keys), reverse=True)
    placed = []
    for k, S in zip(keys, sizes):
        for attempt in range(8000):
            x, y = rnd.uniform(30, W - 30), rnd.uniform(30, H - 30)
            if any(z[0] - S <= x <= z[2] + S and z[1] - S <= y <= z[3] + S for z in zones):
                continue
            gap = 22 if attempt < 3500 else 10
            if all(math.hypot(x - px, y - py) >= (S + ps) / 2 + gap for _, px, py, ps in placed):
                placed.append((k, x, y, S))
                break
    out = []
    for n, (k, x, y, S) in enumerate(placed):
        ic = ICONS[k]
        USED.add(k)
        vb = ic["vb"]
        s_ = S / max(vb[2], vb[3])
        tx, ty = -(vb[0] + vb[2] / 2) * s_, -(vb[1] + vb[3] / 2) * s_
        depth, step = 6, max(0.55, S * 0.032)
        layers = []
        for i in range(depth, 0, -1):
            v = int(0x28 + (0x80 - 0x28) * (depth - i) / (depth - 1))
            layers.append(f'<use href="#ic-{k}" transform="translate({tx+i*step:.2f},{ty+i*step:.2f}) scale({s_:.4f})" fill="#%02x%02x%02x"/>' % (v, v, v + 4))
        layers.append(f'<use href="#ic-{k}" transform="translate({tx:.2f},{ty:.2f}) scale({s_:.4f})" fill="#f2f2f5"/>')
        cls = "s1" if S < 24 else "s2" if S < 28 else "s3"
        op = 0.5 + 0.5 * (S - 18) / 13
        dur, dly = rnd.uniform(6.5, 11.5), rnd.uniform(0, 11)
        out.append(f'<g transform="translate({x:.1f},{y:.1f})" opacity="{op:.2f}"><g class="ic {cls}" style="animation-duration:{dur:.1f}s;animation-delay:-{dly:.1f}s">{"".join(layers)}</g></g>')
    return "".join(out)


def hero():
    W, H = 900, 356
    lw, lh = 146, 146 * LOGO_H / LOGO_W
    LY = 126
    FLOOR = 236
    tones = {"a": (0.62, 0.62, 0.65), "b": (0.38, 0.38, 0.41), "c": (0.2, 0.2, 0.23)}
    defs = f"""
<clipPath id="rc"><rect width="{W}" height="{H}" rx="22"/></clipPath>
<radialGradient id="bg" cx="50%" cy="38%" r="75%"><stop offset="0" stop-color="#1c1c20"/><stop offset=".6" stop-color="#0e0e10"/><stop offset="1" stop-color="{BG}"/></radialGradient>
<radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#fff" stop-opacity=".13"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<linearGradient id="fg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000"/><stop offset=".25" stop-color="#fff"/><stop offset="1" stop-color="#555"/></linearGradient>
<mask id="fm"><rect x="0" y="{FLOOR}" width="{W}" height="{H-FLOOR}" fill="url(#fg)"/></mask>
<filter id="bl" x="-30%" y="-100%" width="160%" height="300%"><feGaussianBlur stdDeviation="6"/></filter>
""" + "".join(
        f'<filter id="t{k}" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" '
        f'values="0 0 0 0 {r}  0 0 0 0 {g}  0 0 0 0 {b}  0 0 0 1 0"/></filter>' for k, (r, g, b) in tones.items()
    ) + f'<image id="logo" width="{lw}" height="{lh:.2f}" href="data:image/png;base64,{LOGO_B64}"/>'

    css = """
@keyframes drop{
0%{transform:translateY(-260px);opacity:0;animation-timing-function:cubic-bezier(.55,0,1,.45)}
.5%{opacity:1}
6.25%{transform:translateY(0);animation-timing-function:cubic-bezier(0,.55,.45,1)}
9.4%{transform:translateY(-62px);animation-timing-function:cubic-bezier(.55,0,1,.45)}
12.5%{transform:translateY(0);animation-timing-function:cubic-bezier(0,.55,.45,1)}
14.4%{transform:translateY(-22px);animation-timing-function:cubic-bezier(.55,0,1,.45)}
16.25%{transform:translateY(0);animation-timing-function:cubic-bezier(0,.55,.45,1)}
17.5%{transform:translateY(-7px);animation-timing-function:cubic-bezier(.55,0,1,.45)}
18.75%{transform:translateY(0);opacity:1;animation-timing-function:linear}
93.75%{transform:translateY(0);opacity:1;animation-timing-function:ease-out}
96.9%{transform:translateY(-40px);opacity:0}
100%{transform:translateY(-260px);opacity:0}}
@keyframes land{
0%{transform:scale(.2);opacity:0}6.25%{transform:scale(1);opacity:.75}9.4%{transform:scale(.62);opacity:.4}
12.5%{transform:scale(1);opacity:.75}14.4%{transform:scale(.86);opacity:.55}16.25%{transform:scale(1);opacity:.75}
17.5%{transform:scale(.95);opacity:.65}18.75%{transform:scale(1);opacity:.75}93.75%{transform:scale(1);opacity:.75}
96.9%{transform:scale(.5);opacity:.2}100%{transform:scale(.2);opacity:0}}
@keyframes flt{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
@keyframes sw1{0%,100%{transform:translateY(0) rotate(-3deg)}50%{transform:translateY(-8px) rotate(3deg)}}
@keyframes sw2{0%,100%{transform:translateY(0) rotate(4deg)}50%{transform:translateY(-12px) rotate(-4deg)}}
@keyframes sw3{0%,100%{transform:translate(0,0) rotate(-5deg)}50%{transform:translate(5px,-16px) rotate(5deg)}}
.ic{transform-box:fill-box;transform-origin:center}
.s1{animation:sw1 8s ease-in-out infinite}.s2{animation:sw2 9s ease-in-out infinite}.s3{animation:sw3 10s ease-in-out infinite}
.drop{animation:drop 16s infinite both}
.flt{animation:flt 5s ease-in-out infinite}
.land{transform-box:fill-box;transform-origin:center;animation:land 16s infinite both}
@media (prefers-reduced-motion:reduce){.land{opacity:.75}}
"""
    b = [f'<g clip-path="url(#rc)"><rect width="{W}" height="{H}" fill="url(#bg)"/>']
    g = ['<g mask="url(#fm)" stroke="#34343a" stroke-width="1" fill="none">']
    for k in range(0, 9):
        y = FLOOR + 4 + (k / 8) ** 2 * (H - FLOOR - 4)
        g.append(f'<line x1="0" y1="{y:.1f}" x2="{W}" y2="{y:.1f}"/>')
    for i in range(-16, 17):
        g.append(f'<line x1="{450+i*16}" y1="{FLOOR}" x2="{450+i*92}" y2="{H}"/>')
    g.append("</g>")
    b.append("".join(g))
    zones = [(345, 0, 555, 212), (190, 240, 710, 344)]
    b.append(floating_icons(W, H, zones))
    b.append(f'<ellipse cx="450" cy="{LY}" rx="220" ry="150" fill="url(#glow)"/>')
    b.append(f'<g transform="translate(453,{LY+94})"><ellipse class="land" rx="74" ry="8" fill="#000" filter="url(#bl)"/></g>')
    layers = []
    for i in range(10, 0, -1):
        tone = "c" if i >= 7 else "b" if i >= 4 else "a"
        layers.append(f'<use href="#logo" x="{-lw/2 + i*1.05:.2f}" y="{-lh/2 + i*1.05:.2f}" filter="url(#t{tone})"/>')
    layers.append(f'<use href="#logo" x="{-lw/2:.2f}" y="{-lh/2:.2f}"/>')
    b.append(f'<g transform="translate(450,{LY})"><g class="drop"><g class="flt">{"".join(layers)}</g></g></g>')

    lw2 = len(PORTFOLIO) * 11.2 + 78
    b.append(f'<g transform="translate({450-lw2/2:.1f},250)"><rect width="{lw2:.1f}" height="36" rx="18" fill="#141416" stroke="#4a4a52"/>'
             f'<text x="28" y="23.5" font-size="16" letter-spacing="1.4" class="mono" fill="#e6e6ea">{esc(PORTFOLIO)}</text>'
             f'<path d="M{lw2-40:.1f} 18 h13 M{lw2-33:.1f} 12.5 l6.5 5.5 l-6.5 5.5" fill="none" stroke="#e6e6ea" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></g>')
    pills = [pill(t) for t in ["Web Development", "Quality & Testing", "Practical Tooling"]]
    x = 450 - (sum(p[1] for p in pills) + 14 * (len(pills) - 1)) / 2
    for markup, w in pills:
        b.append(f'<g transform="translate({x:.1f},304)">{markup}</g>')
        x += w + 14
    b.append(f'</g><rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="22" fill="none" stroke="{LINE}"/>')
    return svg(W, H, "".join(b), "Kennu Elnar - Frontend Developer and QA Tester",
               f"Animated hero: the KE logo drops with gravity while small 3D tech logos float around. Portfolio: {PORTFOLIO}", defs, css)


# ---------------------------------------------------------------- section headers (slim)
def header(fname, text, sub):
    W, H = 900, 52
    body = (f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="13" fill="{BG}" stroke="{LINE}"/>'
            + cube(38, 25, 10) + title(text, 62, 37, 30, depth=5, max_w=520, fb_size=24)
            + f'<text x="{W-24}" y="30" text-anchor="end" font-size="11.5" class="mono" fill="{SOFT}">{esc(sub)}</text>')
    save(fname, svg(W, H, body, text, f"Section heading: {text}"))


# ---------------------------------------------------------------- ABOUT (compact)
def about():
    W, H = 900, 246
    p1 = ("I'm Kennu, an Information Systems graduate and builder based in the Philippines. I focus on "
          "developing clean web interfaces, exploring practical backend logic, and testing software "
          "workflows to ensure applications run reliably.")
    p2 = ("Whether I'm building personal projects or running functional tests to catch edge cases, I value "
          "simple structure, consistent practice, and steady iteration.")
    b = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="16" fill="{PANEL}" stroke="{LINE}"/>']
    y = 46
    for para in (p1, p2):
        for ln in wrap(para, 62):
            b.append(f'<text x="34" y="{y}" font-size="15" class="sans" fill="#cdcdd3">{esc(ln)}</text>')
            y += 23
        y += 12
    px, py, pw, ph = 560, 20, 312, H - 40
    b.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="12" fill="{BG}" stroke="#2f2f35"/>')
    rows = [("Role", "Frontend Dev & QA Tester"), ("Education", "Information Systems graduate"),
            ("Location", "Philippines"), ("Focus", "Web, testing, tooling"), ("Portfolio", PORTFOLIO)]
    ry = py + 30
    for i, (k, v) in enumerate(rows):
        b.append(f'<text x="{px+22}" y="{ry}" font-size="10.5" class="mono" fill="{SOFT}">{esc(k)}</text>')
        b.append(f'<text x="{px+22}" y="{ry+17}" font-size="14.5" class="sans" font-weight="600" fill="#f1f1f3">{esc(v)}</text>')
        if i < len(rows) - 1:
            b.append(f'<line x1="{px+22}" y1="{ry+28}" x2="{px+pw-22}" y2="{ry+28}" stroke="{LINE}"/>')
        ry += 37
    b.append(cube(px + pw - 32, py + 30, 9, "b1", 2))
    save("about.svg", svg(W, H, "".join(b), "About Kennu Elnar", "Short bio and quick facts about Kennu Elnar."))


# ---------------------------------------------------------------- FOCUS (compact)
def focus():
    W, H = 900, 128
    items = [("Web Development", "mdi-code-tags", "Building responsive interfaces and straightforward server-side systems."),
             ("Quality & Testing", "mdi-bug-check", "Exploring manual testing, test scenarios, and automated checks to improve application stability."),
             ("Practical Tooling", "mdi-source-branch", "Improving day-to-day Git workflows, database modeling, and structured development setups.")]
    cw, gap = 288, 18
    b = []
    for i, (t, g, d) in enumerate(items):
        x = i * (cw + gap)
        b.append(f'<g transform="translate({x},0)"><rect x=".5" y=".5" width="{cw-1}" height="{H-1}" rx="16" fill="{PANEL}" stroke="{LINE}"/>')
        b.append(tile(44, 46, g, 0.85, delay=i * 1.1))
        b.append(title(t, 88, 36, 24, depth=0, front="#f4f4f6", max_w=cw - 106, fb_size=18))
        for j, ln in enumerate(wrap(d, 33)):
            b.append(f'<text x="88" y="{58+j*16}" font-size="12.3" class="sans" fill="#a0a0a8">{esc(ln)}</text>')
        b.append("</g>")
    save("focus.svg", svg(W, H, "".join(b), "Current focus", "Web development, quality and testing, practical tooling."))


# ---------------------------------------------------------------- PROJECTS (two per row)
PROJECTS = [
    ("mirams", "MIRAMS Enterprise System", "mdi-factory",
     "Manufacturing request and asset management system with RBAC, approval workflows and live analytics.",
     ["TypeScript", "React", "Laravel", "RBAC"], 4),
    ("ncamis", "NCAMIS-SHS", "mdi-school",
     "Management information system that streamlines Senior High School academic and admin processes.",
     ["JavaScript", "Web Platform", "Records"], 4),
    ("nobleclassics", "NobleClassics", "mdi-book-open-page-variant",
     "Full e-commerce bookstore on a custom PHP backend, from cart to checkout, with an admin dashboard.",
     ["PHP", "E-Commerce", "Admin Dashboard"], 2),
    ("bento", "Bento Grid Portfolio", "mdi-view-dashboard",
     "Portfolio template with a Bento Grid layout, 3D tilt interactions and glassmorphism.",
     ["React", "Tailwind CSS", "Framer Motion"], 2),
    ("particles", "3D Particle Simulation", "mdi-atom",
     "Gesture-controlled 3D particle simulation that morphs particles between 3D models in real time.",
     ["Python", "Computer Vision", "3D"], 1),
    ("visiontrack", "3D Vision Track", "mdi-hand-wave",
     "Real-time hand tracking that spans an interactive 2D or 3D shape between both hands.",
     ["Python", "OpenCV", "MediaPipe"], 2),
]


def projects():
    W, H = 450, 160
    for n, (key, ttl, g, desc, tags, stars) in enumerate(PROJECTS):
        b = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="16" fill="{PANEL}" stroke="{LINE}"/>',
             tile(52, 44, g, 0.95, delay=n * 0.9),
             title(ttl, 96, 50, 26, depth=0, front="#f4f4f6", max_w=262, fb_size=20)]
        USED.add("mdi-star")
        sw = len(str(stars)) * 8.6
        b.append(f'<use href="#ic-mdi-star" transform="translate({W-24-sw-22:.1f},31) scale(.75)" fill="#d8d8de"/>'
                 f'<text x="{W-24}" y="46" font-size="15" font-weight="700" text-anchor="end" class="sans" fill="#e6e6ea">{stars}</text>')
        lines = wrap(desc, 56)
        assert len(lines) <= 2, (key, lines)
        for j, ln in enumerate(lines):
            b.append(f'<text x="24" y="{96+j*18}" font-size="13" class="sans" fill="#a0a0a8">{esc(ln)}</text>')
        x = 24
        for t in tags:
            w = len(t) * 6.4 + 20
            b.append(f'<g transform="translate({x:.1f},126)"><rect width="{w:.1f}" height="22" rx="11" fill="#151517" stroke="#34343a"/>'
                     f'<text x="{w/2:.1f}" y="15" font-size="10.5" text-anchor="middle" class="mono" fill="#b4b4bb">{esc(t)}</text></g>')
            x += w + 8
        save(f"projects/{key}.svg", svg(W, H, "".join(b), ttl, desc))


# ---------------------------------------------------------------- CAPABILITIES (compact, real logos)
STACK = [
    [("Frontend", [("react", "React"), ("vuedotjs", "Vue.js"), ("tailwindcss", "Tailwind\nCSS"), ("nextdotjs", "Next.js"), ("typescript", "TypeScript"), ("javascript", "JavaScript")]),
     ("Backend", [("nodedotjs", "Node.js"), ("express", "Express.js"), ("php", "PHP"), ("laravel", "Laravel"), ("python", "Python")])],
    [("Databases", [("mysql", "MySQL"), ("supabase", "Supabase"), ("firebase", "Firebase"), ("mongodb", "MongoDB")]),
     ("Testing Tools", [("asana", "Asana"), ("jira", "Jira"), ("googlechrome", "Chrome\nDevTools"), ("postman", "Postman")]),
     ("AI & Machine Learning", [("googlegemini", "Gemini"), ("claude", "Claude"), ("manus", "Manus"), ("perplexity", "Perplexity")]),
     ("Authentication & Security", [("jsonwebtokens", "JWT"), ("gitguardian", "GitGuardian"), ("dependabot", "Dependabot"), ("zap", "OWASP\nZAP")])],
    [("Platforms & Dev Tools", [("github", "Git / GitHub"), ("vercel", "Vercel"), ("notion", "Notion"), ("vscode", "VS Code"), ("vite", "Vite"), ("npm", "npm"), ("cline", "Cline"), ("antigravity", "Antigravity")]),
     ("Cloud & Hosting", [("vercel", "Vercel"), ("hostinger", "Hostinger"), ("cloudflare", "Cloudflare")]),
     ("Mobile", [("flutter", "Flutter"), ("react", "React\nNative")])],
]


def capabilities():
    W, PAD, TOP, CW, GAP, ROW, PER, PITCH, K = 900, 27, 24, 262, 30, 74, 5, 52, 0.92
    cols = [[STACK[0][0], STACK[0][1], STACK[1][0]],      # Frontend, Backend, Databases
            [STACK[1][1], STACK[1][2], STACK[1][3]],      # Testing, AI, Security
            [STACK[2][0], STACK[2][1], STACK[2][2]]]      # Platforms, Cloud, Mobile
    b, ends, idx = [], [], 0
    for ci, col in enumerate(cols):
        x0, y = PAD + ci * (CW + GAP), TOP
        for ttl, items in col:
            b.append(title(ttl, x0, y + 22, 25, depth=3, step=0.7, max_w=CW, fb_size=18))
            b.append(f'<line x1="{x0}" y1="{y+31}" x2="{x0+CW}" y2="{y+31}" stroke="{LINE}"/>')
            rows = math.ceil(len(items) / PER)
            for k, (g, label) in enumerate(items):
                r, c = divmod(k, PER)
                cx, cy = x0 + 27 + c * PITCH, y + 31 + 27 + r * ROW
                b.append(tile(cx, cy, g, K, delay=(idx * 0.37) % 4.8))
                for li, ln in enumerate(label.split("\n")):
                    fs = 9.8 if len(ln) <= 8 else 9.0 if len(ln) <= 9 else 8.4
                    b.append(f'<text x="{cx}" y="{cy+38+li*11.5}" font-size="{fs}" text-anchor="middle" class="sans" fill="#9c9ca4">{esc(ln)}</text>')
                idx += 1
            y += 31 + 27 + (rows - 1) * ROW + 52 + 12
        ends.append(y)
    H = max(ends) + 6
    body = f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="16" fill="{BG}" stroke="{LINE}"/>' + "".join(b)
    save("capabilities.svg", svg(W, H, body, "Tech stack and capabilities",
         "3D isometric tiles with the logos of the languages, frameworks, databases, tools and platforms Kennu uses."))


# ---------------------------------------------------------------- SNAPSHOT (stats + languages in one compact card)
PROFILE = {
    "snapshot": "Nov 3, 2026",
    "repos": 12,         # public repositories
    "followers": 9,
    "stars": 15,         # stars on the six featured repositories (4+4+2+2+1+2)
    "featured": 6,
    "langs": [("JavaScript", 2), ("Python", 2), ("TypeScript", 1), ("PHP", 1)],   # main language of each featured project
}


def stats_card(p=PROFILE):
    W, H = 900, 200
    cells = [("mdi-source-repository", p["repos"], "Public repositories"), ("mdi-account-group", p["followers"], "Followers"),
             ("mdi-star", p["stars"], "Stars on featured work"), ("mdi-view-dashboard", p["featured"], "Featured projects")]
    b = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="16" fill="{PANEL}" stroke="{LINE}"/>']
    cw = 205
    for i, (g, val, lab) in enumerate(cells):
        x0 = 40 + i * cw
        if i:
            b.append(f'<line x1="{x0-6}" y1="22" x2="{x0-6}" y2="82" stroke="{LINE}"/>')
        b.append(tile(x0 + 28, 46, g, 0.8, delay=i * 1.2))
        b.append(f'<text x="{x0+68}" y="52" font-size="31" font-weight="700" class="sans" fill="#f4f4f6">{val}</text>')
        b.append(f'<text x="{x0+68}" y="72" font-size="12" class="sans" fill="#a0a0a8">{esc(lab)}</text>')
    b.append(f'<line x1="40" y1="100" x2="{W-40}" y2="100" stroke="{LINE}"/>')
    b.append(f'<text x="40" y="128" font-size="14" font-weight="700" class="sans" fill="#f4f4f6">Languages in my featured work</text>')
    b.append(f'<text x="{W-40}" y="128" font-size="10.5" text-anchor="end" class="mono" fill="#5c5c64">snapshot, {esc(p["snapshot"])}</text>')
    shades = ["#f4f4f6", "#b4b4bb", "#84848c", "#55555d", "#3a3a40"]
    tot = sum(n for _, n in p["langs"])
    b.append(f'<clipPath id="bar"><rect x="40" y="140" width="{W-80}" height="12" rx="6"/></clipPath><g clip-path="url(#bar)">')
    x = 40.0
    for i, (nm, n) in enumerate(p["langs"]):
        w = (W - 80) * n / tot
        b.append(f'<rect x="{x:.2f}" y="140" width="{w+0.5:.2f}" height="12" fill="{shades[i]}"/>')
        x += w
    b.append("</g>")
    for i, (nm, n) in enumerate(p["langs"]):
        lx = 40 + i * 205
        b.append(f'<circle cx="{lx+5}" cy="173" r="5" fill="{shades[i]}"/>')
        b.append(f'<text x="{lx+16}" y="177" font-size="12.5" class="sans" fill="#d0d0d6">{esc(nm)}</text>'
                 f'<text x="{lx+16+len(nm)*6.6+10:.0f}" y="177" font-size="11" class="mono" fill="{SOFT}">{n}</text>')
    save("stats.svg", svg(W, H, "".join(b), "GitHub snapshot",
         f"{p['repos']} public repositories, {p['followers']} followers, {p['stars']} stars on featured work, {p['featured']} featured projects. Main languages: "
         + ", ".join(f"{a} {n}" for a, n in p["langs"]) + "."))


# ---------------------------------------------------------------- FOOTER (compact)
def footer():
    W, H = 900, 112
    lw, lh = 54, 54 * LOGO_H / LOGO_W
    defs = (f'<clipPath id="rc"><rect width="{W}" height="{H}" rx="18"/></clipPath>'
            f'<filter id="tb" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="0 0 0 0 .3  0 0 0 0 .3  0 0 0 0 .33  0 0 0 1 0"/></filter>'
            f'<image id="logo" width="{lw}" height="{lh:.2f}" href="data:image/png;base64,{LOGO_B64}"/>')
    css = "@keyframes flt{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}.flt{animation:flt 4.5s ease-in-out infinite}"
    b = [f'<g clip-path="url(#rc)"><rect width="{W}" height="{H}" fill="{BG}"/>']
    for cx, cy, a, cls, d in [(790, 34, 13, "b2", 1), (850, 78, 9, "b3", 3), (736, 82, 8, "b1", 5)]:
        b.append(cube(cx, cy, a, cls, d))
    lay = "".join(f'<use href="#logo" x="{-lw/2+i*.7:.2f}" y="{-lh/2+i*.7:.2f}" filter="url(#tb)"/>' for i in range(5, 0, -1))
    lay += f'<use href="#logo" x="{-lw/2}" y="{-lh/2:.2f}"/>'
    b.append(f'<g transform="translate(80,{H/2})"><g class="flt">{lay}</g></g>')
    for i, t in enumerate(["Building practical tools, learning through iteration,", "and testing for reliability."]):
        b.append(title(t, 140, 50 + i * 26, 21, depth=0, front="#d0d0d6", max_w=560, fb_size=17))
    b.append(f'</g><rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="18" fill="none" stroke="{LINE}"/>')
    save("footer.svg", svg(W, H, "".join(b), "Kennu Elnar footer", "Closing note with the KE logo.", defs, css))


# ---------------------------------------------------------------- run
if __name__ == "__main__":
    load_font()
    save("hero.svg", hero())
    header("h-about.svg", "About Me", "who I am")
    header("h-focus.svg", "Current Focus", "what I'm exploring")
    header("h-projects.svg", "Featured Work", "things I've built")
    header("h-stack.svg", "Tech Stack", "tools I build with")
    header("h-stats.svg", "GitHub Snapshot", "profile at a glance")
    about()
    focus()
    projects()
    capabilities()
    stats_card()
    footer()
