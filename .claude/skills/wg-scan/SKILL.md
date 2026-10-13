---
name: wg-scan
description: Scan WG-Gesucht for Frankfurt rooms and flats, read each new ad, look up commute and amenities, save listings/<id>.json and log scored rows in WG tracker.xlsx. Use when asked to look for rooms, scan WG-Gesucht, or run the WG scan.
---

# Scan WG-Gesucht

## 1. Preflight
- Read `CLAUDE.md`, `CLAUDE.local.md` and `config.yaml` (budget, dates, office address).
- If `~$WG tracker.xlsx` exists, Excel has the tracker open. Ask the user to close it. Never write over it.
- Load the Chrome tools in one ToolSearch call (tabs_context_mcp, tabs_create_mcp, navigate,
  get_page_text, find, computer, read_page, tabs_close_mcp). Open **one** new tab.
- Check the header shows the user's name and "Abmelden". If logged out, stop and ask them
  to log in. Never type a password.

## 2. Search pages
Category ids: 0 = WG-Zimmer, 1 = 1-Zimmer-Wohnung, 2 = Wohnung. Frankfurt city id is in
`config.yaml`. Pattern (verify on the site, the filter params may change):
`https://www.wg-gesucht.de/<slug>-in-Frankfurt-am-Main.41.<cat>.1.0.html?rMax=800`
Use the site's own filter form for move-in date if the URL params don't stick, then copy the
resulting URL into `CLAUDE.md` so the next run reuses it.

Collect listing IDs from the result list. Skip any already tracked:
```bash
python3 src/tracker.py has <id>    # exit 0 = tracked, skip it
```
**Test run = 5 ads.** Otherwise stop after the number the user asked for (default 15).

## 3. Read each ad fully
`get_page_text` alone **misses the hidden Lage / WG-Leben / Sonstiges tabs**, which is where
trick questions hide. So after navigating, first run this with `javascript_tool`, then `get_page_text`:
```js
document.querySelectorAll('[id^="freitext_"]').forEach(e => { let n = e; for (let k = 0; k < 4 && n; k++, n = n.parentElement) { n.style.display = 'block'; n.style.visibility = 'visible'; n.classList.remove('hidden','collapse'); } const h = document.createElement('p'); h.textContent = '### SECTION ' + e.id; e.prepend(h); });
```
(freitext_0 = Zimmer/Wohnung, 1 = Lage, 2 = WG-Leben, 3 = Sonstiges.) Batch the wait, navigate,
unhide and get_page_text calls into one `browser_batch` per ad.

Read: Zimmer/Wohnung details, Kosten, Adresse,
Verfügbarkeit, Lage, WG-Leben, Sonstiges, the free-text description, and the flatmate
sidebar. Pause a few seconds between ads, like a person reading. If a captcha or
rate-limit page appears, **stop and tell the user**.

Save `listings/<id>.json` with these keys (null when unknown, money as numbers in EUR):
```
id, url, type ("WG-Zimmer" | "1-Zi-Wohnung" | "Wohnung"), title, address, stadtteil,
date_found, online_since, kaltmiete, nebenkosten, sonstige_kosten, gesamtmiete, kaution,
abloese, room_size, available_from, available_until (null = unbefristet),
zwischenmiete (bool), flatmates_count, flatmates_detail ("2: Lena 26 w, Tom 29 m"),
wg_type, wg_languages, smoking, furnished (bool), anmeldung ("Yes" | "No" | "Unknown"),
dist_km, transit_min, bike_min, walk_min, approx_location (bool), stations, amenities,
contacts (list of names), ad_language ("DE" | "EN"), trick_question (exact text or null),
wanted (the "Gesucht wird" text), eligible (false if the wanted age or gender excludes the
applicant, null if unclear),
hold_reasons (list), scam_flags (list), notes, sections {heading: text}, description (raw)
```
Dates as ISO `YYYY-MM-DD`. `gesamtmiete` is warm and all-in: if the ad only gives
Kaltmiete + Nebenkosten, add them (plus Sonstige Kosten) and say so in `notes`.

**Scam flags**: rent far below market for the size and area, payment or deposit before a
viewing, "I'm abroad", keys by post, contact only via external email or WhatsApp.

**Trick questions and holds**: anything checking that the ad was read (a codeword, a word in
the subject, "start with your favourite X", a question to answer, "write in German",
"send a photo"). Copy the exact text into `trick_question`. When unsure, treat it as one.
Also put into `hold_reasons`: application form or external link required, documents
requested up front, anything only the user can answer.

## 4. Commute and amenities
From the ad address (or street or Stadtteil if that's all there is; set `approx_location`)
to the office in `config.yaml`: Google Maps transit for a weekday 09:00 arrival, bike time,
walk time if under 30 min, route distance in km.

Google Maps URLs that work (the old `ttype=arr&time=` params are ignored):
```
transit, arrive by 09:00: https://www.google.com/maps/dir/<origin>/<office>/data=!4m6!4m5!2m3!6e1!7e2!8j<epoch>!3e3?hl=de
bike:                     https://www.google.com/maps/dir/<origin>/<office>/data=!4m2!4m1!3e1?hl=de
```
`<epoch>` is the next weekday 09:00 written as if it were UTC (2026-10-14 09:00 → 1791968400,
add 86400 per day). Read the results with `javascript_tool`:
`[...document.querySelectorAll('[data-travel_mode]')].map(e=>e.innerText.trim()).join('|') + ' ## ' + document.querySelector('[role="main"]').innerText.replace(/\s+/g,' ').slice(0,450)`.
The chips are Beste | car | transit | walk | bike. The panel text gives lines and km. Dismiss the
Google cookie banner with the most privacy-preserving option if it appears. Nearest S/U/Tram stops with lines and
walking minutes. Two nearest supermarkets with distance, plus a park, gym or anything
notable. Keep `amenities` to one compact line, e.g.
`Rewe 3 min, Aldi 6 min, Rebstockpark 5 min, FitX 8 min`.
Subagents may do these lookups in parallel with WebSearch or WebFetch. Chrome stays with the
main session.

## 5. Log
```bash
python3 src/tracker.py upsert <id> <id> ...
```
This scores each listing, applies hard filters (Rejected), sets On hold for trick
questions, and writes the "why this score" line to Notes.

## 6. Report
Table, best first: `# | score | status | rent | flatmates | transit | Stadtteil | type | why`.
Then list every **On hold** ad with its exact trick-question text, and every Rejected ad
with its reason. Send a PushNotification if any holds were found. Close the tab.
Then wait. Drafting is `/wg-draft`.

## Never
Never send a message from this skill. Never open more than one tab. Never hammer the site.
Never type a password.
