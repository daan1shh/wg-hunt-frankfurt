"""Shared paths, config loading and date parsing."""
import datetime as dt
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LISTINGS = ROOT / "listings"
DRAFTS = ROOT / "drafts"
TEMPLATES = ROOT / "templates"
ASSETS = ROOT / "assets"


def load_config():
    path = ROOT / "config.yaml"
    if not path.exists():
        sys.exit("config.yaml missing. Copy config.example.yaml to config.yaml and fill it in.")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def to_date(value):
    """Accept a date, datetime, ISO string or German dd.mm.yyyy string. Return date or None."""
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unrecognised date: {value!r}")


def load_listing(listing_id_or_path):
    p = Path(listing_id_or_path)
    if not p.suffix:
        p = LISTINGS / f"{listing_id_or_path}.json"
    return json.loads(p.read_text(encoding="utf-8"))
