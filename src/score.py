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
    if listing.get("eligible") is False:
        reasons.append(f"not eligible, ad wants: {listing.get('wanted') or 'see ad'}")
    if listing.get("scam_flags"):
        reasons.append("suspected scam: " + ", ".join(listing["scam_flags"]))
    if reasons:
        return {"score": 0, "covers": covers, "rejected": True, "reasons": reasons,
                "why": "REJECTED: " + "; ".join(reasons)}

    pts = {}  # component -> points (penalties negative)

    # rent
    if rent is None:
        pts["rent"] = w["rent"] * 0.5
        parts.append("rent unknown")
    else:
        pts["rent"] = _lerp_points(rent, s["rent_full_at"], cap, w["rent"])
        parts.append(f"{rent:.0f} EUR")

    # flatmates: fewer is better, and the allowance shrinks as rent rises
    n = listing.get("flatmates_count")
    if listing.get("type") in ("1-Zi-Wohnung", "Wohnung") or n == 0:
        pts["flatmates"] = w["flatmates"]
        parts.append("own flat" if listing.get("type") != "WG-Zimmer" else "0 flatmates")
    elif n is None:
        pts["flatmates"] = w["flatmates"] * 0.5
        parts.append("flatmates unknown")
    else:
        r = rent if rent is not None else s["rent_high"]
        frac = max(0.0, min(1.0, (r - s["rent_full_at"]) / (s["rent_high"] - s["rent_full_at"])))
        allowed = s["flatmates_allowed_at_rent_full"] + frac * (
            s["flatmates_allowed_at_rent_high"] - s["flatmates_allowed_at_rent_full"])
        excess = max(0.0, n - allowed)
        pts["flatmates"] = w["flatmates"] * max(0.0, 1 - s["flatmate_penalty_each"] * excess)
        parts.append(f"{n} flatmates" + (f" (too many for the rent, ok up to {allowed:.1f})" if excess else ""))

    # commute (the main preference)
    t = listing.get("transit_min")
    if t is None:
        pts["commute"] = w["commute"] * 0.4
        parts.append("commute unknown")
    else:
        pts["commute"] = _lerp_points(t, s["commute_full_at_min"], s["commute_zero_at_min"], w["commute"])
        parts.append(f"{t} min transit" + (" (approx)" if listing.get("approx_location") else ""))

    # room size: slight penalty only
    m2 = listing.get("room_size")
    if m2 is None:
        pts["room"] = w["room_size"] * 0.7
    else:
        pts["room"] = _lerp_points(m2, s["room_min_m2"], s["room_zero_at_m2"], w["room_size"])
        if m2 < s["room_min_m2"]:
            parts.append(f"small room {m2} m2")

    # dates
    need_until = to_date(cfg["applicant"]["need_until"])
    avail_from = to_date(listing.get("available_from"))
    avail_until = to_date(listing.get("available_until"))
    if covers == "Yes":
        pts["dates"] = w["dates"] * 0.6
        if listing.get("zwischenmiete") and avail_until is not None and \
                (avail_until - need_until).days <= 45:
            pts["dates"] += w["dates"] * 0.2
            parts.append("Zwischenmiete fits")
        if avail_from is None or avail_from <= to_date(s["early_move_in_cutoff"]):
            pts["dates"] += w["dates"] * 0.2
            parts.append("late-Nov move-in ok")
    else:
        # penalty grows with the share of the Dec-May window that is not covered
        need_from = to_date(cfg["applicant"]["need_from"])
        lo = max(avail_from or need_from, need_from)
        hi = min(avail_until or need_until, need_until)
        share = max(0, (hi - lo).days) / (need_until - need_from).days
        pts["dates"] = -s["partial_cover_penalty"] * (1 - share)
        parts.append(f"covers only {share:.0%} of Dec to May")

    # Anmeldung
    a = (listing.get("anmeldung") or "Unknown").lower()
    if a == "yes":
        pts["anmeldung"] = w["anmeldung"]
        parts.append("Anmeldung ok")
    elif a == "no":
        pts["anmeldung"] = -s["anmeldung_no_penalty"]
        parts.append("NO Anmeldung")
    else:
        pts["anmeldung"] = w["anmeldung"] * 0.4

    # furnishing: unfurnished is a fallback only
    f = listing.get("furnished")
    if f is False or str(f).lower() in ("no", "unmöbliert", "false"):
        pts["furnishing"] = -s["unfurnished_penalty"]
        parts.append("UNFURNISHED")
    elif isinstance(f, str) and "teil" in f.lower():
        pts["furnishing"] = -s["partly_furnished_penalty"]
        parts.append("partly furnished")

    # lease that is hard to leave after May
    if long_lease(listing, cfg):
        pts["lease"] = -s["long_lease_penalty"]
        parts.append("LONG LEASE")

    final = int(round(max(0.0, min(100.0, sum(pts.values())))))
    return {"score": final, "covers": covers, "rejected": False, "reasons": [],
            "points": {k: round(v, 1) for k, v in pts.items()},
            "why": f"{final}: " + ", ".join(parts)}


def long_lease(listing, cfg):
    """True if leaving after the window is hard: own main lease / Nachmieter, or a minimum term past it."""
    if listing.get("long_lease"):
        return True
    months = listing.get("min_months")
    start = to_date(listing.get("available_from")) or to_date(cfg["applicant"]["need_from"])
    if months:
        end_month = start.month - 1 + int(months)
        min_end = start.replace(year=start.year + end_month // 12, month=end_month % 12 + 1, day=1)
        return (min_end - to_date(cfg["applicant"]["need_until"])).days > 31
    return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    r = score(load_listing(sys.argv[1]))
    print(r["why"])
    for k, v in (r.get("points") or {}).items():
        print(f"  {k:<11}{v:>6}")
