---
name: wg-draft
description: Draft a personal WG-Gesucht message for tracked listings from the master skeleton, lint it, and write drafts/<id>.md. Use after a scan, or when asked to draft messages for specific listings.
---

# Draft messages

## 1. Pick listings
Default: every tracker row with Status `New` or `On hold (trick Q)`, best score first.
```bash
python3 src/tracker.py list --status New
```
Skip `Rejected`. Ask before drafting `Needs review` rows.

## 2. Read the ad, then fill the skeleton
Read `listings/<id>.json`, especially `description`, `sections` and `contacts`.

**Language**: German ad → `de`, English ad → `en`. If the ad asks for German, use `de`.

Start from the skeleton, unchanged:
```bash
python3 src/draft.py fill <lang> "<names>" "<liked>"
```
- `names`: flatmates' first names from the ad ("Lena and Tom" / "Lena und Tom"). None
  given → pass `""` for "Hi everyone" / "Hallo zusammen".
- `liked`: one specific, genuine detail from *their* ad that reads naturally after
  "really liked" / before "hat mir sofort gefallen". Not the commute, the skeleton
  already says that.

**Only tweak what the ad gives a reason to tweak.** Answer a question they ask. Match a
playful ad with a slightly playful line. Mention a shared interest if they list hobbies.
Drop the "bridge a gap" sentence if they want long-term but accept 6 months. For a
whole Wohnung, rewrite the flatmate lines for a landlord in the same tone. Never invent
facts that aren't in the master. Keep the length close to the master.

## 3. Write and lint
Write a fill JSON (shape in `src/draft.py`, put it in the scratchpad) with `body` holding
the final tweaked message, plus a `personalisation` list quoting the ad for every change.
For a trick question include `trick_question` and `proposed_answer`, and work the answer
into the body.
```bash
python3 src/draft.py write <fill.json>        # exit 1 = lint FAIL, fix and rerun
python3 src/tracker.py set <id> Status=Drafted "Draft file=drafts/<id>.md"
```
Keep Status `On hold (trick Q)` for trick-question drafts, and only set the Draft file.

Subagents can draft several listings in parallel. Each one runs the lint and returns the path.

## 4. Report
For each draft: id, language, the `liked` detail, tweaks, lint result. Paste the full
message only for holds and anything unusual. The user reviews the rest with `/wg-status`.

## Never
No em dashes, en dashes or semicolons. No bullet lists, no bold, no "AI" phrasing. No
unfilled `[placeholder]`. Never send from this skill.
