# wg-hunt-frankfurt

Semi-automated WG-Gesucht pipeline: scan ads, log them in `WG tracker.xlsx`, score them,
draft personal messages from a master skeleton, and send only what the user approves.
Personal details (who, dates, office) live in `CLAUDE.local.md` and `config.yaml`, both gitignored.

## Workflow
Two skills:
- `/wg-scan [N | status]`: bulk scan. Reads as many plausible ads as possible and logs them, scored,
  for the user to review **personally**. Never contacts anyone.
- `/wg-message`: drafts and fills the contact form for listings the user picks. **Disabled** until the
  photo collage and flatmate notes are in `assets/` and `sending.enabled: true`.

Build progress goes phase by phase. Finish a phase, show the result, wait for the user's OK.

| Phase | What | State |
|---|---|---|
| 0 | Setup questions | done 2026-10-13 |
| 1 | Repo skeleton | done 2026-10-13 |
| 2 | Tracker columns (`tracker.py migrate` on the real tracker) | done 2026-10-13 |
| 3 | Scanning, test run of 5 ads | done 2026-10-13 |
| 4 | Scoring tuned on real ads, skills cut to wg-scan + wg-message | done 2026-10-13 |
| 5 | Bulk scanning, user reviews ads personally | **current** |
| 6 | Messaging (`/wg-message`) | later, once `assets/` has the collage and flatmate notes |

## Decisions
- Repo is **public**. Personal data is gitignored: `*.docx`, the tracker, `listings/`, `drafts/`,
  `assets/`, `backups/`, `templates/master_*.txt`, `config.yaml`, `CLAUDE.local.md`, `PROMPT_*.md`.
  Committed: code, skills, `config.example.yaml`, `templates/example_*.txt`, `tracker_template.xlsx`.
- The user **always clicks "Nachricht senden" themselves**. Claude fills the form and attaches the
  collage, then stops. Max 5 messages per day, with pauses between them.
- All WG types are fine. No preference on flatmates' age, gender or Stadtteil.
- Ads that exclude the applicant's gender (`applicant.gender` in `config.yaml`) are skipped: `eligible: false` → Rejected.
- Language follows the ad (DE → German version, EN → English). If the ad asks for German, use German.
- The rent cap is **warm** (Gesamtmiete, all-in).
- **Long leases** (Nachmieter / own main lease / minimum term past May) get -15 and Needs review.
- **Unfurnished is a fallback only** (buying furniture for 6 months then selling it is too much hassle). Score -30 and status Needs review, never drafted unless the user asks. Teilmöbliert -8.
- Templates were cleaned once (em dashes and semicolons → full stops or commas, approved diff).
  `extract_template.py` won't overwrite them without `--force`.

## Rules
- **Git: never list Claude as author or co-author.** No `Co-Authored-By` trailer and no
  "Generated with Claude Code" line in commits, PRs or docs. Commits use the user's git identity only.
- Before writing the tracker, check for `~$WG tracker.xlsx`. If it exists, ask the user to close
  Excel. `tracker.py` refuses anyway and backs up to `backups/` before every write.
- Chrome: the user's own logged-in session, one tab, human pace. Never type a password. Captcha or
  rate-limit page → stop and tell the user.
- Messages must pass `src/lint_message.py`: no em or en dashes, no semicolons, no bullets or bold,
  no "AI" phrasing, no unfilled `[placeholder]`. Don't invent facts beyond the master.
- Trick questions, required forms or external links, documents up front, anything personal → status
  `On hold (trick Q)`, draft with the proposed answer marked, notify the user. When unsure, hold.
- Draft-only mode until `sending.enabled: true` in `config.yaml` **and** the collage exists.

## Layout
```
config.example.yaml   copy to config.yaml: dates, office, budget, weights, send limit
src/common.py         paths, config, dates
src/tracker.py        init-template | migrate | has | upsert | set | list
src/score.py          hard filters + 0-100 score, one-line "why", per-component points
src/amenities.py      stations + amenities from OpenStreetMap (Nominatim + Overpass, via curl)
src/draft.py          fill skeleton, write drafts/<id>.md with lint result
src/lint_message.py   message style checks, exit 1 on violation
src/extract_template.py  .docx → templates/master_{en,de}.txt
.claude/skills/       wg-scan, wg-message
```
The listing JSON schema is in `.claude/skills/wg-scan/SKILL.md`.

## Open questions
- 6019405 (Karla, Bockenheim): asks for contact by phone or email. The user decides.
