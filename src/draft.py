"""Fill the master skeleton for one listing and write drafts/<id>.md.

    python src/draft.py fill <lang> "<names>" "<liked>"   # print the filled skeleton
    python src/draft.py write <fill.json>                 # write drafts/<id>.md, lint, exit 1 on FAIL

fill.json:
{
  "listing_id": "12345678",
  "language": "en" | "de",
  "names": "Lena and Tom",            # or "everyone" / "zusammen" when the ad gives none
  "liked": "your balcony with the tomato plants",
  "body": null,                         # optional: full hand-tweaked message, used instead of the fill
  "personalisation": [                  # what changed and why, quoting the ad
    {"what": "names", "why": "signed by Lena and Tom", "quote": "Liebe Grüße, Lena & Tom"}
  ],
  "trick_question": null,               # exact text from the ad, if any
  "proposed_answer": null               # how the message answers it (marked for review)
}
"""
import json
import sys

from common import DRAFTS, ROOT, TEMPLATES, load_listing
from lint_message import lint, report

PLACEHOLDERS = {
    "names": ["[names]", "[Namen]"],
    "liked": ["[something you liked]", "[was dir gefallen hat]"],
}
GREETING_NO_NAMES = {"en": ("Hi [names],", "Hi everyone,"), "de": ("Hallo [Namen],", "Hallo zusammen,")}


def fill(lang, names, liked):
    text = (TEMPLATES / f"master_{lang}.txt").read_text(encoding="utf-8")
    if not names or names.lower() in ("everyone", "zusammen"):
        old, new = GREETING_NO_NAMES[lang]
        text = text.replace(old, new)
    for token in PLACEHOLDERS["names"]:
        text = text.replace(token, names)
    for token in PLACEHOLDERS["liked"]:
        text = text.replace(token, liked)
    return text.strip()


def write(spec):
    lid = str(spec["listing_id"])
    lang = spec["language"]
    message = (spec.get("body") or fill(lang, spec.get("names"), spec["liked"])).strip()
    errors, warnings = lint(message, lang)
    try:
        L = load_listing(lid)
    except FileNotFoundError:
        L = {}

    out = [f"# Draft {lid}: {L.get('title', '')}".rstrip(), ""]
    out.append(f"URL: {L.get('url', '')}  ")
    out.append(f"Language: {lang.upper()}  ")
    out.append(f"Contact: {', '.join(L.get('contacts') or []) or 'none named'}")
    out += ["", "## Message", "", message, "", "## Personalisation", ""]
    for p in spec.get("personalisation") or []:
        line = f"* {p['what']}: {p['why']}"
        if p.get("quote"):
            line += f' (ad: "{p["quote"]}")'
        out.append(line)
    if spec.get("trick_question"):
        out += ["", "## Trick question (ON HOLD, needs your OK)", "",
                f'Ad says: "{spec["trick_question"]}"', "",
                f"Proposed answer: {spec.get('proposed_answer') or 'TODO'}"]
    out += ["", "## Lint", "", "PASS" if not errors else "FAIL", "", report(errors, warnings), ""]

    DRAFTS.mkdir(exist_ok=True)
    path = DRAFTS / f"{lid}.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}: {'PASS' if not errors else 'FAIL'}")
    if errors or warnings:
        print(report(errors, warnings))
    return path, not errors


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["fill"] and len(args) == 4:
        print(fill(args[1], args[2], args[3]))
    elif args[:1] == ["write"] and len(args) == 2:
        with open(args[1], encoding="utf-8") as f:
            _, ok = write(json.load(f))
        sys.exit(0 if ok else 1)
    else:
        sys.exit(__doc__)
