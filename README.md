# wg-hunt-frankfurt

A small, human-in-the-loop pipeline for finding a room on WG-Gesucht in Frankfurt. It runs as
Claude Code project skills, driving your own logged-in Chrome session at a human pace.

1. **`/wg-scan`** reads new ads (WG-Zimmer, 1-Zimmer-Wohnung, Wohnung), looks up commute
   time to your office and nearby amenities, and logs scored rows in an Excel tracker.
2. **`/wg-draft`** fills your message skeleton with details from each ad and lints it.
3. **`/wg-status`** shows drafts to approve, ads on hold and follow-ups due.
4. **`/wg-send`** fills the contact form for approved drafts. You press send yourself.

Ads with a "did you read this?" check (codewords, questions, "write in German") are put
on hold for you to answer instead of being sent.

## Setup

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml                 # your dates, office address, budget, weights
cp tracker_template.xlsx "WG tracker.xlsx"
# put your master message (.docx with "ENGLISH VERSION" / "DEUTSCHE VERSION" headings) here, then:
python3 src/extract_template.py
python3 src/lint_message.py templates/master_en.txt --template
```

`templates/example_*.txt` shows the expected shape of the skeleton. Placeholders are
`[names]` / `[Namen]` and `[something you liked]` / `[was dir gefallen hat]`.

## Commands

```bash
python3 src/tracker.py list                    # tracker overview, best score first
python3 src/tracker.py upsert <id>             # score listings/<id>.json and write its row
python3 src/tracker.py set <id> Status=Approved
python3 src/score.py <id>                      # score breakdown for one listing
python3 src/draft.py fill en "Lena" "your balcony"
python3 src/lint_message.py drafts/<id>.md --lang en
```

## Privacy

Everything personal is gitignored: the tracker, the master .docx, `config.yaml`,
`listings/`, `drafts/`, `assets/` and the filled templates. Only code and blank templates
are committed.

## Etiquette

One tab, short pauses, no bulk requests, a daily send limit. If WG-Gesucht shows a captcha
or rate-limit page, the scan stops. Respect the site's terms and the people behind the ads.
