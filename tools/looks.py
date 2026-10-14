"""Scenes, palettes and the catalog of looks for the verse pictures (1080 x 1350).

Everything is drawn as SVG by code, so any look can be redrawn on a fresh machine with no image files.
Each scene function takes (seed, palette) and returns SVG markup for a full 1080x1350 canvas.
LOOKS maps a look id to a scene, a palette, a text layout and a plain-English description for alt text.
"""
import math
import random

W, H = 1080, 1350


def f(v):
    return f"{v:.1f}"


def stops(lst):
    out = []
    for s in lst:
        op = f' stop-opacity="{s[2]}"' if len(s) > 2 else ""
        out.append(f'<stop offset="{s[0]}" stop-color="{s[1]}"{op}/>')
    return "".join(out)


def lin(gid, lst, x1=0, y1=0, x2=0, y2=1):
    return f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{stops(lst)}</linearGradient>'


def rad(gid, color, inner=1.0, outer=0.0, cx=0.5, cy=0.5, r=0.5):
    return (f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}">'
            f'<stop offset="0" stop-color="{color}" stop-opacity="{inner}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="{outer}"/></radialGradient>')


COMMON_DEFS = "".join(
    f'<filter id="b{n}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{n}"/></filter>'
    for n in (4, 8, 14, 30, 70)
)


def ridge(r, base, amp, octaves=4, sharp=0.0, step=6, x0=-12, x1=W + 12):
    comps = []
    for o in range(octaves):
        wl = (W * r.uniform(0.9, 1.5)) / (1.9 ** o)
        a = amp / (1.8 ** o)
        comps.append((wl, a, r.uniform(0, 2 * math.pi)))
    pts = []
    for x in range(x0, x1 + 1, step):
        y = base
        for wl, a, ph in comps:
            s = math.sin(2 * math.pi * x / wl + ph)
            if sharp:
                s = (1 - sharp) * s + sharp * (1 - 2 * abs(s))
            y -= a * s
        pts.append((x, y))
    return pts


def fill_path(pts, bottom=H + 20):
    d = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in pts)
    return d + f" L{pts[-1][0]},{bottom} L{pts[0][0]},{bottom} Z"


def line_pts(pts):
    return " ".join(f"{f(x)},{f(y)}" for x, y in pts)


def ground_y(pts, x):
    step = pts[1][0] - pts[0][0]
    i = max(0, min(len(pts) - 1, int((x - pts[0][0]) / step)))
    return pts[i][1]


def pines(r, ground, count, hmin, hmax, color, wscale=0.42, op=1.0, xmin=-30, xmax=W + 30):
    out = []
    for _ in range(count):
        x = r.uniform(xmin, xmax)
        h = r.uniform(hmin, hmax)
        y = ground_y(ground, x) + 6
        w = h * wscale
        for t in range(5):
            ty = y - h + t * h * 0.17
            th = h * 0.36
            tw = w * (0.38 + 0.62 * (t + 1) / 5)
            out.append(f'<polygon points="{f(x)},{f(ty)} {f(x + tw / 2)},{f(ty + th)} {f(x - tw / 2)},{f(ty + th)}" fill="{color}" opacity="{op}"/>')
        out.append(f'<rect x="{f(x - 4)}" y="{f(y - h * 0.1)}" width="8" height="{f(h * 0.12)}" fill="{color}" opacity="{op}"/>')
    return "".join(out)


def star_field(r, count, ymax, big=14, color="#fff", fade=True):
    out = []
    for _ in range(count):
        x, y = r.uniform(0, W), r.uniform(0, ymax)
        rad_ = r.choice([0.6, 0.7, 0.8, 0.9, 1.1, 1.3, 1.6])
        op = r.uniform(0.35, 1.0) * (max(0.15, 1 - y / H) if fade else 1)
        out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{rad_}" fill="{color}" opacity="{op:.2f}"/>')
    for _ in range(big):
        x, y = r.uniform(60, W - 60), r.uniform(40, ymax * 0.75)
        out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="6" fill="#cfe0ff" opacity="0.5" filter="url(#b8)"/>'
                   f'<circle cx="{f(x)}" cy="{f(y)}" r="1.9" fill="{color}"/>')
    return "".join(out)


# --------------------------------------------------------------------------- scenes
def aurora(r, cols):
    out = []
    for k, col in enumerate(cols):
        base = 330 + k * 100 + r.uniform(-30, 30)
        top, bot = [], []
        for x in range(-40, W + 41, 24):
            y = base + 70 * math.sin(x / 190 + k * 1.7) + 35 * math.sin(x / 71 + k)
            h = 190 + 90 * math.sin(x / 260 + k * 2.3) + 40 * math.sin(x / 47)
            top.append((x, y))
            bot.append((x, y + h))
        d = ("M" + " L".join(f"{f(x)},{f(y)}" for x, y in top) + " L"
             + " L".join(f"{f(x)},{f(y)}" for x, y in reversed(bot)) + " Z")
        out.append(f'<defs>{lin(f"au{k}", [(0, col, 0), (0.28, col, 0.55), (1, col, 0)])}</defs>'
                   f'<path d="{d}" fill="url(#au{k})" filter="url(#b14)" opacity="0.8"/>')
    return "".join(out)


def scene_night(seed, p):
    r = random.Random(seed)
    mx, my = p.get("moon_xy", (896, 150))
    s = ['<defs>' + COMMON_DEFS + lin("sky", p["sky"]) + rad("mw", p["mw"], p.get("mw_op", 0.6), 0)
         + rad("moonglow", p["moon_glow"], 0.55, 0) + lin("fogd", [(0, p["fog"], 0), (0.6, p["fog"], 0.35), (1, p["fog"], 0)])
         + f'<mask id="cres"><rect width="{W}" height="{H}" fill="black"/><circle cx="{mx}" cy="{my}" r="56" fill="white"/>'
         f'<circle cx="{mx + 24}" cy="{my - 11}" r="50" fill="black"/></mask></defs>']
    s.append(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    s.append('<g transform="rotate(-28 540 560)"><ellipse cx="540" cy="560" rx="780" ry="140" fill="url(#mw)" filter="url(#b30)" opacity="0.5"/>'
             '<ellipse cx="640" cy="540" rx="520" ry="60" fill="url(#mw)" filter="url(#b30)" opacity="0.45"/></g>')
    if p.get("aurora"):
        s.append(aurora(r, p["aurora"]))
    s.append(star_field(r, p.get("stars", 340), H * 0.84))
    mode = p.get("moon", "crescent")
    if mode != "none":
        s.append(f'<circle cx="{mx + 10}" cy="{my}" r="190" fill="url(#moonglow)"/>')
    if mode == "crescent":
        s.append(f'<rect width="{W}" height="{H}" fill="{p["moon_color"]}" mask="url(#cres)"/>')
    elif mode == "full":
        s.append(f'<circle cx="{mx}" cy="{my}" r="62" fill="{p["moon_color"]}"/>')
        for dx, dy, rr, op in ((-24, -16, 17, 0.07), (17, -27, 10, 0.06), (27, 10, 15, 0.07), (-5, 27, 13, 0.06), (-33, 14, 8, 0.05), (7, -3, 9, 0.05)):
            s.append(f'<circle cx="{mx + dx}" cy="{my + dy}" r="{rr}" fill="#5a3a6a" opacity="{op}" filter="url(#b4)"/>')
    ground = ridge(r, 1250, 24, octaves=3)
    s.append(pines(r, ground, 26, 150, 300, p["pine_far"], op=0.9))
    s.append(f'<rect x="0" y="1010" width="{W}" height="300" fill="url(#fogd)"/>')
    s.append(pines(r, ground, 20, 220, 430, p["pine_near"]))
    s.append(f'<path d="{fill_path(ground)}" fill="{p["ground"]}"/>')
    return "".join(s)


def scene_dawn(seed, p):
    r = random.Random(seed)
    hz = 945
    s = ['<defs>' + COMMON_DEFS + lin("sky", p["sky"]) + rad("glow", p["glow"], 0.95, 0)
         + lin("mist", [(0, p["mist"], 0), (0.5, p["mist"], 0.55), (1, p["mist"], 0)]) + '</defs>']
    s.append(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    sx = p.get("sun_x", 640)
    sy = hz - 35
    s.append(f'<circle cx="{sx}" cy="{sy}" r="560" fill="url(#glow)"/>')
    s.append(f'<circle cx="{sx}" cy="{sy}" r="92" fill="{p["sun"]}"/>')
    for i, (c_top, c_bot) in enumerate(p["layers"]):
        base = hz + 28 + i * 112
        pts = ridge(r, base, 58 + i * 12, octaves=3)
        s.append(f'<defs>{lin(f"h{i}", [(0, c_top), (1, c_bot)])}</defs><path d="{fill_path(pts)}" fill="url(#h{i})"/>')
        if i < len(p["layers"]) - 1:
            s.append(f'<rect x="0" y="{f(base + 10)}" width="{W}" height="200" fill="url(#mist)" opacity="{0.6 - i * 0.12:.2f}"/>')
    return "".join(s)


def scene_sea(seed, p):
    r = random.Random(seed)
    hz = 891
    flip = p.get("flip", False)
    gx = 440 if flip else 640
    s = ['<defs>' + COMMON_DEFS + lin("sky", p["sky"]) + lin("sea", p["sea"])
         + rad("hzglow", p["hzglow"], 0.8, 0) + rad("lamp", p["lamp"], 0.95, 0)
         + lin("beam", [(0, p["lamp"], 0.75), (1, p["lamp"], 0)], 0, 0, 1, 0) + '</defs>']
    s.append(f'<rect width="{W}" height="{hz}" fill="url(#sky)"/>')
    if p.get("stars"):
        s.append(star_field(r, 260, hz * 0.9, big=10))
    s.append(f'<rect y="{hz}" width="{W}" height="{H - hz}" fill="url(#sea)"/>')
    s.append(f'<ellipse cx="{gx}" cy="{hz}" rx="720" ry="170" fill="url(#hzglow)"/>')
    for i in range(22):
        y = hz + 16 + (i ** 1.55) * 8.5
        amp, wl = 1.2 + i * 0.75, 90 + i * 26
        ph = r.uniform(0, 6.28)
        pts = " ".join(f"{x},{f(y + amp * math.sin(2 * math.pi * x / wl + ph))}" for x in range(-20, W + 40, 10))
        s.append(f'<polyline points="{pts}" fill="none" stroke="{p["streak"]}" stroke-opacity="{0.05 + 0.006 * i:.3f}" stroke-width="{1 + i * 0.14:.2f}"/>')
    for j in range(26):
        y = hz + 14 + j * 17
        w = 26 + j * 10 + r.uniform(-8, 8)
        s.append(f'<rect x="{f(gx - w / 2 + r.uniform(-8, 8))}" y="{y}" width="{f(w)}" height="3" rx="1.5" fill="{p["streak"]}" opacity="{max(0.06, 0.55 - j * 0.02):.2f}"/>')
    lx, rock_top, lamp_y = 205, 1000, 672
    s.append('<g transform="translate(1080,0) scale(-1,1)">' if flip else '<g>')
    s.append(f'<polygon points="{lx + 20},{lamp_y} {W + 60},{lamp_y - 120} {W + 60},{lamp_y + 120}" fill="url(#beam)" filter="url(#b8)"/>')
    s.append(f'<circle cx="{lx}" cy="{lamp_y + 10}" r="150" fill="url(#lamp)"/>')
    s.append(f'<polygon points="{lx - 42},{rock_top} {lx + 42},{rock_top} {lx + 27},{lamp_y + 40} {lx - 27},{lamp_y + 40}" fill="{p["tower"]}"/>')
    s.append(f'<rect x="{lx - 40}" y="{lamp_y + 32}" width="80" height="9" fill="{p["tower"]}"/>')
    s.append(f'<rect x="{lx - 19}" y="{lamp_y - 6}" width="38" height="40" fill="{p["lamp"]}"/>')
    s.append(f'<polygon points="{lx - 28},{lamp_y - 6} {lx + 28},{lamp_y - 6} {lx},{lamp_y - 40}" fill="{p["tower"]}"/>')
    s.append(f'<rect x="{lx - 2}" y="{lamp_y - 58}" width="4" height="20" fill="{p["tower"]}"/>')
    rock = [(-20, H), (-20, 1046), (60, 1020), (135, 1004), (205, rock_top), (290, 1010), (352, 1034), (420, 1066), (486, 1108), (540, H)]
    s.append('<polygon points="' + " ".join(f"{x},{y}" for x, y in rock) + f'" fill="{p["rock"]}" stroke="{p["rock"]}" stroke-width="6" stroke-linejoin="round"/>')
    s.append('</g>')
    return "".join(s)


def scene_mist(seed, p):
    r = random.Random(seed)
    sx, sy = p.get("sun_xy", (790, 610))
    s = ['<defs>' + COMMON_DEFS + lin("sky", p["sky"]) + rad("sunglow", p["sunglow"], 0.95, 0)
         + lin("fog", [(0, p["fog"], 0), (0.55, p["fog"], 0.78), (1, p["fog"], 0)]) + '</defs>']
    s.append(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    s.append(f'<circle cx="{sx}" cy="{sy}" r="380" fill="url(#sunglow)"/><circle cx="{sx}" cy="{sy}" r="62" fill="{p["sun"]}" opacity="0.95"/>')
    for i, (c1, c2) in enumerate(p["ridges"]):
        base = 700 + i * 118
        pts = ridge(r, base, 120 - i * 10, octaves=4, sharp=0.78)
        s.append(f'<defs>{lin(f"m{i}", [(0, c1), (1, c2)])}</defs><path d="{fill_path(pts)}" fill="url(#m{i})"/>')
        if i < len(p["ridges"]) - 1:
            s.append(f'<rect x="0" y="{base + 20}" width="{W}" height="230" fill="url(#fog)" opacity="{0.9 - i * 0.12:.2f}"/>')
    return "".join(s)


def scene_paper(seed, p):
    s = ['<defs>' + COMMON_DEFS
         + rad("wash1", p["wash1"], p.get("wash1_op", 0.38), 0) + rad("wash2", p["wash2"], p.get("wash2_op", 0.22), 0)
         + '<radialGradient id="paper" cx="0.5" cy="0.42" r="0.75">' + stops(p["base"]) + '</radialGradient></defs>']
    s.append(f'<rect width="{W}" height="{H}" fill="url(#paper)"/>')
    s.append('<ellipse cx="170" cy="190" rx="460" ry="360" fill="url(#wash1)" filter="url(#b30)"/>')
    s.append('<ellipse cx="930" cy="1180" rx="520" ry="400" fill="url(#wash2)" filter="url(#b30)"/>')
    for inset, op, sw in ((58, 0.55, 2.5), (74, 0.3, 1.2)):
        s.append(f'<rect x="{inset}" y="{inset}" width="{W - 2 * inset}" height="{H - 2 * inset}" fill="none" stroke="{p["border"]}" stroke-opacity="{op}" stroke-width="{sw}"/>')
    for cx, cy in ((84, 84), (W - 84, 84), (84, H - 84), (W - 84, H - 84)):
        s.append(f'<rect x="{cx - 7}" y="{cy - 7}" width="14" height="14" transform="rotate(45 {cx} {cy})" fill="{p["diamond"]}" opacity="0.65"/>')
    return "".join(s)


def scene_dunes(seed, p):
    r = random.Random(seed)
    hz = p.get("hz", 860)
    sx, sy = p.get("sun_xy", (660, hz - 20))
    s = ['<defs>' + COMMON_DEFS + lin("sky", p["sky"]) + rad("glow", p["glow"], 0.9, 0)
         + lin("haze", [(0, p["haze"], 0), (0.5, p["haze"], 0.5), (1, p["haze"], 0)]) + '</defs>']
    s.append(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    s.append(f'<circle cx="{sx}" cy="{sy}" r="520" fill="url(#glow)"/><circle cx="{sx}" cy="{sy}" r="{p.get("sun_r", 96)}" fill="{p["sun"]}"/>')
    n = len(p["dunes"])
    for i, (c1, c2) in enumerate(p["dunes"]):
        base = hz + 40 + i * 105
        pts = ridge(r, base, 70 + i * 14, octaves=2, sharp=0.3)
        s.append(f'<defs>{lin(f"d{i}", [(0, c1), (1, c2)])}</defs><path d="{fill_path(pts)}" fill="url(#d{i})"/>')
        s.append(f'<polyline points="{line_pts(pts)}" fill="none" stroke="{p["crest"]}" stroke-opacity="0.35" stroke-width="2.5"/>')
        if i < n - 1:
            s.append(f'<rect x="0" y="{base + 10}" width="{W}" height="200" fill="url(#haze)" opacity="{0.55 - 0.08 * i:.2f}"/>')
    return "".join(s)


def scene_forest(seed, p):
    r = random.Random(seed)
    gx, gy = p.get("glow_xy", (250, 110))
    s = ['<defs>' + COMMON_DEFS + lin("sky", p["sky"]) + rad("glow", p["glow"], p.get("glow_op", 0.85), 0)
         + lin("fog", [(0, p["fog"], 0), (0.5, p["fog"], 0.75), (1, p["fog"], 0)])
         + lin("ray", [(0, p["rays"], p.get("ray_op", 0.5)), (1, p["rays"], 0)]) + '</defs>']
    s.append(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    s.append(f'<circle cx="{gx}" cy="{gy}" r="470" fill="url(#glow)"/>')
    for k in range(6):
        a = math.radians(58 + k * 9 + r.uniform(-2, 2))
        wd = math.radians(r.uniform(2.2, 4.5))
        L = 1700
        pts = [(gx, gy), (gx + L * math.cos(a - wd), gy + L * math.sin(a - wd)), (gx + L * math.cos(a + wd), gy + L * math.sin(a + wd))]
        s.append('<polygon points="' + " ".join(f"{f(x)},{f(y)}" for x, y in pts) + '" fill="url(#ray)" filter="url(#b8)"/>')
    n = len(p["trees"])
    for i, col in enumerate(p["trees"]):
        base = 780 + i * 125
        ground = ridge(r, base, 18, octaves=2)
        s.append(pines(r, ground, 34 - i * 4, 150 + i * 40, 260 + i * 70, col))
        s.append(f'<path d="{fill_path(ground)}" fill="{col}"/>')
        if i < n - 1:
            s.append(f'<rect x="0" y="{base - 160}" width="{W}" height="360" fill="url(#fog)" opacity="{0.8 - 0.12 * i:.2f}"/>')
    return "".join(s)


def scene_rays(seed, p):
    r = random.Random(seed)
    sx, sy = p.get("sun_xy", (720, 560))
    s = ['<defs>' + COMMON_DEFS + lin("sky", p["sky"]) + rad("glow", p["glow"], 0.85, 0)
         + lin("beam", [(0, p["beam"], 0.5), (1, p["beam"], 0)]) + '</defs>']
    s.append(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    s.append(f'<circle cx="{sx}" cy="{sy}" r="430" fill="url(#glow)"/>')
    for k in range(10):
        a = math.radians(48 + k * 10.5 + r.uniform(-2, 2))
        wd = math.radians(r.uniform(2.2, 4.8))
        L = 1900
        pts = [(sx, sy), (sx + L * math.cos(a - wd), sy + L * math.sin(a - wd)), (sx + L * math.cos(a + wd), sy + L * math.sin(a + wd))]
        s.append('<polygon points="' + " ".join(f"{f(x)},{f(y)}" for x, y in pts) + '" fill="url(#beam)" filter="url(#b14)"/>')
    for _ in range(22):
        cx, cy = r.uniform(-120, W + 120), r.uniform(30, 520)
        rx, ry = r.uniform(170, 400), r.uniform(40, 105)
        s.append(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{p["cloud"]}" opacity="{r.uniform(0.55, 0.95):.2f}" filter="url(#b30)"/>')
    for i, col in enumerate(p["ground"]):
        pts = ridge(r, 1080 + i * 120, 55 + i * 10, octaves=3)
        s.append(f'<path d="{fill_path(pts)}" fill="{col}"/>')
    return "".join(s)


def scene_nebula(seed, p):
    r = random.Random(seed)
    s = ['<defs>' + COMMON_DEFS + lin("sky", p["sky"]) + '</defs>']
    s.append(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    for col in p["blobs"]:
        for _ in range(2):
            cx, cy = r.uniform(0, W), r.uniform(0, H * 0.8)
            rx, ry = r.uniform(250, 520), r.uniform(120, 260)
            s.append(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{col}" opacity="{r.uniform(0.22, 0.45):.2f}" '
                     f'filter="url(#b70)" transform="rotate({r.uniform(-60, 60):.0f} {f(cx)} {f(cy)})" style="mix-blend-mode:screen"/>')
    s.append(star_field(r, 420, H * 0.78, big=18, fade=False))
    if p.get("planet"):
        cy, R = 2000, 1040
        s.append('<defs><radialGradient id="rim" gradientUnits="userSpaceOnUse" cx="540" cy="%d" r="%d">'
                 '<stop offset="0.93" stop-color="%s" stop-opacity="0"/><stop offset="0.965" stop-color="%s" stop-opacity="0.85"/>'
                 '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient></defs>' % (cy, R + 60, p["rim"], p["rim"], p["rim"]))
        s.append(f'<circle cx="540" cy="{cy}" r="{R + 60}" fill="url(#rim)" filter="url(#b8)"/>')
        s.append(f'<circle cx="540" cy="{cy}" r="{R}" fill="{p["planet"]}"/>')
    return "".join(s)


def scene_watercolor(seed, p):
    r = random.Random(seed)
    s = ['<defs>' + COMMON_DEFS
         + f'<filter id="wc" x="-30%" y="-30%" width="160%" height="160%"><feTurbulence type="fractalNoise" baseFrequency="0.011" numOctaves="3" seed="{seed % 97 + 1}" result="n"/>'
         '<feDisplacementMap in="SourceGraphic" in2="n" scale="85"/><feGaussianBlur stdDeviation="16"/></filter></defs>']
    s.append(f'<rect width="{W}" height="{H}" fill="{p["paper"]}"/>')
    for col in p["blobs"]:
        a = r.uniform(0, 6.283)
        dist = r.uniform(500, 700)
        cx, cy = 540 + dist * math.cos(a) * 0.95, 675 + dist * math.sin(a) * 1.05
        rx, ry = r.uniform(180, 300), r.uniform(160, 270)
        s.append(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{col}" opacity="{r.uniform(0.34, 0.52):.2f}" filter="url(#wc)"/>')
    return "".join(s)


def scene_lake(seed, p):
    r = random.Random(seed)
    hz = 820
    sx, sy = p.get("sun_xy", (760, 560))
    top = [f'<rect x="-60" width="{W + 120}" height="{hz}" fill="url(#sky)"/>',
           f'<circle cx="{sx}" cy="{sy}" r="{p.get("glow_r", 340)}" fill="url(#sunglow)"/><circle cx="{sx}" cy="{sy}" r="58" fill="{p["sun"]}"/>']
    for i, (c1, c2) in enumerate(p["ridges"]):
        base = hz - 150 + i * 70
        pts = ridge(r, base, 95 - i * 14, octaves=4, sharp=0.6)
        top.append(f'<path d="{fill_path(pts, bottom=hz)}" fill="url(#m{i})"/>')
    defs = ('<defs>' + COMMON_DEFS + lin("sky", p["sky"], 0, 0, 0, 1) + rad("sunglow", p["sun"], 0.8, 0)
            + "".join(lin(f"m{i}", [(0, c1), (1, c2)]) for i, (c1, c2) in enumerate(p["ridges"]))
            + f'<clipPath id="above"><rect width="{W}" height="{hz}"/></clipPath>'
            f'<clipPath id="below"><rect y="{hz}" width="{W}" height="{H - hz}"/></clipPath></defs>')
    s = [defs, '<g clip-path="url(#above)">', "".join(top), '</g>',
         '<g clip-path="url(#below)"><g filter="url(#b4)">', f'<g transform="translate(0,{2 * hz}) scale(1,-1)">', "".join(top), '</g></g>',
         f'<rect y="{hz}" width="{W}" height="{H - hz}" fill="{p["water"]}" opacity="0.28"/>']
    for i in range(34):
        y = hz + 14 + i * 15.5
        w = r.uniform(60, 240) * (0.6 + i / 40)
        x = r.uniform(0, W - w)
        s.append(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="2" rx="1" fill="{p["ripple"]}" opacity="{r.uniform(0.08, 0.28):.2f}"/>')
    s.append('</g>')
    return "".join(s)


def scene_boho(seed, p):
    r = random.Random(seed)
    cx, cy = 540, p.get("cy", 1140)
    s = [f'<rect width="{W}" height="{H}" fill="{p["bg"]}"/>']
    for R, col in p["radii"]:
        s.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{col}"/>')
    s.append(f'<rect x="0" y="{cy}" width="{W}" height="{H - cy}" fill="{p["bg"]}"/>')
    for k in range(3):
        s.append(f'<rect x="{cx - 470 + k * 60}" y="{cy + 40 + k * 26}" width="{940 - k * 120}" height="4" rx="2" fill="{p["radii"][1 + k % 2][1]}" opacity="0.8"/>')
    for _ in range(26):
        x, y = r.uniform(80, W - 80), r.uniform(60, cy - 520)
        s.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{r.choice([2, 3, 4])}" fill="{p["dot"]}" opacity="{r.uniform(0.3, 0.7):.2f}"/>')
    return "".join(s)


SCENES = {
    "night": scene_night, "dawn": scene_dawn, "sea": scene_sea, "mist": scene_mist, "paper": scene_paper,
    "dunes": scene_dunes, "forest": scene_forest, "rays": scene_rays, "nebula": scene_nebula,
    "watercolor": scene_watercolor, "lake": scene_lake, "boho": scene_boho,
}

# --------------------------------------------------------------------------- palettes
LIGHT_INK = "#f7f2e6"
PAL = {
    "night": {
        "midnight": dict(sky=[(0, "#04061a"), (0.5, "#0d1445"), (0.82, "#27286b"), (1, "#4b3a7c")], mw="#aab9ff", moon="crescent",
                         moon_color="#fff6dc", moon_glow="#fff2c8", pine_far="#15184a", pine_near="#070a22", ground="#060820", fog="#4b3a7c"),
        "aurora": dict(sky=[(0, "#010b14"), (0.45, "#04202c"), (0.8, "#0b3b42"), (1, "#1a5a54")], mw="#7fe8d0", mw_op=0.35, moon="none",
                       moon_color="#fff", moon_glow="#c8fff0", aurora=["#5cffb0", "#35d0c0", "#b25cff"], stars=300,
                       pine_far="#0a2a30", pine_near="#041418", ground="#031013", fog="#1a5a54"),
        "plum": dict(sky=[(0, "#12061f"), (0.5, "#2a0f45"), (0.82, "#5a1f63"), (1, "#8a3a6b")], mw="#e6a8ff", mw_op=0.4, moon="full",
                     moon_color="#ffe9ef", moon_glow="#ffd0e6", moon_xy=(860, 170), pine_far="#2a1038", pine_near="#12061c", ground="#0e0517", fog="#8a3a6b"),
    },
    "dawn": {
        "violet": dict(sky=[(0, "#1b1f58"), (0.34, "#4d3585"), (0.52, "#b5567f"), (0.62, "#f09a5d"), (0.70, "#ffd98d")], glow="#ffd9a0", sun="#fff3d2",
                       layers=[("#7a5a8e", "#4f3f78"), ("#45497f", "#2f3566"), ("#243d66", "#172a4d"), ("#10233a", "#0a1626")], mist="#ffd7b5", sun_x=640),
        "golden": dict(sky=[(0, "#14264a"), (0.36, "#2a4a7a"), (0.52, "#c9704f"), (0.62, "#ffb257"), (0.70, "#ffe19a")], glow="#ffe2a0", sun="#fff6d8",
                       layers=[("#c98a5e", "#8f5a46"), ("#7a4a48", "#553345"), ("#3f2f45", "#2b2038"), ("#1f1a2a", "#121018")], mist="#ffd49a", sun_x=420),
        "rose": dict(sky=[(0, "#2a2150"), (0.34, "#6a3f82"), (0.52, "#d96a86"), (0.62, "#f7a38b"), (0.70, "#ffd9b8")], glow="#ffd3c0", sun="#fff0e6",
                     layers=[("#9a6f9e", "#6f4f86"), ("#5a4a88", "#3d3770"), ("#2f3d6e", "#1f2b57"), ("#141f3d", "#0c1428")], mist="#ffd0c8", sun_x=760),
    },
    "sea": {
        "dusk": dict(sky=[(0, "#12154a"), (0.40, "#47337a"), (0.62, "#a9507f"), (0.82, "#f09566"), (1, "#ffd39b")],
                     sea=[(0, "#3a3f6e"), (0.18, "#1f2b57"), (1, "#060b22")], hzglow="#ffd9a0", lamp="#fff0b8", streak="#ffe1b0", tower="#0b1029", rock="#080c24"),
        "storm": dict(sky=[(0, "#0c121c"), (0.35, "#232d3d"), (0.62, "#4a586b"), (0.85, "#c0965a"), (1, "#ffd89a")],
                      sea=[(0, "#3a4658"), (0.2, "#1c2635"), (1, "#05080f")], hzglow="#ffd9a0", lamp="#fff0b8", streak="#ffe1b0", tower="#070b14", rock="#05080f", flip=True),
        "night": dict(sky=[(0, "#03050f"), (0.45, "#0a1230"), (0.8, "#1a2c5c"), (1, "#34528a")], stars=True,
                      sea=[(0, "#243a66"), (0.2, "#101c3c"), (1, "#030610")], hzglow="#9fc0ff", lamp="#fff4c4", streak="#cfe0ff", tower="#04060f", rock="#03050c"),
    },
    "mist": {
        "blue": dict(sky=[(0, "#e6edf6"), (0.42, "#cfdaea"), (0.62, "#f1e3dc")], sun="#fffaf0", sunglow="#fff6e6", fog="#f4f6fa", sun_xy=(790, 610),
                     ridges=[("#c3d0e2", "#b3c3da"), ("#9db1cc", "#8aa1c0"), ("#748fb0", "#5f7ba0"), ("#4a6786", "#3a5573"), ("#243b53", "#17283b")]),
        "rose": dict(sky=[(0, "#f6e9ea"), (0.42, "#efd5d8"), (0.62, "#fbe9dc")], sun="#fffaf3", sunglow="#fff0e0", fog="#fbf3f2", sun_xy=(800, 640),
                     ridges=[("#dcc5d3", "#cdb3c6"), ("#b79bb8", "#a387a8"), ("#8a74a0", "#745f8e"), ("#5f4f7c", "#4a3c66"), ("#33294d", "#221a38")]),
        "sage": dict(sky=[(0, "#eaf2ea"), (0.42, "#d6e6d8"), (0.62, "#f4efdc")], sun="#fffdf0", sunglow="#fffbe6", fog="#f3f7f1", sun_xy=(780, 590),
                     ridges=[("#c6d6c4", "#b4c8b2"), ("#9ab59b", "#86a388"), ("#6f9078", "#5a7a64"), ("#476650", "#34503e"), ("#243d31", "#16291f")]),
    },
    "paper": {
        "parchment": dict(base=[(0, "#f7efdc"), (0.6, "#f0e4c9"), (1, "#dcc9a2")], wash1="#e7b27c", wash2="#c98b6a", border="#6b4a2b", diamond="#8a4b2a"),
        "linen": dict(base=[(0, "#fbf9f4"), (0.6, "#f1eee6"), (1, "#e0dbcf")], wash1="#9fb4cf", wash2="#c8b9a0", wash1_op=0.3, wash2_op=0.22, border="#2d3b55", diamond="#2d3b55"),
        "slate": dict(base=[(0, "#2c343f"), (0.6, "#222a33"), (1, "#171d25")], wash1="#4a5d7a", wash2="#6a5a3a", wash1_op=0.3, wash2_op=0.22, border="#c9a45a", diamond="#c9a45a"),
    },
    "dunes": {
        "sunset": dict(sky=[(0, "#2b1b4a"), (0.35, "#7a3a6a"), (0.55, "#e0705a"), (0.68, "#ffc27a"), (0.75, "#ffe4b0")], glow="#ffd9a0", sun="#fff1cc", haze="#ffd2a0", crest="#ffe2b8",
                       dunes=[("#d98a5a", "#b86a48"), ("#a85a40", "#7f4636"), ("#6f3a33", "#4c2a2c"), ("#3d2227", "#2a181f")]),
        "noon": dict(sky=[(0, "#4f86b3"), (0.5, "#8fbbd6"), (0.66, "#e8e0cc")], glow="#fff6dc", sun="#fffdf4", haze="#f4ead0", crest="#fff3d6", sun_xy=(300, 840), sun_r=84,
                     dunes=[("#ecd3a4", "#d9b983"), ("#d2a975", "#b98c5a"), ("#b48453", "#946a43"), ("#8d6340", "#6c492f")]),
    },
    "forest": {
        "green": dict(sky=[(0, "#eaf1e6"), (1, "#d4e4d6")], glow="#fff7d6", fog="#eef4ec", rays="#fff6cf",
                      trees=["#b3c8b6", "#88a98f", "#5a846b", "#355f4d", "#183a2f"]),
        "emerald": dict(sky=[(0, "#0a2622"), (1, "#1d4d43")], glow="#d6ffe6", fog="#1f5a4c", rays="#d8ffe8", glow_xy=(800, 100), glow_op=0.55, ray_op=0.26,
                        trees=["#2b6a58", "#1f5648", "#144236", "#0c2e25", "#061a15"]),
    },
    "rays": {
        "storm": dict(sky=[(0, "#0a0f1a"), (0.45, "#1b2433"), (0.7, "#3a4558"), (1, "#6a7688")], glow="#ffe1a0", beam="#ffe8b0", cloud="#10161f",
                      ground=["#0d131c", "#070b12"], sun_xy=(740, 600)),
        "dawn": dict(sky=[(0, "#2a1f4a"), (0.45, "#6a3a7a"), (0.7, "#d0707a"), (1, "#f5b08a")], glow="#ffe0c0", beam="#fff0d8", cloud="#2c1f45",
                     ground=["#2a1a3a", "#150d22"], sun_xy=(360, 600)),
    },
    "nebula": {
        "violet": dict(sky=[(0, "#05071c"), (1, "#0a0f33")], blobs=["#3a2aa0", "#2a6ad0", "#7a3ad0", "#1a8ad0"], planet="#03060f", rim="#8ad0ff"),
        "teal": dict(sky=[(0, "#03121a"), (1, "#081d2a")], blobs=["#0d8a8a", "#a13a8a", "#1a6ab0", "#d04a8a"], planet="#02090e", rim="#ffa0d0"),
    },
    "watercolor": {
        "ocean": dict(paper="#f6f1e6", blobs=["#4aa3b5", "#3d7fa8", "#8ac8c0", "#6fa8c8", "#b8dcd6"]),
        "sunrise": dict(paper="#f9efe2", blobs=["#f08a6a", "#f4b860", "#e86a8a", "#f8d49a", "#c86aa0"]),
        "meadow": dict(paper="#f4f1e2", blobs=["#8aa86a", "#c4b05a", "#5f8a6a", "#d8c88a", "#a8c4a0"]),
    },
    "lake": {
        "dawn": dict(sky=[(0, "#f3e3ea"), (0.55, "#f4cfc4"), (1, "#fbe4cc")], sun="#fffaf0", water="#c9a8b8", ripple="#fff4ea", sun_xy=(760, 560),
                     ridges=[("#c9bfd8", "#b7accb"), ("#9a90b8", "#867ca4"), ("#6a6590", "#575280")]),
        "twilight": dict(sky=[(0, "#0b0f33"), (0.7, "#3a2f7a"), (1, "#e0829a")], sun="#fff0d8", water="#1b1b4a", ripple="#f6c9d8", sun_xy=(800, 700), glow_r=250,
                         ridges=[("#4a3f80", "#3a3270"), ("#2a2560", "#1f1b4c"), ("#12113a", "#0b0a28")]),
    },
    "boho": {
        "terracotta": dict(bg="#f4e8d4", dot="#c9855a", cy=1160, radii=[(430, "#d9825f"), (350, "#e8a36b"), (270, "#f0c389"), (190, "#a8b58a"), (110, "#e2724a")]),
        "navy": dict(bg="#101b3d", dot="#e6c277", cy=1160, radii=[(430, "#1d2f63"), (350, "#2c4585"), (270, "#d9b567"), (190, "#f0d58a"), (110, "#fff1c4")]),
    },
}

# --------------------------------------------------------------------------- text styles
FONTS = {
    "charter": "'Bitstream Charter','Caladea',serif",
    "caladea": "'Caladea','Bitstream Charter',serif",
    "lora": "'Lora','Caladea',serif",
    "baskerville": "'GFS Baskerville','Caladea',serif",
}
# "light" = light text on a dark picture, "dark" = dark text on a light picture
GRAIN = {"light": ("1,1,1", 0.45), "dark": ("0.25,0.22,0.2", 0.32)}
VIGNETTE = {
    "light": "radial-gradient(ellipse at 50% 42%, rgba(0,0,0,0) 50%, rgba(0,0,12,0.4) 100%)",
    "dark": "radial-gradient(ellipse at 50% 42%, rgba(255,255,255,0) 55%, rgba(60,50,40,0.16) 100%)",
}


def _look(scene, pal, seed, mode, ink, accent, zone, align, font, alt, italic=False, brand=None, brand_op=0.62, brand_bottom=50, **extra):
    d = dict(scene=scene, pal=pal, seed=seed, mode=mode, ink=ink, accent=accent, zone=zone, align=align, font=font,
             italic=italic, alt=alt, brand=brand or ink, brand_op=brand_op, brand_bottom=brand_bottom)
    d.update(extra)
    return d


LOOKS = {
    # night forests
    "night-pines-midnight": _look("night", "midnight", 11, "light", LIGHT_INK, "#f1c453", (250, 640), "center", "charter",
                                  "a starry night sky with a crescent moon above a pine forest"),
    "night-pines-aurora": _look("night", "aurora", 14, "light", "#eef8f2", "#8ff0c8", (250, 640), "center", "lora",
                                "a green northern lights sky over a dark pine forest"),
    "night-pines-plum": _look("night", "plum", 17, "light", "#fbf1f3", "#ffc58a", (250, 640), "center", "caladea",
                              "a purple twilight sky with a full moon above a pine forest"),
    # sunrise over hills
    "dawn-hills-violet": _look("dawn", "violet", 21, "light", "#ffffff", "#fff0c8", (120, 600), "left", "charter",
                               "a purple and orange sunrise over layered hills"),
    "dawn-hills-golden": _look("dawn", "golden", 23, "light", "#ffffff", "#ffe7b0", (120, 600), "left", "baskerville",
                               "a golden sunrise over layered dark hills"),
    "dawn-hills-rose": _look("dawn", "rose", 27, "light", "#ffffff", "#ffe6c8", (120, 600), "left", "lora",
                             "a pink and peach sunrise over layered blue hills", italic=True),
    # lighthouse
    "sea-lighthouse-dusk": _look("sea", "dusk", 3, "light", "#ffffff", "#ffe9c2", (110, 470), "left", "charter",
                                 "a lighthouse sending a beam of light across the sea at dusk"),
    "sea-lighthouse-storm": _look("sea", "storm", 5, "light", "#f4f6f8", "#ffdca0", (110, 470), "left", "caladea",
                                  "a lighthouse on a rocky shore under a stormy sky with golden light on the horizon"),
    "sea-lighthouse-night": _look("sea", "night", 9, "light", "#f2f6ff", "#ffd98a", (110, 470), "left", "lora",
                                  "a lighthouse sending a beam of light across the sea under a starry night sky"),
    # misty mountains (light pictures, dark text)
    "mist-ridges-blue": _look("mist", "blue", 8, "dark", "#14263d", "#b0482e", (110, 560), "left", "caladea",
                              "misty blue mountain ridges under a pale sun", brand="#e6eef8", brand_op=0.75),
    "mist-ridges-rose": _look("mist", "rose", 12, "dark", "#3a1f3a", "#a8442f", (110, 560), "left", "charter",
                              "misty pink and purple mountain ridges under a pale sun", brand="#f4e9f2", brand_op=0.75),
    "mist-ridges-sage": _look("mist", "sage", 15, "dark", "#17301f", "#9a4a22", (110, 560), "left", "lora",
                              "misty green mountain ridges under a pale sun", brand="#e6f0e6", brand_op=0.75),
    # paper
    "paper-parchment": _look("paper", "parchment", 5, "dark", "#2b2118", "#8a4b2a", (170, 1010), "center", "caladea",
                             "warm aged paper with a thin border", italic=True, brand_bottom=104, brand_op=0.7),
    "paper-linen": _look("paper", "linen", 6, "dark", "#1f2a44", "#8a5a2b", (170, 1010), "center", "baskerville",
                         "pale linen paper with a thin navy border", brand_bottom=104, brand_op=0.7),
    "paper-slate": _look("paper", "slate", 7, "light", "#f1ead8", "#d9b567", (170, 1010), "center", "lora",
                         "dark slate with a thin gold border", brand_bottom=104, brand_op=0.7),
    # dunes
    "dunes-sunset": _look("dunes", "sunset", 31, "light", "#fff8ee", "#ffd9a0", (120, 560), "left", "charter",
                          "a desert sunset over layered sand dunes"),
    "dunes-noon": _look("dunes", "noon", 33, "dark", "#10263a", "#a8431f", (120, 560), "left", "caladea",
                        "pale sand dunes under a blue sky", brand="#fff3d6", brand_op=0.8),
    # forests in fog
    "forest-fog-green": _look("forest", "green", 41, "dark", "#14281f", "#9a4a22", (120, 520), "center", "lora",
                              "layers of misty green pine trees with soft rays of light", brand="#e8f1ea", brand_op=0.8),
    "forest-fog-emerald": _look("forest", "emerald", 43, "light", "#f1faf4", "#ffd98a", (120, 520), "center", "charter",
                                "deep green pine forest in fog with pale rays of light"),
    # sun breaking through clouds
    "rays-storm-gold": _look("rays", "storm", 51, "light", "#f7f4ec", "#ffd98a", (110, 520), "left", "caladea",
                             "golden rays of sunlight breaking through dark storm clouds"),
    "rays-dawn": _look("rays", "dawn", 53, "light", "#fff6f0", "#ffe0b0", (110, 520), "left", "lora",
                       "pale rays of light breaking through purple clouds at sunrise"),
    # space
    "nebula-violet": _look("nebula", "violet", 61, "light", "#f2f5ff", "#ffd98a", (200, 700), "center", "charter",
                           "a violet and blue starry sky above the curve of a planet"),
    "nebula-teal": _look("nebula", "teal", 63, "light", "#f0fbfb", "#ffe0a0", (200, 700), "center", "baskerville",
                         "a teal and magenta starry sky above the curve of a planet"),
    # watercolor
    "watercolor-ocean": _look("watercolor", "ocean", 71, "dark", "#12304a", "#a8431f", (250, 760), "center", "lora",
                              "soft blue and teal watercolor washes on cream paper", italic=True),
    "watercolor-sunrise": _look("watercolor", "sunrise", 73, "dark", "#3a1f2a", "#a8431f", (250, 760), "center", "caladea",
                                "soft coral, gold and pink watercolor washes on cream paper"),
    "watercolor-meadow": _look("watercolor", "meadow", 75, "dark", "#1f2f1c", "#8a4a1f", (250, 760), "center", "charter",
                               "soft green and gold watercolor washes on cream paper"),
    # lake reflections
    "lake-dawn": _look("lake", "dawn", 81, "dark", "#2a2340", "#a8431f", (110, 520), "left", "baskerville",
                       "pale mountains reflected in a still lake at dawn", brand="#fff4ea", brand_op=0.85),
    "lake-twilight": _look("lake", "twilight", 83, "light", "#f6f0ff", "#ffd7a0", (110, 520), "left", "charter",
                           "dark mountains reflected in a still lake at twilight"),
    # simple graphic
    "boho-terracotta": _look("boho", "terracotta", 91, "dark", "#3a2519", "#a8431f", (90, 620), "center", "caladea",
                             "warm terracotta and gold arches on cream", brand="#6b4a2b", brand_op=0.8),
    "boho-navy": _look("boho", "navy", 93, "light", "#f6f0e0", "#e6c277", (90, 620), "center", "baskerville",
                       "gold and blue arches on deep navy"),
}


def build_scene(look_id, variant=0):
    look = LOOKS[look_id]
    pal = PAL[look["scene"]][look["pal"]]
    return SCENES[look["scene"]](look["seed"] + 1000 * variant, pal)
