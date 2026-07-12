#!/usr/bin/env python3
"""
fetch_images.py (v2) — real product images for the SamCity catalog.

WHY THIS IS A SCRIPT AND NOT A FINISHED ZIP
-------------------------------------------
The environment that generated the catalog has no outbound internet access
(every image host returns 403 host_not_allowed). Downloading is therefore
impossible there. This script does the download on YOUR machine, which has
internet, and produces exactly the two requested artifacts:

    catalog_images.zip     real WEBP product photos, keyed to existing image_path
    missing_images.json    every product for which no acceptable image was found

It NEVER writes a placeholder card. A product either gets a real photo that
passes the quality gates, or it is reported as missing. That is requirement #9.

QUICK START
-----------
    pip install requests pillow

    # optional but STRONGLY recommended - much better packshots, free keys:
    export PEXELS_API_KEY=...          # https://www.pexels.com/api/
    export UNSPLASH_ACCESS_KEY=...     # https://unsplash.com/developers

    python fetch_images.py                       # full run, priority-ordered
    python fetch_images.py --only coca-cola-1l   # single product
    python fetch_images.py --report-only         # re-check + rebuild report/zip
    python fetch_images.py --loose               # relax gates for a 2nd pass

QUALITY GATES (requirement #6)
------------------------------
    * >= 500x500 source resolution (configurable, --min-res)
    * not a logo/SVG/GIF; must be a real raster photo
    * aspect ratio within 1:2.5 (rejects banners and label strips)
    * background cleanliness score from border-pixel sampling (white preferred)
    * subject occupies a sane share of the frame (rejects zoomed-out shelf shots)
    * known watermark-heavy stock hosts are blocked outright
    * best-of-N: every candidate is scored, the highest scorer wins

MANUAL OVERRIDES (requirement #10 escape hatch)
----------------------------------------------
Anything the crawler cannot find, put in image_overrides.json and re-run:

    { "kazi-horse-sausage-300g": "https://example.com/kazi.jpg" }

Overrides skip search and go straight to download (gates still apply unless
--force). This is how you close out the last mile after the first pass.

LICENSING - READ THIS
---------------------
Wikimedia Commons / Openverse results are freely licensed but attribution is
often required. Pexels/Unsplash are free for commercial use. NONE of them
guarantee the correct SKU packaging. For a production marketplace the correct
source is supplier/manufacturer photography or your own studio shots -
scraping brand-owned packshots off retailer sites is a trademark/copyright
risk you should clear with counsel first.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from PIL import Image
except ImportError:
    sys.exit("Missing deps. Run:  pip install requests pillow")

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "catalog_150_products.json")
OVERRIDES = os.path.join(HERE, "image_overrides.json")
IMG_DIR = os.path.join(HERE, "catalog")
ZIP_PATH = os.path.join(HERE, "catalog_images.zip")
REPORT = os.path.join(HERE, "missing_images.json")

UA = {"User-Agent": "SamCity-Catalog/2.0 (contact: dev@samcity.uz)"}
TIMEOUT = 25

# Hosts that stamp watermarks on preview images - never download from these.
WATERMARK_HOSTS = (
    "shutterstock", "istockphoto", "gettyimages", "alamy", "dreamstime",
    "123rf", "depositphotos", "adobestock", "stock.adobe", "canstockphoto",
    "vectorstock", "bigstockphoto",
)

# ---------------------------------------------------------------------------
# Priority (requirement #7). Products are processed in this order, so if you
# interrupt the run or burn an API quota, the important SKUs are already done.
# ---------------------------------------------------------------------------
PRIORITY_PATTERNS = [
    r"coca-cola", r"^pepsi", r"^fanta", r"^sprite",
    r"milk|kefir|qatiq|ayran|suzma|yogurt|butter|cheese|sour-cream|eggs",
    r"non|bread|lavash",
    r"tea",
    r"coffee|nescafe|jacobs",
    r"oil",
    r"rice|devzira|lazer",
    r"pasta|spaghetti|vermicelli|noodles|makfa",
]


def priority_rank(slug: str) -> int:
    for i, pat in enumerate(PRIORITY_PATTERNS):
        if re.search(pat, slug):
            return i
    return len(PRIORITY_PATTERNS)  # "common supermarket items" - everything else


# ---------------------------------------------------------------------------
# Query construction
# ---------------------------------------------------------------------------
GENERIC_BRANDS = {"SamCity", "Local Farm", "Local Bakery"}
SIZE_RE = re.compile(r"\b\d+(\.\d+)?\s?(l|ml|g|kg|pcs|m)\b", re.I)

# Nudges the search toward a packshot rather than a lifestyle photo.
FORM_HINTS = {
    "bottle": "bottle", "can": "can", "jar": "jar", "box": "carton pack",
    "pack": "package", "bag": "bag", "bar": "bar", "tube": "tube",
    "tray": "pack", "loaf": "loaf", "piece": "", "kg": "", "bunch": "",
    "roll": "roll",
}


def build_queries(p: dict) -> list[str]:
    """Ordered list of progressively looser queries."""
    name = SIZE_RE.sub("", p["name"]).replace("%", "").strip(" -")
    brand = p["brand"]
    generic = brand in GENERIC_BRANDS
    form = FORM_HINTS.get(p["unit"], "")

    qs = []
    if not generic:
        qs.append(f"{brand} {name} {form} product".strip())
        qs.append(f"{brand} {name}".strip())
        qs.append(f"{brand} {p['subcategory']}")  # req #10: same brand + category
    qs.append(f"{name} {form} white background".strip())
    qs.append(f"{name} {p['subcategory']}".strip())
    qs.append(name)
    # dedupe, preserve order
    seen, out = set(), []
    for q in qs:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out


# ---------------------------------------------------------------------------
# Sources. Each returns a list of candidate dicts: {url, title, w, h, source}
# ---------------------------------------------------------------------------
def src_commons(q: str, n: int) -> list[dict]:
    r = requests.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query", "generator": "search", "gsrsearch": f"filetype:bitmap {q}",
            "gsrnamespace": 6, "gsrlimit": n, "prop": "imageinfo",
            "iiprop": "url|size|mime", "format": "json",
        },
        headers=UA, timeout=TIMEOUT,
    )
    out = []
    for page in (r.json().get("query", {}).get("pages", {}) or {}).values():
        ii = (page.get("imageinfo") or [{}])[0]
        if ii.get("mime", "").startswith("image/") and "svg" not in ii.get("mime", ""):
            out.append({"url": ii["url"], "title": page.get("title", ""),
                        "w": ii.get("width", 0), "h": ii.get("height", 0), "source": "commons"})
    return out


def src_openverse(q: str, n: int) -> list[dict]:
    r = requests.get(
        "https://api.openverse.org/v1/images/",
        params={"q": q, "page_size": n, "license_type": "commercial", "mature": "false"},
        headers=UA, timeout=TIMEOUT,
    )
    return [
        {"url": i["url"], "title": i.get("title", ""), "w": i.get("width", 0),
         "h": i.get("height", 0), "source": "openverse"}
        for i in r.json().get("results", []) if i.get("url")
    ]


def src_pexels(q: str, n: int) -> list[dict]:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    r = requests.get(
        "https://api.pexels.com/v1/search",
        params={"query": q, "per_page": n},
        headers={"Authorization": key, **UA}, timeout=TIMEOUT,
    )
    return [
        {"url": p["src"].get("large2x") or p["src"]["large"], "title": p.get("alt", ""),
         "w": p.get("width", 0), "h": p.get("height", 0), "source": "pexels"}
        for p in r.json().get("photos", [])
    ]


def src_unsplash(q: str, n: int) -> list[dict]:
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        return []
    r = requests.get(
        "https://api.unsplash.com/search/photos",
        params={"query": q, "per_page": n},
        headers={"Authorization": f"Client-ID {key}", **UA}, timeout=TIMEOUT,
    )
    return [
        {"url": p["urls"]["regular"], "title": p.get("alt_description") or "",
         "w": p.get("width", 0), "h": p.get("height", 0), "source": "unsplash"}
        for p in r.json().get("results", [])
    ]


SOURCES = {"pexels": src_pexels, "commons": src_commons,
           "openverse": src_openverse, "unsplash": src_unsplash}
DEFAULT_ORDER = ["pexels", "commons", "openverse", "unsplash"]


# ---------------------------------------------------------------------------
# Image quality assessment
# ---------------------------------------------------------------------------
def bg_whiteness(im: Image.Image) -> float:
    """Fraction of border pixels that are near-white. 1.0 = perfect packshot."""
    small = im.convert("RGB").resize((64, 64))
    px = small.load()
    border, white = 0, 0
    for x in range(64):
        for y in (0, 1, 62, 63):
            for cx, cy in ((x, y), (y, x)):
                r, g, b = px[cx, cy]
                border += 1
                if r > 235 and g > 235 and b > 235:
                    white += 1
    return white / max(border, 1)


def subject_fill(im: Image.Image) -> float:
    """Rough share of frame occupied by non-background content."""
    small = im.convert("L").resize((64, 64))
    px = small.load()
    dark = sum(1 for x in range(64) for y in range(64) if px[x, y] < 230)
    return dark / 4096.0


def score_candidate(im: Image.Image, cand: dict, tokens: set[str], args) -> tuple[float, str]:
    w, h = im.size
    if min(w, h) < args.min_res:
        return -1, f"resolution {w}x{h} < {args.min_res}"
    ar = max(w, h) / min(w, h)
    if ar > args.max_aspect:
        return -1, f"aspect ratio {ar:.1f} too extreme"

    white = bg_whiteness(im)
    fill = subject_fill(im)
    if fill < 0.02:
        return -1, "frame is essentially empty"
    if fill > 0.97 and white < 0.05:
        return -1, "no discernible background (likely a crop/texture)"

    title = (cand.get("title") or "").lower()
    hits = sum(1 for t in tokens if t in title)

    score = 0.0
    score += min(min(w, h) / 1000.0, 1.5)      # resolution, capped
    score += white * 3.0                        # clean background - weighted heavily
    score += 1.5 if 0.10 <= fill <= 0.80 else 0 # well-framed subject
    score += 0.5 * hits                         # title relevance
    score += {"pexels": 0.6, "unsplash": 0.5, "commons": 0.3, "openverse": 0.0}.get(
        cand["source"], 0)
    score -= 1.0 if ar > 1.6 else 0
    return score, ""


def to_webp(im: Image.Image, dest: str, size: int, quality: int) -> None:
    """Contain on a white canvas - never crops the product out of frame."""
    im = im.convert("RGB")
    im.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGB", (size, size), (255, 255, 255))
    canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2))
    canvas.save(dest, "WEBP", quality=quality, method=6)


# ---------------------------------------------------------------------------
# Per-product worker
# ---------------------------------------------------------------------------
def download(url: str) -> Image.Image:
    if any(h in url.lower() for h in WATERMARK_HOSTS):
        raise ValueError("watermarked stock host - blocked")
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    if not r.headers.get("Content-Type", "").startswith("image/"):
        raise ValueError("not an image response")
    return Image.open(io.BytesIO(r.content))


def process(p: dict, overrides: dict, order: list[str], args) -> dict:
    slug = os.path.splitext(os.path.basename(p["image_path"]))[0]
    dest = os.path.join(IMG_DIR, f"{slug}.webp")

    if args.resume and os.path.exists(dest):
        return {"slug": slug, "ok": True, "source": "existing", "score": None}

    tokens = {t for t in re.split(r"\W+", p["name"].lower()) if len(t) > 2}
    tried, rejected = [], []

    # 1) manual override wins outright
    if slug in overrides:
        try:
            im = download(overrides[slug])
            if not args.force:
                s, why = score_candidate(im, {"title": p["name"], "source": "override"}, tokens, args)
                if s < 0:
                    raise ValueError(f"override rejected: {why}")
            to_webp(im, dest, args.size, args.quality)
            return {"slug": slug, "ok": True, "source": "override", "score": None}
        except Exception as exc:
            rejected.append({"url": overrides[slug], "reason": f"override failed: {exc}"})

    # 2) source cascade x query cascade, keep the best-scoring candidate
    best = (None, -1, None)  # (image, score, cand)
    for query in build_queries(p):
        for src_name in order:
            try:
                cands = SOURCES[src_name](query, args.candidates)
            except Exception as exc:
                rejected.append({"query": query, "source": src_name, "reason": f"search error: {exc}"})
                continue
            tried.append({"query": query, "source": src_name, "candidates": len(cands)})
            for c in cands:
                if c["w"] and c["h"] and min(c["w"], c["h"]) < args.min_res:
                    continue  # cheap pre-filter before spending a download
                try:
                    im = download(c["url"])
                except Exception as exc:
                    rejected.append({"url": c["url"], "reason": str(exc)[:120]})
                    continue
                s, why = score_candidate(im, c, tokens, args)
                if s < 0:
                    rejected.append({"url": c["url"], "reason": why})
                    continue
                if s > best[1]:
                    best = (im, s, c)
                if best[1] >= args.good_enough:
                    break
            if best[1] >= args.good_enough:
                break
        if best[1] >= args.min_score:
            break
        time.sleep(0.2)

    if best[0] is not None and best[1] >= args.min_score:
        to_webp(best[0], dest, args.size, args.quality)
        return {"slug": slug, "ok": True, "source": best[2]["source"],
                "url": best[2]["url"], "score": round(best[1], 2)}

    return {
        "slug": slug, "ok": False,
        "best_score": round(best[1], 2) if best[1] > -1 else None,
        "min_score": args.min_score,
        "queries_tried": [t["query"] for t in tried][:6],
        "rejected": rejected[:6],
    }


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=",".join(DEFAULT_ORDER))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--size", type=int, default=800)
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--min-res", type=int, default=500, help="requirement #6")
    ap.add_argument("--max-aspect", type=float, default=2.5)
    ap.add_argument("--candidates", type=int, default=6)
    ap.add_argument("--min-score", type=float, default=2.2, help="accept threshold")
    ap.add_argument("--good-enough", type=float, default=4.0, help="stop searching early")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--resume", action="store_true", help="keep files already on disk")
    ap.add_argument("--force", action="store_true", help="skip gates for overrides")
    ap.add_argument("--loose", action="store_true", help="2nd pass: relax gates")
    ap.add_argument("--report-only", action="store_true", help="no fetching; re-verify + rezip")
    args = ap.parse_args()

    if args.loose:
        args.min_res, args.min_score, args.max_aspect = 400, 1.2, 3.0

    with open(CATALOG, encoding="utf-8") as f:
        catalog = json.load(f)
    products = catalog["products"]

    overrides = {}
    if os.path.exists(OVERRIDES):
        with open(OVERRIDES, encoding="utf-8") as f:
            overrides = json.load(f)
        print(f"loaded {len(overrides)} manual override(s)")

    os.makedirs(IMG_DIR, exist_ok=True)
    order = [s.strip() for s in args.sources.split(",") if s.strip() in SOURCES]

    results = {}
    if not args.report_only:
        todo = [p for p in products
                if not args.only
                or os.path.splitext(os.path.basename(p["image_path"]))[0] in args.only]
        # requirement #7 - priority first
        todo.sort(key=lambda p: (
            priority_rank(os.path.splitext(os.path.basename(p["image_path"]))[0]), p["name"]))

        print(f"fetching {len(todo)} product images via {order} ...\n")
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {pool.submit(process, p, overrides, order, args): p for p in todo}
            for i, fut in enumerate(as_completed(futs), 1):
                r = fut.result()
                results[r["slug"]] = r
                mark = "OK  " if r["ok"] else "MISS"
                extra = f"{r.get('source','-'):<10} score={r.get('score')}" if r["ok"] else ""
                print(f"[{i:3}/{len(todo)}] {mark} {r['slug']:<38} {extra}")

    # ---- verify what is actually on disk (single source of truth) ----------
    missing, present = [], []
    for p in products:
        slug = os.path.splitext(os.path.basename(p["image_path"]))[0]
        path = os.path.join(IMG_DIR, f"{slug}.webp")
        ok = False
        if os.path.exists(path):
            try:
                with Image.open(path) as im:
                    ok = im.format == "WEBP" and min(im.size) >= args.min_res
            except Exception:
                ok = False
        if ok:
            present.append(p)
        else:
            r = results.get(slug, {})
            missing.append({
                "name": p["name"], "slug": slug, "brand": p["brand"],
                "category": p["category"], "subcategory": p["subcategory"],
                "image_path": p["image_path"],
                "reason": "no candidate passed the quality gates" if r
                          else "not fetched (no internet access at build time)",
                "best_score": r.get("best_score"),
                "queries_tried": r.get("queries_tried", []),
                "rejected_samples": r.get("rejected", []),
            })

    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_products": len(products),
            "with_image": len(present),
            "missing_count": len(missing),
            "quality_gates": {
                "min_resolution": f"{args.min_res}x{args.min_res}",
                "max_aspect_ratio": args.max_aspect,
                "min_score": args.min_score,
                "watermarked_hosts_blocked": list(WATERMARK_HOSTS),
            },
            "next_steps": "Add URLs to image_overrides.json for these slugs and re-run.",
            "missing": missing,
        }, f, ensure_ascii=False, indent=2)

    # ---- rebuild the zip from real images only -----------------------------
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        for p in present:
            slug = os.path.splitext(os.path.basename(p["image_path"]))[0]
            z.write(os.path.join(IMG_DIR, f"{slug}.webp"), p["image_path"])

    print(f"\n{'-'*58}")
    print(f"with image : {len(present)}/{len(products)}")
    print(f"missing    : {len(missing)}  -> {os.path.basename(REPORT)}")
    print(f"zip        : {os.path.basename(ZIP_PATH)} ({os.path.getsize(ZIP_PATH)/1024:.0f} KB)")
    if missing:
        print("\nNext: python fetch_images.py --loose --resume")
        print("Then: paste URLs into image_overrides.json and re-run.")


if __name__ == "__main__":
    main()
