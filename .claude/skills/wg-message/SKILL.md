---
name: wg-message
description: Draft personal WG-Gesucht messages for listings the user picked, lint them, and fill the contact form with the collage attached for the user to send. Only usable once the collage and flatmate notes are in assets/ and sending is enabled. Use when the user asks to message, contact or apply to specific listings.
---

# Message picked listings

## 0. Gate. Refuse unless all of these hold
- `sending.enabled: true` in `config.yaml`, and the collage at `sending.collage` exists in `assets/`.
  Otherwise say messaging isn't set up yet (collage and flatmate notes are missing) and stop.
- The user picked these listings **in this conversation**, by id or by number from a
  `/wg-scan` shortlist. Never message anything they didn't pick.
- The Status is not `Sent` and `Sent on` is empty. Never message a listing twice.
- Today's count of `Sent on == today` is below `sending.max_per_day`.

## 1. Draft
Read `listings/<id>.json`, especially `description`, `sections`, `contacts` and `trick_question`.
Language: German ad → `de`, English ad → `en`. If the ad asks for German, use `de`.

Start from the skeleton, unchanged:
```bash
python3 src/draft.py fill <lang> "<names>" "<liked>"
```
- `names`: first names from the ad ("Lena and Tom" / "Lena und Tom"). None given → `""`
  gives "Hi everyone" / "Hallo zusammen".
- `liked`: one specific, genuine detail from *their* ad that reads naturally after "really liked"
  or before "hat mir sofort gefallen". Not the commute, because the skeleton already says that.

**Only tweak what the ad gives a reason to tweak.** Answer a question they ask. Match a playful
ad with a slightly playful line. Mention a shared interest if they list hobbies. Drop the
"bridge a gap" sentence if they want someone long term but accept 6 months. For a whole
Wohnung or a landlord, rewrite the flatmate lines for a landlord in the same tone. Never invent
facts that aren't in the master. Keep the length close to the master.

**Trick questions**: answer them in the message (e.g. start with the codeword), and show the
user the exact ad text next to your answer before going further.

Write a fill JSON (shape in `src/draft.py`, in the scratchpad) with `body` holding the final
message and a `personalisation` list quoting the ad for each change:
```bash
python3 src/draft.py write <fill.json>        # exit 1 = lint FAIL, fix and rerun
python3 src/tracker.py set <id> Status=Drafted "Draft file=drafts/<id>.md"
```

## 2. Show, then wait
Paste each full message with what was personalised. The user approves, edits or drops each one.
Set approved ones to `Status=Approved`.

## 3. Fill the form, one listing at a time
Re-lint first: `python3 src/lint_message.py drafts/<id>.md --lang <lang>`. FAIL or any `[` left → skip.
Load the Chrome tools in one ToolSearch call (include `file_upload`), one tab, and check the user is
logged in. Open the ad, click "Nachricht senden", paste the `## Message` section exactly and
attach the single collage image.

**Stop at the send button.** Tell the user which listing is ready and ask them to press
"Nachricht senden" themselves. Wait for "sent".

## 4. Log, after the user confirms
```bash
python3 src/tracker.py set <id> Status=Sent "Sent on=<today>"    # Follow-up on is set to +4 days
```
Pause `sending.pause_seconds` between listings and close the tab at the end.

## Follow-ups
For rows with Status Sent and `Follow-up on` today or earlier, offer a short follow-up that passes
`src/lint_message.py`. The user sends it. When the user reports an outcome (Replied, Viewing,
Rejected, Got it), update the Status with `tracker.py set`.

## Never
Never click the final send button. No em dashes, en dashes or semicolons, no bullets or bold, no
"AI" phrasing, no unfilled `[placeholder]`. Never exceed the daily limit. Never type a password.
