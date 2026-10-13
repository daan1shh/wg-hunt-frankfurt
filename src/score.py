"""Hard filters and 0-100 score for one listing.

    python src/score.py <listing_id | path/to/listing.json>
"""
import sys

from common import load_config, load_listing, to_date


def coverage(listing, cfg):
    """Yes / Partly / No: does the availability cover the needed window?"""
    need_from = to_date(cfg["applicant"]["need_from"])
    need_until = to_date(cfg["applicant"]["need_until"])
    avail_from = to_date(listing.get("available_from"))
    avail_until = to_date(listing.get("available_until"))  # None = unbefristet
    start = avail_from or need_from
    if start <= need_from and (avail_until is None or avail_until >= need_until):
        return "Yes"
    if start > need_until or (avail_until is not None and avail_until < need_from):
        return "No"
    return "Partly"


def _lerp_points(value, full_at, zero_at, weight):
    """Full points at or better than full_at, zero at or worse than zero_at, linear between."""
    if value is None:
        return None
    if full_at < zero_at:
        frac = (zero_at - value) / (zero_at - full_at)
    else:
        frac = (value - zero_at) / (full_at - zero_at)
    return weight * max(0.0, min(1.0, frac))


def score(listing, cfg=None):
    """Return dict: score, covers, rejected (bool), reasons (list), why (one line)."""
    cfg = cfg or load_config()
    s = cfg["scoring"]
    w = s["weights"]
    cap = cfg["search"]["max_rent_warm"]
    reasons, parts = [], []

    rent = listing.get("gesamtmiete")
    covers = coverage(listing, cfg)

    # hard filters
    if rent is not None and rent > cap:
        reasons.append(f"Gesamtmiete {rent} EUR over {cap} cap")
    if covers == "No":
        reasons.append("availability does not cover Dec to May")
    if listing.get("scam_flags"):
        reasons.append("suspected scam: " + ", ".join(listing["scam_flags"]))
    if reasons:
        return {"score": 0, "covers": covers, "rejected": True, "reasons": reasons,
                "why": "REJECTED: " + "; ".join(reasons)}

    total = 0.0

    # rent
    if rent is None:
        pts = w["rent"] * 0.5
        parts.append("rent unknown")
    else:
        pts = _lerp_points(rent, s["rent_full_at"], cap, w["rent"])
        parts.append(f"{rent:.0f} EUR")
    total += pts

    # flatmates: fewer is better, and the allowance shrinks as rent rises
    n = listing.get("flatmates_count")
    if listing.get("type") in ("1-Zi-Wohnung", "Wohnung") or n == 0:
        pts = w["flatmates"]
        parts.append("own flat" if listing.get("type") != "WG-Zimmer" else "0 flatmates")
    elif n is None:
        pts = w["flatmates"] * 0.5
        parts.append("flatmates unknown")
    else:
        r = rent if rent is not None else (s["rent_full_at"] + cap) / 2
        frac = max(0.0, min(1.0, (r - s["rent_full_at"]) / (cap - s["rent_full_at"])))
        allowed = s["flatmates_allowed_at_rent_full"] + frac * (
            s["flatmates_allowed_at_rent_cap"] - s["flatmates_allowed_at_rent_full"])
        excess = max(0.0, n - allowed)
        pts = w["flatmates"] * max(0.0, 1 - s["flatmate_penalty_each"] * excess)
        parts.append(f"{n} flatmates")
    total += pts

    # commute
    t = listing.get("transit_min")
    if t is None:
        pts = w["commute"] * 0.4
        parts.append("commute unknown")
    else:
        pts = _lerp_points(t, s["commute_full_at_min"], s["commute_zero_at_min"], w["commute"])
        parts.append(f"{t} min transit" + (" (approx)" if listing.get("approx_location") else ""))
    total += pts

    # room size: slight penalty only
    m2 = listing.get("room_size")
    if m2 is None:
        pts = w["room_size"] * 0.7
    else:
        pts = _lerp_points(m2, s["room_min_m2"], s["room_zero_at_m2"], w["room_size"])
        if m2 < s["room_min_m2"]:
            parts.append(f"small room {m2} m2")
    total += pts

    # dates
    avail_from = to_date(listing.get("available_from"))
    avail_until = to_date(listing.get("available_until"))
    if covers == "Yes":
        pts = w["dates"] * 0.6
        if listing.get("zwischenmiete") and avail_until is not None and \
                (avail_until - to_date(cfg["applicant"]["need_until"])).days <= 45:
            pts += w["dates"] * 0.2
            parts.append("Zwischenmiete fits")
        if avail_from is None or avail_from <= to_date(s["mid_nov_cutoff"]):
            pts += w["dates"] * 0.2
            parts.append("mid-Nov move-in ok")
    else:
        pts = 0
        parts.append("only partly covers Dec to May")
    total += pts

    # Anmeldung
    a = (listing.get("anmeldung") or "Unknown").lower()
    if a == "yes":
        total += w["anmeldung"]
        parts.append("Anmeldung ok")
    elif a == "no":
        total -= s["anmeldung_no_penalty"]
        parts.append("NO Anmeldung")
    else:
        total += w["anmeldung"] * 0.4

    final = int(round(max(0.0, min(100.0, total))))
    return {"score": final, "covers": covers, "rejected": False, "reasons": [],
            "why": f"{final}: " + ", ".join(parts)}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(score(load_listing(sys.argv[1])))
