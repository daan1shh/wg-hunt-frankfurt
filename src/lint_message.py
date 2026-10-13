"""Style checks for a message. Exits non-zero on any error.

    python src/lint_message.py <file> [--lang en|de] [--template]

<file> is a plain-text message or a drafts/<id>.md (the "## Message" section is checked).
--template allows the [placeholders] (for checking templates/master_*.txt itself).
"""
import re
import sys
from pathlib import Path

from common import TEMPLATES, load_config

BULLET = re.compile(r"^\s*([-*•]|\d+[.)])\s+", re.M)


def message_from(path):
    text = Path(path).read_text(encoding="utf-8")
    if path.endswith(".md"):
        m = re.search(r"^## Message\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
        if not m:
            raise SystemExit(f"{path}: no '## Message' section")
        text = m.group(1)
    return text.strip()


def lint(text, lang=None, template=False, cfg=None):
    """Return (errors, warnings) as lists of strings."""
    cfg = cfg or load_config()
    errors, warnings = [], []
    if "—" in text:
        errors.append(f"em dash (—) x{text.count('—')}")
    if "–" in text:
        errors.append(f"en dash (–) x{text.count('–')}")
    if re.search(r"\s-\s", text):
        errors.append("hyphen used as a dash ( - )")
    if ";" in text:
        errors.append(f"semicolon x{text.count(';')}")
    if not template:
        left = re.findall(r"\[[^\]]+\]", text)
        if left:
            errors.append("unfilled placeholder(s): " + ", ".join(sorted(set(left))))
    if "**" in text or "__" in text:
        errors.append("bold markup")
    if BULLET.search(text):
        errors.append("bullet or numbered list")
    low = text.lower()
    for phrase in cfg["lint"]["banned_phrases"]:
        if phrase.lower() in low:
            errors.append(f"banned phrase: {phrase!r}")
    if lang:
        master = TEMPLATES / f"master_{lang}.txt"
        if master.exists():
            n, m = len(text.split()), len(master.read_text(encoding="utf-8").split())
            tol = cfg["lint"]["length_tolerance"]
            if abs(n - m) > tol * m:
                warnings.append(f"length {n} words vs master {m} (more than {tol:.0%} off)")
    return errors, warnings


def report(errors, warnings):
    lines = [f"ERROR: {e}" for e in errors] + [f"warning: {w}" for w in warnings]
    return "\n".join(lines) if lines else "PASS"


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    lang = args[args.index("--lang") + 1] if "--lang" in args else None
    errors, warnings = lint(message_from(args[0]), lang, "--template" in args)
    print(("PASS" if not errors else "FAIL") + (("\n" + report(errors, warnings)) if errors or warnings else ""))
    sys.exit(1 if errors else 0)
