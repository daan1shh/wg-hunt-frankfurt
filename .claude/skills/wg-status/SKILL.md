---
name: wg-status
description: Report on the WG search: drafts waiting for approval, holds needing an answer, follow-ups due, and replies. Use when asked how the WG search is going, what to approve, or what to chase.
---

# WG search status

```bash
python3 src/tracker.py list
```

Report:
1. **Headline**: counts by Status, plus anything at Viewing or Got it.
2. **On hold (trick Q)**: for each, the exact trick question and the proposed answer from
   `drafts/<id>.md`. The user decides.
3. **Drafts to approve**: numbered, best score first, one line each
   (`# | id | score | rent | flatmates | transit | Stadtteil | liked detail`). Offer to show
   any full message. When the user approves ("1, 3, 5" or "all above 70"), run
   `python3 src/tracker.py set <id> Status=Approved` for each.
4. **Follow-ups due**: Status Sent and `Follow-up on` is today or earlier. Offer a short
   follow-up draft that passes `src/lint_message.py`. The user sends it.
5. **Sending budget**: how many sent today vs `sending.max_per_day`, and whether sending
   is enabled (it needs the collage in `assets/`).

When the user reports an outcome (reply, viewing, rejected, got it), update Status with
`tracker.py set`. It backs the tracker up first. If `~$WG tracker.xlsx` exists, ask them to
close Excel.
