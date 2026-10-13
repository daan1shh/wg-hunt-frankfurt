"""Nearest stations and amenities from OpenStreetMap, written into listings/<id>.json.

    python src/amenities.py <id> [<id> ...] [--force]

Geocodes the ad address with Nominatim (1 req/s) and queries Overpass once per listing.
Fills `stations`, `amenities`, `lat`, `lon` and `straight_km` (to the office). Skips listings
that already have `amenities` unless --force. Lines come from OSM route relations, so a
station whose relations are incomplete in OSM may show fewer lines than really stop there.
"""
import json
import math
import re
import subprocess
import sys
import time
import urllib.parse

from common import LISTINGS, load_config

UA = "wg-hunt-frankfurt/0.1 (personal room search)"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
NICHE_GYM = re.compile(r"yoga|pilates|ems\b|physio|reha|tanz|dance|boxing|crossfit|kampfsport", re.I)
NOT_A_PARK = re.compile(r"spielplatz|friedhof$", re.I)


def _get(url, data=None):
    # curl, not urllib: python.org builds on macOS often lack CA certificates
    cmd = ["curl", "-sf", "-m", "150", "-A", UA, url]
    if data:
        cmd[1:1] = ["--data-binary", "@-"]
    r = subprocess.run(cmd, input=data, capture_output=True, check=True)
    return json.loads(r.stdout.decode())


def geocode(address):
    q = urllib.parse.quote(address)
    res = _get(f"https://nominatim.openstreetmap.org/search?format=json&limit=1&q={q}")
    time.sleep(1.1)
    if not res:
        raise LookupError(f"not found: {address}")
    return float(res[0]["lat"]), float(res[0]["lon"])


def overpass(lat, lon):
    a = f"{lat},{lon}"
    q = f"""[out:json][timeout:120];
(node(around:900,{a})[railway~"^(station|halt|tram_stop|stop)$"];
 node(around:900,{a})[public_transport~"^(stop_position|platform)$"];
 node(around:900,{a})[highway=bus_stop];)->.s;
.s out body;
rel(bn.s)[type=route][route~"^(tram|subway|light_rail|train|bus)$"];
out body;
(nwr(around:1500,{a})[shop=supermarket];
 nwr(around:1500,{a})[shop=chemist];
 nwr(around:2000,{a})[leisure=fitness_centre];
 nwr(around:2000,{a})[amenity=pharmacy];);
out tags center;
nwr(around:2500,{a})[leisure=park][name];
out tags geom;"""
    data = urllib.parse.urlencode({"data": q}).encode()
    for attempt in range(4):
        try:
            return _get(OVERPASS[attempt % 2], data)["elements"]
        except Exception as e:  # server busy: back off and try the mirror
            print(f"  overpass retry {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(20)
    raise RuntimeError("Overpass unavailable")


def dist(a, b):
    R = 6371000
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    return 2 * R * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def walk_min(m):
    return max(1, round(m * 1.3 / 80))


def _centre(e):
    return (e["lat"], e["lon"]) if "lat" in e else (e["center"]["lat"], e["center"]["lon"])


def stations(P, E):
    lines_at = {}
    for r in (e for e in E if e["type"] == "relation"):
        ref, mode = r["tags"].get("ref"), r["tags"].get("route")
        if not ref or ref == "EEx" or (mode == "train" and not ref.startswith("S")):
            continue
        mode = {"light_rail": "subway"}.get(mode, mode)
        for m in r["members"]:
            if m["type"] == "node":
                lines_at.setdefault(m["ref"], set()).add((mode, ref))
    groups = {}
    for s in (e for e in E if e["type"] == "node" and e.get("tags", {}).get("name")):
        t = s["tags"]
        if not ({"railway", "public_transport"} & t.keys() or t.get("highway") == "bus_stop"):
            continue
        n = re.sub(r"^Frankfurt( \(Main\)| am Main)? ", "", t["name"]).strip() or t["name"]
        if n in ("West", "Süd", "Ost", "Hauptbahnhof", "Niederrad", "Höchst", "Rödelheim"):
            n = "Frankfurt " + n  # bare "West" reads oddly, keep the station's full name
        g = groups.setdefault(n, {"d": 1e9, "lines": set()})
        g["d"] = min(g["d"], dist(P, (s["lat"], s["lon"])))
        g["lines"] |= lines_at.get(s["id"], set())

    out, seen = [], set()
    rail = sorted(((n, g) for n, g in groups.items()
                   if g["d"] <= 800 and any(m != "bus" for m, _ in g["lines"])), key=lambda x: x[1]["d"])
    for n, g in rail:
        rl = {x for x in g["lines"] if x[0] != "bus"}
        if rl <= seen:
            continue
        seen |= rl
        segs = []
        for mode, fmt in (("train", "{}"), ("subway", "{}"), ("tram", "Tram {}")):
            refs = sorted({r for m, r in rl if m == mode}, key=lambda r: (len(r), r))
            if refs:
                segs.append(fmt.format("/".join(refs)))
        out.append(f"{' '.join(segs)} {n} {walk_min(g['d'])} min")
        if len(out) == 4:
            break
    if not out:
        bus = sorted(((n, g) for n, g in groups.items() if g["d"] <= 850), key=lambda x: x[1]["d"])[:3]
        for n, g in bus:
            refs = sorted({r for m, r in g["lines"] if m == "bus"})
            out.append(f"Bus {'/'.join(refs) + ' ' if refs else ''}{n} {walk_min(g['d'])} min")
    return ", ".join(out)


def amenities(P, E):
    shops = []
    for e in E:
        t = e.get("tags", {})
        name = t.get("brand") or t.get("name") or ""
        if t.get("shop") == "supermarket" or (t.get("shop") == "chemist" and re.search(r"\bdm\b|rossmann", name, re.I)):
            shops.append((dist(P, _centre(e)), {"Netto Marken-Discount": "Netto"}.get(name, name or "Supermarkt")))
    out = [f"{n} {walk_min(d)} min" for d, n in sorted(shops)[:2]]

    parks = []
    for e in E:
        t = e.get("tags", {})
        if t.get("leisure") == "park" and t.get("name") and not NOT_A_PARK.search(t["name"]):
            pts = [(p["lat"], p["lon"]) for p in e.get("geometry", []) if p] or \
                  [(p["lat"], p["lon"]) for m in e.get("members", []) for p in m.get("geometry", []) if p]
            if pts:
                parks.append((min(dist(P, q) for q in pts), t["name"]))
    if parks:
        d, n = min(parks)
        out.append(f"{n} {walk_min(d)} min")

    gyms = sorted((dist(P, _centre(e)), e["tags"].get("brand") or e["tags"].get("name") or "Gym")
                  for e in E if e.get("tags", {}).get("leisure") == "fitness_centre")
    real = [g for g in gyms if not NICHE_GYM.search(g[1])] or gyms
    if real:
        out.append(f"{real[0][1]} {walk_min(real[0][0])} min")
    pharm = sorted(dist(P, _centre(e)) for e in E if e.get("tags", {}).get("amenity") == "pharmacy")
    if pharm:
        out.append(f"Apotheke {walk_min(pharm[0])} min")
    return ", ".join(out)


def run(ids, force=False):
    cfg = load_config()
    office = geocode(cfg["office"]["address"])
    for lid in ids:
        path = LISTINGS / f"{lid}.json"
        L = json.loads(path.read_text(encoding="utf-8"))
        if L.get("amenities") and not force:
            print(f"{lid}: has amenities, skip")
            continue
        try:
            P = geocode(L["address"])
        except LookupError:
            P = geocode(f"{L.get('stadtteil') or ''}, Frankfurt am Main")
            L["approx_location"] = True
        E = overpass(*P)
        L.update(lat=round(P[0], 5), lon=round(P[1], 5), straight_km=round(dist(P, office) / 1000, 1),
                 stations=stations(P, E), amenities=amenities(P, E))
        path.write_text(json.dumps(L, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{lid}: {L['stations']} | {L['amenities']}")
        time.sleep(5)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    run(args, force="--force" in sys.argv)
