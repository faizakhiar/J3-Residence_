"""Stitch real satellite + road-overlay tiles into two portrait map plates and
write pin pixel positions (Web Mercator) for the location scene.

    python3 -I tools/make_map.py <tile-cache-dir>
Imagery: Esri World Imagery + World Transportation reference layer.
"""
import json, math, os, sys, time, urllib.request, io
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = sys.argv[1]
UA = {"User-Agent": "video-map-builder/1.0"}
LAYERS = {
    "img": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "road": "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}",
}
SITE = (2.8740625, 101.7094375)          # plus code VPF5+JQ (Google Maps link)
PLACES = {                               # OpenStreetMap / Nominatim
    "putrajaya": (2.9384381, 101.6922300), "cyberjaya": (2.9338908, 101.6455587),
    "bangi": (2.9540793, 101.7810018), "klia": (2.7479778, 101.7132225),
    "sra": (2.885102, 101.7212359), "skj": (2.8690613, 101.7319394),
}

def px(lat, lon, z):
    n = 256 * 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y

def tile(layer, z, x, y):
    p = os.path.join(CACHE, f"{layer}_{z}_{x}_{y}.png")
    if not os.path.exists(p):
        for k in range(4):
            try:
                req = urllib.request.Request(LAYERS[layer].format(z=z, x=x, y=y), headers=UA)
                data = urllib.request.urlopen(req, timeout=30).read(); break
            except Exception as e:
                time.sleep(1 + k)
        else:
            raise SystemExit(f"tile failed {layer} {z} {x} {y}")
        Image.open(io.BytesIO(data)).convert("RGBA").save(p)
    return Image.open(p).convert("RGBA")

def plate(name, z, W, H, ax, ay):
    """Image W x H at zoom z with the site at pixel (ax, ay)."""
    sx, sy = px(*SITE, z)
    x0, y0 = int(round(sx - ax)), int(round(sy - ay))
    out = Image.new("RGBA", (W, H))
    for tx in range(x0 // 256, (x0 + W) // 256 + 1):
        for ty in range(y0 // 256, (y0 + H) // 256 + 1):
            base = tile("img", z, tx, ty)
            base.alpha_composite(tile("road", z, tx, ty))
            out.paste(base, (tx * 256 - x0, ty * 256 - y0))
    out.convert("RGB").save(os.path.join(ROOT, "assets/img", f"map_{name}.jpg"), quality=88)
    pins = {k: [round(px(*v, z)[0] - x0, 1), round(px(*v, z)[1] - y0, 1)] for k, v in {"site": SITE, **PLACES}.items()}
    return dict(z=z, w=W, h=H, pins=pins)

os.makedirs(CACHE, exist_ok=True)
meta = {
    # both plates put the site on the same screen point (400, 950) so the zoom-out is continuous
    "close": plate("close", 15, 1240, 2120, 460, 1040),
    "wide": plate("wide", 13, 1300, 2200, 510, 1090),
}
json.dump(meta, open(os.path.join(ROOT, "tools/map_meta.json"), "w"), indent=1)
for k, m in meta.items():
    print(k, m["z"], {p: v for p, v in m["pins"].items() if 0 <= v[0] <= m["w"] and 0 <= v[1] <= m["h"]})
