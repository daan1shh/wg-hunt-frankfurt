---
name: wg-send
description: Put approved WG-Gesucht drafts into the contact form with the collage attached, ready for the user to press send. Use only when the user asks to send approved messages.
---

# Send approved messages

## 0. Gate. Refuse unless all of these hold
- `sending.enabled: true` in `config.yaml`, and the collage at `sending.collage` exists in
  `assets/`. Otherwise say the pipeline is in draft-only mode and stop.
- The user approved these specific listings **in this conversation** (by id or number from
  `/wg-status`), and each row's Status is `Approved`.
- Status is not already `Sent` and `Sent on` is empty. Never send twice to a listing.
- Today's count of `Sent on == today` is below `sending.max_per_day`.

## 1. Re-lint every draft
```bash
python3 src/lint_message.py drafts/<id>.md --lang <lang>
```
FAIL or any `[` placeholder left → skip it and report.

## 2. Fill the form, one listing at a time
Load the Chrome tools in one ToolSearch call (include `file_upload`). One tab. Check the user is
logged in. Open the ad, click "Nachricht senden", paste the message from the
`## Message` section exactly, and attach the single collage image.

`sending.user_clicks_send` is true: **stop at the send button.** Tell the user which tab and
listing it is and ask them to press "Nachricht senden" themselves. Wait for "sent".

## 3. Log, after the user confirms
```bash
python3 src/tracker.py set <id> Status=Sent "Sent on=<today>"    # Follow-up on is set to +4 days
```
Pause `sending.pause_seconds` between listings. Close the tab at the end.

## Never
Never click the final send button. Never send an unapproved, unlinted or placeholder draft.
Never exceed the daily limit. Never type a password.
