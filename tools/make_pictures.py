#!/usr/bin/env python3
"""Verse pictures for Scan The Good News: 1080 x 1350 JPEG (4:5) with the KJV verse set in type.

Run it with python3 -I (isolated mode) from the repo root:

  python3 -I tools/make_pictures.py looks  [--log data/posts-log.json]
  python3 -I tools/make_pictures.py render SPEC.json OUT_DIR --verses VERSES.json [--log data/posts-log.json]
  python3 -I tools/make_pictures.py demo   OUT_DIR [--text "..." --ref "Isaiah 41:10"] [--only id,id] [--variant N]

SPEC.json is a list like
  [{"date": "2026-10-22", "ref": "John 3:16", "look": "dunes-sunset", "variant": 0}]
The file is named <date>-<reference>.jpg (for example 2026-10-22-john-3-16.jpg); "slug" can be given instead of "date".
`variant` is optional. The verse text always comes from VERSES.json (written by get_verses.py), never from the spec.

Every picture is checked before it is saved:
  * the verse must fit its text zone at 46 px or larger
  * the text must keep a WCAG contrast of 4.5 (verse) and 3.0 (reference) against the picture behind it
    (a soft scrim is added behind the text if a scene is too busy; the scrim is reported)
  * no look is reused within 20 posts and no scene family repeats within 2 posts (checked against the log)

Output: OUT_DIR/<slug>.jpg, OUT_DIR/manifest.json and OUT_DIR/_contact-sheet.png.
Exit status 0 = every picture passed, 2 = at least one problem (details are in the JSON printed on stdout).
"""
import argparse
import hashlib
import html
import io
import json
import pathlib
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import looks as L  # noqa: E402

W, H = L.W, L.H
MIN_FONT = 46
MIN_CONTRAST_VERSE = 4.5
MIN_CONTRAST_REF = 3.0
SCRIMS = (0.0, 0.2, 0.32, 0.44, 0.56, 0.68)
RECENT_LOOKS = 20
RECENT_SCENES = 2
DEMO_REF = "Isaiah 41:10"
DEMO_TEXT = ("Fear thou not; for I am with thee: be not dismayed; for I am thy God: I will strengthen thee; "
             "yea, I will help thee; yea, I will uphold thee with the right hand of my righteousness.")
CAPACITY_TEXT = ("Fear thou not for I am with thee be not dismayed for I am thy God I will strengthen thee yea I will help thee "
                 "yea I will uphold thee with the right hand of my righteousness But God commendeth his love toward us in that "
                 "while we were yet sinners Christ died for us Thy word is a lamp unto my feet and a light unto my path "
                 "Be ye doers of the word and not hearers only deceiving your own selves").split()

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;padding:0;background:#000}
.pic{position:relative;width:1080px;height:1350px;overflow:hidden}
.pic>svg.bg{position:absolute;left:0;top:0}
.vig{position:absolute;inset:0;background:__VIG__}
svg.grain{position:absolute;left:0;top:0;opacity:__GOP__;mix-blend-mode:overlay}
.scrim{position:absolute;left:0;top:0;width:0;height:0;border-radius:90px;filter:blur(46px);opacity:0}
.zone{position:absolute;left:112px;right:112px;top:__ZT__px;height:__ZH__px;display:flex;flex-direction:column;
  justify-content:center;text-align:__ALIGN__;color:__COLOR__;align-items:__ITEMS__}
.verse{font-family:__FAMILY__;font-style:__STYLE__;font-weight:400;line-height:1.28;letter-spacing:-0.003em;text-wrap:balance;
  text-shadow:__SHADOW__}
.rule{width:76px;height:4px;border-radius:2px;background:__ACCENT__;margin:46px 0 30px;flex:none}
.ref{font-family:'Inter','DejaVu Sans',sans-serif;font-weight:600;font-size:27px;letter-spacing:0.24em;text-transform:uppercase;
  color:__ACCENT__;text-shadow:__RSH__}
.brand{position:absolute;left:0;right:0;bottom:__BB__px;text-align:center;font-family:'Inter','DejaVu Sans',sans-serif;font-weight:500;
  font-size:22px;letter-spacing:0.08em;color:__BC__;opacity:__BO__}
</style></head><body>
<div class="pic">
<svg class="bg" width="1080" height="1350" viewBox="0 0 1080 1350" xmlns="http://www.w3.org/2000/svg">__SCENE__</svg>
<div class="vig"></div>
<svg class="grain" width="1080" height="1350" viewBox="0 0 1080 1350" xmlns="http://www.w3.org/2000/svg">
<filter id="gr" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" seed="4"/>
<feColorMatrix type="matrix" values="0 0 0 0 __GR__ 0 0 0 0 __GG__ 0 0 0 0 __GB__ 1.1 0 0 0 -0.3"/></filter>
<rect width="1080" height="1350" filter="url(#gr)"/></svg>
<div class="scrim" id="scrim"></div>
<div class="zone" id="zone"><div class="verse" id="v">__VERSE__</div><div class="rule"></div><div class="ref" id="ref">__REF__ &middot; KJV</div></div>
<div class="brand">scanthegoodnews.com</div>
</div>
<script>
function fit(start, min){
  const zone=document.getElementById('zone'), v=document.getElementById('v');
  let s=start; v.style.fontSize=s+'px';
  while(zone.scrollHeight>zone.clientHeight+1 && s>min){ s-=2; v.style.fontSize=s+'px'; }
  return [s, zone.scrollHeight>zone.clientHeight+1];
}
function setVerse(t){ document.getElementById('v').textContent=t; }
function lineRects(){
  const out={verse:[], ref:[]};
  const pairs=[['verse', document.getElementById('v')], ['ref', document.getElementById('ref')]];
  for(const [k, el] of pairs){
    const w=document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n;
    while((n=w.nextNode())){
      const r=document.createRange(); r.selectNodeContents(n);
      for(const q of r.getClientRects()){ if(q.width>1 && q.height>1) out[k].push([q.left, q.top, q.width, q.height]); }
    }
  }
  return out;
}
function setScrim(l,t,w,h,rgb,a){
  const s=document.getElementById('scrim');
  s.style.left=l+'px'; s.style.top=t+'px'; s.style.width=w+'px'; s.style.height=h+'px';
  s.style.background='rgba('+rgb+','+a+')'; s.style.opacity=a>0?1:0;
}
function showText(on){ document.getElementById('zone').style.visibility=on?'visible':'hidden'; }
</script></body></html>"""


class PictureError(Exception):
    pass


# --------------------------------------------------------------------------- helpers
def clean_end(t):
    t = re.sub(r"\s+", " ", t).strip()
    return t[:-1] + "." if t and t[-1] in ":;," else t


def lum_map(rgb):
    c = rgb.astype(np.float32) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def hex_lum(h):
    h = h.lstrip("#")
    arr = np.array([[[int(h[i:i + 2], 16) for i in (0, 2, 4)]]], dtype=np.uint8)
    return float(lum_map(arr)[0, 0])


def worst_contrast(Y, rects, ink_lum, mode):
    """Lowest contrast ratio over the given text line boxes. Light text is judged against the brightest 10% of the
    picture behind each line, dark text against the darkest 10%, so a single bright or dark patch counts."""
    worst = 99.0
    for x, y, w, h in rects:
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(W, int(x + w) + 1), min(H, int(y + h) + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        crop = Y[y0:y1, x0:x1]
        if mode == "light":
            ratio = (ink_lum + 0.05) / (float(np.percentile(crop, 90)) + 0.05)
        else:
            ratio = (float(np.percentile(crop, 10)) + 0.05) / (ink_lum + 0.05)
        worst = min(worst, ratio)
    return worst


def fonts_report():
    out = {}
    for name in ("Bitstream Charter", "Caladea", "Lora", "GFS Baskerville", "Inter"):
        try:
            fam = subprocess.run(["fc-match", "-f", "%{family}", name], capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception as e:  # fc-match missing
            fam = f"unknown ({e.__class__.__name__})"
        out[name] = fam
    return out


def fill_template(look, scene_svg, text, ref):
    mode = look["mode"]
    gr = L.GRAIN[mode]
    rgb = [float(x) for x in gr[0].split(",")]
    shadow = "0 2px 22px rgba(0,0,0,0.38)" if mode == "light" else "none"
    rshadow = "0 1px 12px rgba(0,0,0,0.45)" if mode == "light" else "none"
    reps = {
        "__VIG__": L.VIGNETTE[mode], "__GOP__": str(gr[1]), "__ZT__": str(look["zone"][0]), "__ZH__": str(look["zone"][1]),
        "__BB__": str(look["brand_bottom"]), "__BC__": look["brand"], "__BO__": str(look["brand_op"]), "__RSH__": rshadow,
        "__ALIGN__": look["align"], "__ITEMS__": "center" if look["align"] == "center" else "flex-start",
        "__COLOR__": look["ink"], "__ACCENT__": look["accent"], "__FAMILY__": L.FONTS[look["font"]],
        "__STYLE__": "italic" if look["italic"] else "normal", "__SHADOW__": shadow,
        "__GR__": str(rgb[0]), "__GG__": str(rgb[1]), "__GB__": str(rgb[2]),
    }
    doc = TEMPLATE
    for k, v in reps.items():
        doc = doc.replace(k, v)
    # verse, reference and scene last, so their text can never be mistaken for a placeholder
    return doc.replace("__SCENE__", scene_svg).replace("__VERSE__", html.escape(text)).replace("__REF__", html.escape(ref))


def alt_text(ref, text, look):
    tone = "White" if look["mode"] == "light" else "Dark"
    return f"{ref} (KJV): {text} {tone} text on {look['alt']}."


class Browser:
    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch()
        except Exception as e:  # fall back to the pre-installed build
            print("default chromium launch failed, using /opt/pw-browsers/chromium:", str(e)[:120], file=sys.stderr)
            self._browser = self._pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        self.page = self._browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        return self.page

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()


def shot(page):
    return Image.open(io.BytesIO(page.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H}))).convert("RGB")


# --------------------------------------------------------------------------- rendering
def render_one(page, look_id, variant, ref, verse):
    """Render one picture. Returns (PIL image, info dict). Raises PictureError when it cannot be made good."""
    look = L.LOOKS[look_id]
    text = clean_end(verse)
    words = len(text.split())
    start = 88 if words <= 16 else 76 if words <= 26 else 64
    page.set_content(fill_template(look, L.build_scene(look_id, variant), text, ref))
    page.evaluate("document.fonts.ready.then(() => true)")
    size, overflow = page.evaluate(f"fit({start}, {MIN_FONT})")
    if overflow:
        raise PictureError(f"fit: {words} words do not fit the text zone of {look_id} at {MIN_FONT}px; choose a look with more room")
    rects = page.evaluate("lineRects()")
    if not rects["verse"] or not rects["ref"]:
        raise PictureError("layout: could not measure the text lines")
    ink, acc = hex_lum(look["ink"]), hex_lum(look["accent"])
    xs = [r[0] for k in rects.values() for r in k]
    ys = [r[1] for k in rects.values() for r in k]
    xe = [r[0] + r[2] for k in rects.values() for r in k]
    ye = [r[1] + r[3] for k in rects.values() for r in k]
    box = (min(xs) - 80, min(ys) - 70, max(xe) - min(xs) + 160, max(ye) - min(ys) + 140)
    scrim_rgb = "4,6,20" if look["mode"] == "light" else "255,252,244"
    page.evaluate("showText(false)")
    cv = cr = 0.0
    used = 0.0
    for a in SCRIMS:
        if a:
            page.evaluate(f"setScrim({box[0]},{box[1]},{box[2]},{box[3]},'{scrim_rgb}',{a})")
        Y = lum_map(np.array(shot(page)))
        cv = worst_contrast(Y, rects["verse"], ink, look["mode"])
        cr = worst_contrast(Y, rects["ref"], acc, look["mode"])
        used = a
        if cv >= MIN_CONTRAST_VERSE and cr >= MIN_CONTRAST_REF:
            break
    page.evaluate("showText(true)")
    info = dict(look=look_id, variant=variant, font_px=size, words=words, scrim=used,
                contrast_verse=round(cv, 2), contrast_ref=round(cr, 2), text=text,
                alt=alt_text(ref, text, look), lines=len(rects["verse"]))
    if cv < MIN_CONTRAST_VERSE or cr < MIN_CONTRAST_REF:
        info["problem"] = f"contrast: verse {cv:.2f} (needs {MIN_CONTRAST_VERSE}), reference {cr:.2f} (needs {MIN_CONTRAST_REF}) even with a scrim; choose another look"
        return shot(page), info
    return shot(page), info


def save_jpeg(img, path):
    img.save(path, "JPEG", quality=94, subsampling=0, optimize=True)


def contact_sheet(items, path, cols=4, tw=380, th=475, gap=16, label_h=30):
    font = None
    for cand in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        try:
            font = ImageFont.truetype(cand, 15)
            break
        except Exception:
            pass
    font = font or ImageFont.load_default()
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * (th + label_h) + (rows + 1) * gap), (243, 244, 246))
    d = ImageDraw.Draw(sheet)
    for i, (label, img_path) in enumerate(items):
        r, c = divmod(i, cols)
        x, y = gap + c * (tw + gap), gap + r * (th + label_h + gap)
        sheet.paste(Image.open(img_path).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 2, y + th + 6), label, fill=(40, 40, 50), font=font)
    sheet.save(path)


def ref_slug(ref):
    return re.sub(r"[^a-z0-9]+", "-", norm_ref(ref)).strip("-")


def norm_ref(ref):
    return re.sub(r"\s+", " ", str(ref).strip().lower()).replace("psalms ", "psalm ")


def load_log(path):
    p = pathlib.Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    posts = [x for x in data.get("posts", []) if x.get("status") != "removed"]
    return sorted(posts, key=lambda x: (x.get("date", ""), x.get("time", "")))


def variety_problems(spec, log):
    problems = []
    seq = [x["look"] for x in log if x.get("look") in L.LOOKS]
    for item in spec:
        lid = item["look"]
        scene = L.LOOKS[lid]["scene"]
        if lid in seq[-RECENT_LOOKS:]:
            problems.append(dict(slug=item["slug"], problem=f"variety: look {lid} was used within the last {RECENT_LOOKS} posts"))
        if scene in [L.LOOKS[s]["scene"] for s in seq[-RECENT_SCENES:]]:
            problems.append(dict(slug=item["slug"], problem=f"variety: scene family '{scene}' was used within the last {RECENT_SCENES} posts"))
        seq.append(lid)
    return problems


# --------------------------------------------------------------------------- commands
def capacity_by_look(page):
    """Most words each look's text zone can hold at the minimum font size."""
    out = {}
    for lid, look in L.LOOKS.items():
        page.set_content(fill_template(look, "", "x", "Ref 1:1"))
        page.evaluate("document.fonts.ready.then(() => true)")
        lo, hi = 5, len(CAPACITY_TEXT)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            page.evaluate("t => setVerse(t)", " ".join(CAPACITY_TEXT[:mid]))
            start = 88 if mid <= 16 else 76 if mid <= 26 else 64
            _, over = page.evaluate(f"fit({start}, {MIN_FONT})")
            if over:
                hi = mid - 1
            else:
                lo = mid
        out[lid] = lo
    return out


def cmd_looks(args):
    log = load_log(args.log)
    last = {}
    for x in log:
        last[x["look"]] = x
    with Browser() as page:
        cap = capacity_by_look(page)
    print(f"{'look':<22} {'scene':<10} {'text':<5} {'font':<11} {'max words':>9}  last used")
    for lid, look in L.LOOKS.items():
        u = last.get(lid)
        used = f"{u['date']} ({u['ref']})" if u else "never"
        print(f"{lid:<22} {look['scene']:<10} {look['mode']:<5} {look['font']:<11} {cap[lid]:>9}  {used}   | {look['alt']}")
    print(f"\nrules: a look is not reused within {RECENT_LOOKS} posts; a scene family does not repeat within {RECENT_SCENES} posts")
    print("fonts:", json.dumps(fonts_report()))
    return 0


def cmd_render(args):
    spec = json.loads(pathlib.Path(args.spec).read_text(encoding="utf-8"))
    verses = {norm_ref(k): v for k, v in json.loads(pathlib.Path(args.verses).read_text(encoding="utf-8")).items()}
    log = load_log(args.log)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    problems = []
    for item in spec:
        if not item.get("slug") and item.get("date") and item.get("ref"):
            item["slug"] = f"{item['date']}-{ref_slug(item['ref'])}"
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", item.get("slug", "")):
            problems.append(dict(slug=item.get("slug"), problem="slug must be lowercase letters, digits and hyphens"))
        if item.get("look") not in L.LOOKS:
            problems.append(dict(slug=item.get("slug"), problem=f"unknown look {item.get('look')!r}; run the looks command"))
        if norm_ref(item.get("ref", "")) not in verses:
            problems.append(dict(slug=item.get("slug"), problem=f"no verse text for {item.get('ref')!r} in {args.verses}"))
    if problems:
        print(json.dumps(dict(ok=False, problems=problems), indent=2))
        return 2
    if not args.no_variety_check:
        problems += variety_problems(spec, log)
    uses = {}
    for x in log:
        uses[x["look"]] = uses.get(x["look"], 0) + 1
    manifest = []
    with Browser() as page:
        for item in spec:
            lid = item["look"]
            variant = item.get("variant")
            if variant is None:
                variant = uses.get(lid, 0)
            uses[lid] = uses.get(lid, 0) + 1
            ref = item["ref"]
            try:
                img, info = render_one(page, lid, variant, ref, verses[norm_ref(ref)])
            except PictureError as e:
                problems.append(dict(slug=item["slug"], problem=str(e)))
                continue
            if "problem" in info:
                problems.append(dict(slug=item["slug"], problem=info.pop("problem")))
            path = out / f"{item['slug']}.jpg"
            save_jpeg(img, path)
            info.update(slug=item["slug"], ref=ref, file=path.name, bytes=path.stat().st_size,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            manifest.append(info)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    if manifest:
        contact_sheet([(f"{m['slug']}  {m['look']} {m['font_px']}px", out / m["file"]) for m in manifest], out / "_contact-sheet.png",
                      cols=min(3, len(manifest)), tw=360, th=450)
    print(json.dumps(dict(ok=not problems, problems=problems, pictures=[{k: m[k] for k in (
        "slug", "ref", "look", "variant", "font_px", "words", "lines", "scrim", "contrast_verse", "contrast_ref", "file", "bytes")} for m in manifest],
        fonts=fonts_report()), indent=2))
    return 0 if not problems else 2


def cmd_demo(args):
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ids = [x for x in args.only.split(",")] if args.only else list(L.LOOKS)
    bad = [x for x in ids if x not in L.LOOKS]
    if bad:
        print("unknown looks:", bad)
        return 2
    text = args.text or DEMO_TEXT
    ref = args.ref or DEMO_REF
    rows, items = [], []
    with Browser() as page:
        for lid in ids:
            try:
                img, info = render_one(page, lid, args.variant, ref, text)
            except PictureError as e:
                rows.append((lid, "FAIL", str(e)))
                continue
            path = out / f"demo-{lid}.jpg"
            save_jpeg(img, path)
            items.append((f"{lid} {info['font_px']}px v{info['contrast_verse']} r{info['contrast_ref']}" + (f" scrim{info['scrim']}" if info["scrim"] else ""), path))
            rows.append((lid, "ok" if "problem" not in info else "WEAK", f"{info['font_px']}px, {info['lines']} lines, verse {info['contrast_verse']}, ref {info['contrast_ref']}, scrim {info['scrim']}"
                         + (f"  <-- {info['problem']}" if "problem" in info else "")))
    for r in rows:
        print(f"{r[0]:<22} {r[1]:<5} {r[2]}")
    for n in range(0, len(items), 8):
        contact_sheet(items[n:n + 8], out / f"_demo-sheet-{n // 8 + 1}.png")
    return 0 if all(r[1] == "ok" for r in rows) else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    default_log = str(HERE.parent / "data" / "posts-log.json")
    p = sub.add_parser("looks")
    p.add_argument("--log", default=default_log)
    p.set_defaults(fn=cmd_looks)
    p = sub.add_parser("render")
    p.add_argument("spec")
    p.add_argument("out")
    p.add_argument("--verses", required=True)
    p.add_argument("--log", default=default_log)
    p.add_argument("--no-variety-check", action="store_true")
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("demo")
    p.add_argument("out")
    p.add_argument("--text")
    p.add_argument("--ref")
    p.add_argument("--only")
    p.add_argument("--variant", type=int, default=0)
    p.set_defaults(fn=cmd_demo)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
