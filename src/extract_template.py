"""Pull the English and German skeletons out of the master .docx into templates/.

    python src/extract_template.py [--force] [--docx "WG master application.docx"]

Writes templates/master_en.txt and templates/master_de.txt (both gitignored).
Refuses to overwrite existing templates without --force, because they may hold
hand-approved edits (dash and semicolon clean-up).
"""
import sys

from docx import Document

from common import ROOT, TEMPLATES

MARKERS = {"en": "ENGLISH VERSION", "de": "DEUTSCHE VERSION"}


def extract(docx_path):
    paras = [p.text.strip() for p in Document(docx_path).paragraphs]
    starts = {lang: next(i for i, t in enumerate(paras) if t.upper() == m)
              for lang, m in MARKERS.items()}
    en = paras[starts["en"] + 1:starts["de"]]
    de = paras[starts["de"] + 1:]
    return {lang: "\n\n".join(t for t in block if t) + "\n" for lang, block in (("en", en), ("de", de))}


if __name__ == "__main__":
    args = sys.argv[1:]
    force = "--force" in args
    docx_path = ROOT / "WG master application.docx"
    if "--docx" in args:
        docx_path = ROOT / args[args.index("--docx") + 1]
    TEMPLATES.mkdir(exist_ok=True)
    for lang, text in extract(docx_path).items():
        out = TEMPLATES / f"master_{lang}.txt"
        if out.exists() and not force:
            print(f"skip {out.name} (exists, use --force)")
            continue
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out.name} ({len(text.split())} words)")
