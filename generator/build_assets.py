#!/usr/bin/env python3
"""
Kennu Elnar - GitHub profile asset generator.

Run locally:   python3 generator/build_assets.py
On GitHub:     runs automatically inside the "Build profile assets" workflow.

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
def hero():
    W, H = 900, 548
    lw, lh = 156, 156 * LOGO_H / LOGO_W
    tones = {"a": (0.62, 0.62, 0.65), "b": (0.38, 0.38, 0.41), "c": (0.2, 0.2, 0.23)}
    defs = f"""
<clipPath id="rc"><rect width="{W}" height="{H}" rx="22"/></clipPath>
<radialGradient id="bg" cx="50%" cy="38%" r="75%"><stop offset="0" stop-color="#1c1c20"/><stop offset=".6" stop-color="#0e0e10"/><stop offset="1" stop-color="{BG}"/></radialGradient>
<radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#fff" stop-opacity=".13"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<linearGradient id="fg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000"/><stop offset=".25" stop-color="#fff"/><stop offset="1" stop-color="#555"/></linearGradient>
<mask id="fm"><rect x="0" y="340" width="{W}" height="{H-340}" fill="url(#fg)"/></mask>
<filter id="bl" x="-30%" y="-100%" width="160%" height="300%"><feGaussianBlur stdDeviation="6"/></filter>
""" + "".join(
        f'<filter id="t{k}" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" '
        f'values="0 0 0 0 {r}  0 0 0 0 {g}  0 0 0 0 {b}  0 0 0 1 0"/></filter>' for k, (r, g, b) in tones.items()
    ) + f'<image id="logo" width="{lw}" height="{lh:.2f}" href="data:image/png;base64,{LOGO_B64}"/>'

    css = """
@keyframes drop{
0%{transform:translateY(-360px);opacity:0;animation-timing-function:cubic-bezier(.55,0,1,.45)}
.5%{opacity:1}
6.25%{transform:translateY(0);animation-timing-function:cubic-bezier(0,.55,.45,1)}
9.4%{transform:translateY(-72px);animation-timing-function:cubic-bezier(.55,0,1,.45)}
12.5%{transform:translateY(0);animation-timing-function:cubic-bezier(0,.55,.45,1)}
14.4%{transform:translateY(-26px);animation-timing-function:cubic-bezier(.55,0,1,.45)}
16.25%{transform:translateY(0);animation-timing-function:cubic-bezier(0,.55,.45,1)}
17.5%{transform:translateY(-8px);animation-timing-function:cubic-bezier(.55,0,1,.45)}
18.75%{transform:translateY(0);opacity:1;animation-timing-function:linear}
93.75%{transform:translateY(0);opacity:1;animation-timing-function:ease-out}
96.9%{transform:translateY(-50px);opacity:0}
100%{transform:translateY(-360px);opacity:0}}
@keyframes land{
0%{transform:scale(.2);opacity:0}6.25%{transform:scale(1);opacity:.75}9.4%{transform:scale(.62);opacity:.4}
12.5%{transform:scale(1);opacity:.75}14.4%{transform:scale(.86);opacity:.55}16.25%{transform:scale(1);opacity:.75}
17.5%{transform:scale(.95);opacity:.65}18.75%{transform:scale(1);opacity:.75}93.75%{transform:scale(1);opacity:.75}
96.9%{transform:scale(.5);opacity:.2}100%{transform:scale(.2);opacity:0}}
@keyframes flt{0%,100%{transform:translateY(0)}50%{transform:translateY(-9px)}}
.drop{animation:drop 16s infinite both}
.flt{animation:flt 5s ease-in-out infinite}
.land{transform-box:fill-box;transform-origin:center;animation:land 16s infinite both}
@media (prefers-reduced-motion:reduce){.land{opacity:.75}}
"""
    b = [f'<g clip-path="url(#rc)"><rect width="{W}" height="{H}" fill="url(#bg)"/>']
    g = ['<g mask="url(#fm)" stroke="#34343a" stroke-width="1" fill="none">']
    for k in range(0, 9):
        y = 345 + (k / 8) ** 2 * 205
        g.append(f'<line x1="0" y1="{y:.1f}" x2="{W}" y2="{y:.1f}"/>')
    for i in range(-16, 17):
        g.append(f'<line x1="{450+i*16}" y1="345" x2="{450+i*92}" y2="{H}"/>')
    g.append("</g>")
    b.append("".join(g))
    for cx, cy, a, cls, d in [(108, 130, 28, "b2", 1), (798, 104, 22, "b3", 4), (190, 330, 15, "b1", 2), (742, 300, 32, "b2", 6),
                              (655, 78, 11, "b1", 3), (268, 64, 13, "b3", 5), (842, 430, 17, "b1", 7), (62, 450, 21, "b3", 2),
                              (560, 332, 9, "b2", 1), (352, 306, 8, "b1", 4)]:
        b.append(cube(cx, cy, a, cls, d))
    b.append('<ellipse cx="450" cy="200" rx="230" ry="190" fill="url(#glow)"/>')
    b.append('<g transform="translate(454,320)"><ellipse class="land" rx="80" ry="9" fill="#000" filter="url(#bl)"/></g>')
    layers = []
    for i in range(10, 0, -1):
        tone = "c" if i >= 7 else "b" if i >= 4 else "a"
        layers.append(f'<use href="#logo" x="{-lw/2 + i*1.15:.2f}" y="{-lh/2 + i*1.15:.2f}" filter="url(#t{tone})"/>')
    layers.append(f'<use href="#logo" x="{-lw/2:.2f}" y="{-lh/2:.2f}"/>')
    b.append(f'<g transform="translate(450,200)"><g class="drop"><g class="flt">{"".join(layers)}</g></g></g>')

    # name
    if FONT:
        b.append(title("Kennu Elnar", 450, 398, 78, "middle", depth=8, max_w=560))
    else:
        b.append(extruded("KENNU ELNAR", 456, 398, 46, "sans", depth=8, anchor="middle", extra='font-weight="800" letter-spacing="11"'))

    # portfolio link (the whole hero image is wrapped in a link in the README)
    lw2 = len(PORTFOLIO) * 11.2 + 78
    b.append(f'<g transform="translate({450-lw2/2:.1f},418)"><rect width="{lw2:.1f}" height="36" rx="18" fill="#141416" stroke="#4a4a52"/>'
             f'<text x="28" y="23.5" font-size="16" letter-spacing="1.4" class="mono" fill="#e6e6ea">{esc(PORTFOLIO)}</text>'
             f'<path d="M{lw2-40:.1f} 18 h13 M{lw2-33:.1f} 12.5 l6.5 5.5 l-6.5 5.5" fill="none" stroke="#e6e6ea" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></g>')
    pills = [pill(t) for t in ["Web Development", "Quality & Testing", "Practical Tooling"]]
    x = 450 - (sum(p[1] for p in pills) + 14 * (len(pills) - 1)) / 2
    for markup, w in pills:
        b.append(f'<g transform="translate({x:.1f},478)">{markup}</g>')
        x += w + 14
    b.append(f'</g><rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="22" fill="none" stroke="{LINE}"/>')
    return svg(W, H, "".join(b), "Kennu Elnar - Frontend Developer and QA Tester",
               f"Animated hero: the KE logo drops with gravity above the name Kennu Elnar. Portfolio: {PORTFOLIO}", defs, css)


# ---------------------------------------------------------------- section headers
def header(fname, text, sub):
    W, H = 900, 70
    body = (f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="{BG}" stroke="{LINE}"/>'
            + cube(44, 34, 12) + title(text, 76, 48, 36, depth=6, max_w=560, fb_size=29)
            + f'<text x="{W-26}" y="40" text-anchor="end" font-size="12" class="mono" fill="{SOFT}">{esc(sub)}</text>')
    save(fname, svg(W, H, body, text, f"Section heading: {text}"))


# ---------------------------------------------------------------- ABOUT
def about():
    W, H = 900, 334
    p1 = ("I'm Kennu, an Information Systems graduate and builder based in the Philippines. I focus on "
          "developing clean web interfaces, exploring practical backend logic, and testing software "
          "workflows to ensure applications run reliably.")
    p2 = ("Whether I'm building personal projects or running functional tests to catch edge cases, I value "
          "simple structure, consistent practice, and steady iteration.")
    b = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="18" fill="{PANEL}" stroke="{LINE}"/>']
    y = 58
    for para in (p1, p2):
        for ln in wrap(para, 52):
            b.append(f'<text x="40" y="{y}" font-size="15.5" class="sans" fill="#cdcdd3">{esc(ln)}</text>')
            y += 26
        y += 16
    px, py, pw, ph = 556, 30, 316, H - 60
    b.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="14" fill="{BG}" stroke="#2f2f35"/>')
    rows = [("Role", "Frontend Dev & QA Tester"), ("Education", "Information Systems graduate"),
            ("Location", "Philippines"), ("Focus", "Web, testing, tooling"), ("Portfolio", PORTFOLIO)]
    ry = py + 42
    for i, (k, v) in enumerate(rows):
        b.append(f'<text x="{px+24}" y="{ry}" font-size="11.5" class="mono" fill="{SOFT}">{esc(k)}</text>')
        b.append(f'<text x="{px+24}" y="{ry+21}" font-size="15" class="sans" font-weight="600" fill="#f1f1f3">{esc(v)}</text>')
        if i < len(rows) - 1:
            b.append(f'<line x1="{px+24}" y1="{ry+36}" x2="{px+pw-24}" y2="{ry+36}" stroke="{LINE}"/>')
        ry += 50
    b.append(cube(px + pw - 38, py + 38, 11, "b1", 2))
    save("about.svg", svg(W, H, "".join(b), "About Kennu Elnar", "Short bio and quick facts about Kennu Elnar."))


# ---------------------------------------------------------------- FOCUS
def focus():
    W, H = 900, 250
    items = [("Web Development", "mdi-code-tags", "Building responsive interfaces and straightforward server-side systems."),
             ("Quality & Testing", "mdi-bug-check", "Exploring manual testing, test scenarios, and automated checks to improve application stability."),
             ("Practical Tooling", "mdi-source-branch", "Improving day-to-day Git workflows, database modeling, and structured development setups.")]
    cw, gap = 276, 36
    b = []
    for i, (t, g, d) in enumerate(items):
        x = i * (cw + gap)
        b.append(f'<g transform="translate({x},0)"><rect x=".5" y=".5" width="{cw-1}" height="{H-1}" rx="18" fill="{PANEL}" stroke="{LINE}"/>')
        b.append(tile(62, 66, g, 1.35, delay=i * 1.1))
        b.append(title(t, 26, 142, 28, depth=0, front="#f4f4f6", max_w=cw - 52, fb_size=21))
        for j, ln in enumerate(wrap(d, 34)):
            b.append(f'<text x="26" y="{170+j*20}" font-size="13.5" class="sans" fill="#a0a0a8">{esc(ln)}</text>')
        b.append("</g>")
    save("focus.svg", svg(W, H, "".join(b), "Current focus", "Web development, quality and testing, practical tooling."))


# ---------------------------------------------------------------- PROJECTS
PROJECTS = [
    ("mirams", "MIRAMS Enterprise System", "mdi-factory",
     "Manufacturing Internal Request & Asset Management System with Spatie RBAC, multi-user approval workflows and live analytics.",
     ["TypeScript", "React", "Laravel", "RBAC"]),
    ("ncamis", "NCAMIS-SHS", "mdi-school",
     "Northills College of Asia Management Information System: a web platform that streamlines Senior High School academic and admin processes.",
     ["JavaScript", "Web Platform", "Academic Records"]),
    ("nobleclassics", "NobleClassics", "mdi-book-open-page-variant",
     "Full-featured e-commerce bookstore on a custom PHP backend, from cart to checkout, with a dedicated admin dashboard.",
     ["PHP", "E-Commerce", "Admin Dashboard"]),
    ("bento", "Bento Grid Portfolio", "mdi-view-dashboard",
     "Immersive portfolio template with a Bento Grid layout, 3D tilt interactions and glassmorphism, animated with Framer Motion.",
     ["React", "Tailwind CSS", "Framer Motion"]),
    ("particles", "3D Particle Simulation", "mdi-atom",
     "Gesture-controlled 3D particle physics simulation that morphs thousands of glowing particles between 3D models in real time.",
     ["Python", "Computer Vision", "3D"]),
    ("visiontrack", "3D Vision Track", "mdi-hand-wave",
     "Real-time computer vision app that tracks both hands to span an interactive 2D quadrilateral or a 3D six-sided box between them.",
     ["Python", "OpenCV", "MediaPipe"]),
]


def projects():
    W, H = 900, 150
    for n, (key, ttl, g, desc, tags) in enumerate(PROJECTS):
        b = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="18" fill="{PANEL}" stroke="{LINE}"/>',
             f'<line x1="162" y1="22" x2="162" y2="{H-22}" stroke="{LINE}"/>', tile(81, 66, g, 1.45, delay=n * 0.9),
             title(ttl, 192, 46, 30, depth=0, front="#f4f4f6", max_w=640, fb_size=23)]
        lines = wrap(desc, 84)
        assert len(lines) <= 2, (key, lines)
        for j, ln in enumerate(lines):
            b.append(f'<text x="192" y="{72+j*20}" font-size="13.5" class="sans" fill="#a0a0a8">{esc(ln)}</text>')
        x = 192
        for t in tags:
            w = len(t) * 6.9 + 22
            b.append(f'<g transform="translate({x},106)"><rect width="{w:.1f}" height="24" rx="12" fill="#151517" stroke="#34343a"/>'
                     f'<text x="{w/2:.1f}" y="16" font-size="11.5" text-anchor="middle" class="mono" fill="#b4b4bb">{esc(t)}</text></g>')
            x += w + 10
        b.append('<text x="838" y="124" font-size="12.5" text-anchor="end" class="sans" fill="#d0d0d6">View repository</text>')
        b.append('<path d="M848 124 h14 M857 118 l6 6 l-6 6" fill="none" stroke="#d0d0d6" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')
        save(f"projects/{key}.svg", svg(W, H, "".join(b), ttl, desc))


# ---------------------------------------------------------------- CAPABILITIES (real brand logos)
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
    W, PAD, TOP, CW, GAP, ROW = 900, 36, 34, 256, 30, 96
    b, ends, idx = [], [], 0
    for ci, col in enumerate(STACK):
        x0, y = PAD + ci * (CW + GAP), TOP
        for ttl, items in col:
            b.append(title(ttl, x0, y + 20, 27, depth=3, step=0.7, max_w=CW, fb_size=19))
            b.append(f'<line x1="{x0}" y1="{y+30}" x2="{x0+CW}" y2="{y+30}" stroke="{LINE}"/>')
            rows = math.ceil(len(items) / 4)
            for k, (g, label) in enumerate(items):
                r, c = divmod(k, 4)
                cx, cy = x0 + 32 + c * 64, y + 30 + 34 + r * ROW
                b.append(tile(cx, cy, g, 1.0, delay=(idx * 0.37) % 4.8))
                for li, ln in enumerate(label.split("\n")):
                    b.append(f'<text x="{cx}" y="{cy+42+li*12.5}" font-size="10.5" text-anchor="middle" class="sans" fill="#9c9ca4">{esc(ln)}</text>')
                idx += 1
            y += 30 + 34 + (rows - 1) * ROW + 58 + 22
        ends.append(y)
    H = max(ends) + 8
    body = f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="18" fill="{BG}" stroke="{LINE}"/>' + "".join(b)
    save("capabilities.svg", svg(W, H, body, "Tech stack and capabilities",
         "3D isometric tiles with the logos of the languages, frameworks, databases, tools and platforms Kennu uses."))


# ---------------------------------------------------------------- STATS (self-hosted, from stats.json)
def load_stats():
    p = os.path.join(ROOT, "stats.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print("stats.json unreadable:", e)
    return None


def fdate(s, year=True):
    d = datetime.date.fromisoformat(s)
    return f"{d.strftime('%b')} {d.day}, {d.year}" if year else f"{d.strftime('%b')} {d.day}"


def stats_card(s):
    W, H = 900, 262
    n = lambda k: f"{s[k]:,}" if s else "-"
    cells = [("Public repositories", n("repos")), ("Stars earned", n("stars")), ("Followers", n("followers")),
             ("Commits, last year", n("commits_year")), ("Pull requests", n("prs")), ("Issues", n("issues"))]
    b = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="18" fill="{PANEL}" stroke="{LINE}"/>',
         f'<line x1="452" y1="28" x2="452" y2="{H-28}" stroke="{LINE}"/>']
    for i, (lab, val) in enumerate(cells):
        r, c = divmod(i, 2)
        x, y = 42 + c * 205, 70 + r * 66
        b.append(f'<text x="{x}" y="{y}" font-size="30" font-weight="700" class="sans" fill="#f4f4f6">{val}</text>')
        b.append(f'<text x="{x}" y="{y+21}" font-size="12.5" class="sans" fill="{SOFT}">{esc(lab)}</text>')
    cur = s["cur_streak"] if s else None
    lon = s["longest"] if s else None
    total = f"{s['total_contrib']:,}" if s else "-"
    cols = [(540, total, "Total contributions", f"Since {fdate(s['first_day'])}" if s else "waiting for first run"),
            (676, None, "Current streak", f"{fdate(cur['start'], False)} - {fdate(cur['end'], False)}" if cur and cur["n"] else "no active streak"),
            (812, f"{lon['n']:,}" if lon else "-", "Longest streak", f"{fdate(lon['start'], False)} - {fdate(lon['end'], False)}" if lon and lon["n"] else "")]
    for cx, val, lab, sub in cols:
        if val is None:
            b.append(f'<circle cx="{cx}" cy="108" r="40" fill="none" stroke="#2c2c31" stroke-width="6"/>')
            b.append(f'<circle cx="{cx}" cy="108" r="40" fill="none" stroke="#f4f4f6" stroke-width="6" stroke-linecap="round" stroke-dasharray="{2*math.pi*40*0.78:.1f} 999" transform="rotate(-90 {cx} 108)"/>')
            b.append(f'<text x="{cx}" y="119" font-size="32" font-weight="700" text-anchor="middle" class="sans" fill="#f4f4f6">{cur["n"] if cur else "-"}</text>')
        else:
            b.append(f'<text x="{cx}" y="120" font-size="34" font-weight="700" text-anchor="middle" class="sans" fill="#f4f4f6">{val}</text>')
        b.append(f'<text x="{cx}" y="176" font-size="13" text-anchor="middle" class="sans" fill="#d0d0d6">{lab}</text>')
        b.append(f'<text x="{cx}" y="196" font-size="11" text-anchor="middle" class="mono" fill="{SOFT}">{esc(sub)}</text>')
    note = f"Updated {fdate(s['updated'])} | live from GitHub" if s else "Run the 'Build profile assets' workflow once to fill in live numbers"
    b.append(f'<text x="42" y="{H-20}" font-size="10.5" class="mono" fill="#5c5c64">{esc(note)}</text>')
    save("stats.svg", svg(W, H, "".join(b), "GitHub stats", "Repositories, stars, followers, commits, pull requests, issues and contribution streaks."))


def languages_card(s):
    W, H = 900, 196
    shades = ["#f4f4f6", "#cfcfd4", "#a9a9b0", "#84848c", "#63636b", "#46464e", "#303036"]
    b = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="18" fill="{PANEL}" stroke="{LINE}"/>',
         f'<text x="40" y="46" font-size="16" font-weight="700" class="sans" fill="#f4f4f6">Most used languages</text>',
         f'<text x="{W-40}" y="46" font-size="11" text-anchor="end" class="mono" fill="#5c5c64">by code size, public repositories</text>']
    langs = (s or {}).get("langs") or []
    tot = sum(v for _, v in langs) or 1
    top = langs[:6]
    rest = sum(v for _, v in langs[6:])
    items = [(nm, v / tot * 100) for nm, v in top] + ([("Other", rest / tot * 100)] if rest > 0 else [])
    bx, bw = 40, W - 80
    b.append(f'<clipPath id="bar"><rect x="{bx}" y="64" width="{bw}" height="14" rx="7"/></clipPath><g clip-path="url(#bar)">')
    if items:
        x = bx
        for i, (nm, p) in enumerate(items):
            w = bw * p / 100
            b.append(f'<rect x="{x:.2f}" y="64" width="{w+0.5:.2f}" height="14" fill="{shades[i]}"/>')
            x += w
    else:
        b.append(f'<rect x="{bx}" y="64" width="{bw}" height="14" fill="#2a2a2f"/>')
    b.append("</g>")
    if items:
        for i, (nm, p) in enumerate(items):
            r, c = divmod(i, 4)
            x, y = 40 + c * 205, 116 + r * 34
            b.append(f'<circle cx="{x+5}" cy="{y-4}" r="5" fill="{shades[i]}"/>')
            b.append(f'<text x="{x+18}" y="{y}" font-size="13" class="sans" fill="#d0d0d6">{esc(nm)}</text>')
            b.append(f'<text x="{x+18}" y="{y+16}" font-size="11.5" class="mono" fill="{SOFT}">{p:.1f}%</text>')
    else:
        b.append(f'<text x="40" y="118" font-size="13" class="sans" fill="{SOFT}">Run the Build profile assets workflow once to fill this in.</text>')
    save("languages.svg", svg(W, H, "".join(b), "Most used languages", "Share of each programming language across public repositories."))


def snake_placeholders():
    """Only created when missing; the workflow replaces them with the real animated snake."""
    for fn in ("github-snake.svg", "github-snake-dark.svg"):
        if os.path.exists(os.path.join(OUT, fn)):
            continue
        body = (f'<rect x=".5" y=".5" width="899" height="139" rx="18" fill="{PANEL}" stroke="{LINE}"/>'
                f'<text x="450" y="76" font-size="14" text-anchor="middle" class="sans" fill="{SOFT}">Contribution snake appears after the first run of the "Build profile assets" workflow</text>')
        save(fn, svg(900, 140, body, "Contribution snake", "Placeholder for the contribution snake animation."))


# ---------------------------------------------------------------- FOOTER
def footer():
    W, H = 900, 200
    lw, lh = 64, 64 * LOGO_H / LOGO_W
    defs = (f'<clipPath id="rc"><rect width="{W}" height="{H}" rx="20"/></clipPath>'
            f'<filter id="tb" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="0 0 0 0 .3  0 0 0 0 .3  0 0 0 0 .33  0 0 0 1 0"/></filter>'
            f'<image id="logo" width="{lw}" height="{lh:.2f}" href="data:image/png;base64,{LOGO_B64}"/>')
    css = "@keyframes flt{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}.flt{animation:flt 4.5s ease-in-out infinite}"
    b = [f'<g clip-path="url(#rc)"><rect width="{W}" height="{H}" fill="{BG}"/>']
    for cx, cy, a, cls, d in [(90, 60, 20, "b2", 1), (806, 52, 16, "b3", 3), (140, 150, 11, "b1", 5), (770, 150, 22, "b2", 2), (450, 188, 7, "b1", 4)]:
        b.append(cube(cx, cy, a, cls, d))
    lay = "".join(f'<use href="#logo" x="{-lw/2+i*.8:.2f}" y="{-lh/2+i*.8:.2f}" filter="url(#tb)"/>' for i in range(6, 0, -1))
    lay += f'<use href="#logo" x="{-lw/2}" y="{-lh/2:.2f}"/>'
    b.append(f'<g transform="translate(450,56)"><g class="flt">{lay}</g></g>')
    for i, t in enumerate(["Building practical tools, learning through iteration,", "and testing for reliability."]):
        b.append(title(t, 450, 132 + i * 30, 23, "middle", depth=0, front="#d0d0d6", max_w=700, fb_size=17))
    b.append(f'</g><rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="20" fill="none" stroke="{LINE}"/>')
    save("footer.svg", svg(W, H, "".join(b), "Kennu Elnar footer", "Closing note with the KE logo.", defs, css))


# ---------------------------------------------------------------- real brand logos for icons that have no bundled logo
def upgrade_brand_icons():
    """Best effort: download the real Cline / Manus / Antigravity logos (only when FETCH_BRAND_ICONS=1)."""
    if os.environ.get("FETCH_BRAND_ICONS") != "1":
        return
    for key in ("cline", "manus", "antigravity"):
        if not ICONS.get(key, {}).get("generic"):
            continue
        try:
            req = urllib.request.Request(f"https://unpkg.com/@lobehub/icons-static-svg@latest/icons/{key}.svg",
                                         headers={"User-Agent": "profile-builder"})
            t = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
            if re.search(r"<(mask|clipPath|linearGradient|radialGradient|filter)", t):
                print("brand icon", key, "skipped (uses effects)")
                continue
            vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', t).group(1).split()]
            ds = re.findall(r'<path[^>]*?\sd="([^"]+)"', t)
            if not ds:
                continue
            ICONS[key] = {"vb": vb, "d": " ".join(ds), "rule": "evenodd" if "evenodd" in t else "nonzero"}
            print("brand icon", key, "downloaded")
        except Exception as e:
            print("brand icon", key, "download failed, keeping stand-in:", e)


# ---------------------------------------------------------------- run
if __name__ == "__main__":
    load_font()
    upgrade_brand_icons()
    st = load_stats()
    save("hero.svg", hero())
    header("h-about.svg", "About Me", "who I am")
    header("h-focus.svg", "Current Focus", "what I'm exploring")
    header("h-projects.svg", "Featured Work", "things I've built")
    header("h-stack.svg", "Tech Stack", "tools I build with")
    header("h-stats.svg", "GitHub Stats", "live numbers")
    header("h-connect.svg", "Let's Connect", "say hello")
    about()
    focus()
    projects()
    capabilities()
    stats_card(st)
    languages_card(st)
    snake_placeholders()
    footer()
