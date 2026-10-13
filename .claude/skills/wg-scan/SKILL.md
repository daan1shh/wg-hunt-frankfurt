---
name: wg-scan
description: Scan WG-Gesucht for Frankfurt rooms and flats in bulk, read each plausible ad in full, look up commute and amenities, and log scored rows in WG tracker.xlsx for the user to review. Never contacts anyone. Use when asked to look for rooms, scan WG-Gesucht, run the WG scan, or show the current shortlist.
---

# Scan WG-Gesucht

The goal is volume: log as many plausible openings as possible so the user can review them
personally. This skill never drafts or sends messages. That's `/wg-message`, later.

Argument: a number of ads to read (default 30), or `status` to skip scanning and only report (step 7).

## 1. Preflight
- Read `CLAUDE.md`, `CLAUDE.local.md` and `config.yaml`.
- If `~$WG tracker.xlsx` exists, ask the user to close Excel. Never write over it.
- Load the Chrome tools in one ToolSearch call: tabs_context_mcp, tabs_create_mcp, navigate,
  get_page_text, javascript_tool, browser_batch, computer, find, tabs_close_mcp. Use **one** tab.
- Check the header shows the user's name and "Abmelden". If logged out, stop and ask the user to
  log in. Never type a password.

## 2. Collect candidates from the result lists (cheap)
Category ids: 0 = WG-Zimmer, 1 = 1-Zimmer-Wohnung, 2 = Wohnung. The page index is the last number:
```
https://www.wg-gesucht.de/wg-zimmer-in-Frankfurt-am-Main.41.0.1.<page>.html?rMax=800
https://www.wg-gesucht.de/1-zimmer-wohnungen-in-Frankfurt-am-Main.41.1.1.<page>.html?rMax=800
https://www.wg-gesucht.de/wohnungen-in-Frankfurt-am-Main.41.2.1.<page>.html?rMax=800
```
On each result page, read the cards with `javascript_tool`:
```js
[...document.querySelectorAll('div[data-id].offer_list_item')].map(c => { const id = c.dataset.id; const a = [...c.querySelectorAll('a[href]')].find(a => a.href.includes(id + '.html')); return [id, c.querySelector('.col-xs-11')?.innerText.replace(/\s+/g,' ').trim(), c.querySelector('.middle')?.innerText.replace(/\s+/g,' ').trim(), a?.href].join(' ~ '); }).join('\n')
```
Each card gives "Ner WG | Stadtteil | Straße" and "rent € from[ - until] m²". **Drop without opening:**
- IDs already tracked: `python3 src/tracker.py has <id>` (exit 0 = tracked)
- duplicate IDs (sponsored cards repeat), and cards without an ad link
- from-date after 2027-01-15, or an until-date before 2027-04-30 (too little of Dec–May)
- 1-Zimmer or Wohnung cards that are clearly long-term Nachmieter deals still pass, since the ad decides

Pause 3 to 5 s between result pages. Keep going through pages and categories until you have
enough candidates, spreading them across the three categories.

## 3. Read each candidate in full
One `browser_batch` per ad: wait 4 to 6 s, navigate, unhide the tabs, `get_page_text`.
`get_page_text` alone **misses the hidden Lage / WG-Leben / Sonstiges tabs**, which is where trick
questions hide, so the unhide step is mandatory:
```js
document.querySelectorAll('[id^="freitext_"]').forEach(e => { let n = e; for (let k = 0; k < 4 && n; k++, n = n.parentElement) { n.style.display = 'block'; n.style.visibility = 'visible'; n.classList.remove('hidden','collapse'); } const h = document.createElement('p'); h.textContent = '### SECTION ' + e.id; e.prepend(h); });
```
(freitext_0 = Zimmer/Wohnung, 1 = Lage, 2 = WG-Leben, 3 = Sonstiges.)
If a captcha, a login wall or a rate-limit page appears, **stop the scan and tell the user**.

Save `listings/<id>.json` (null when unknown, money in EUR, dates ISO `YYYY-MM-DD`):
```
id, url, type ("WG-Zimmer" | "1-Zi-Wohnung" | "Wohnung"), title, address, stadtteil,
date_found, online_since, kaltmiete, nebenkosten, sonstige_kosten, gesamtmiete, kaution, abloese,
room_size, available_from, available_until (null = unbefristet), zwischenmiete (bool),
min_months, long_lease (bool), flatmates_count, flatmates_detail ("2: Lena 26, Tom 29"),
wg_type, wg_languages, smoking, furnished (true | false | "teilmöbliert"),
anmeldung ("Yes" | "No" | "Unknown"), dist_km, transit_min, bike_min, walk_min,
approx_location (bool), stations, amenities, contacts (list of names), ad_language ("DE" | "EN"),
wanted (the "Gesucht wird" text), eligible (false if the ad's wanted age excludes the applicant,
null if unclear), trick_question (exact text or null), hold_reasons (list), scam_flags (list),
notes, sections {heading: text}, description (raw)
```
Rules when filling it in:
- `gesamtmiete` is **warm and all-in** for a ~6-month stay. Add Strom and Internet if they're
  extra (estimate ~70 and say so in `notes`). Apply surcharges for short contracts (co-living
  providers often add 5–10 %).
- `type` is what it really is: a room in someone's flat listed under "Wohnung" is a `WG-Zimmer`.
- `long_lease`: true when you'd become the main tenant (Nachmieter, own Hauptmietvertrag with
  the landlord). Leaving after May then needs ~3 months' notice. `min_months` comes from
  "Mindestmietdauer".
- `eligible`: judge **age** only. Put the gender part of "Gesucht wird" in `wanted` and leave it
  to the user, because the user hasn't set a gender rule.
- **Scam flags**: rent far below market for size and area, payment or deposit before a viewing,
  "I'm abroad", keys by post, contact only via external email or WhatsApp.
- **Holds**: anything checking the ad was read (a codeword, a word in the subject, "start with
  your favourite X", a question to answer, "write in German", "send a photo") goes into
  `trick_question` verbatim. When unsure, treat it as one. Add to `hold_reasons`: a required form
  or external link, documents up front, a request to contact by phone or email, or a choice the
  user must make (e.g. which of several rooms).
- `notes`: what the user needs to know that the columns don't show, in one or two plain sentences.

## 4. Commute (Google Maps, same tab)
For each ad, two navigations, reading the panel with `javascript_tool`:
```
transit, arrive by 09:00: https://www.google.com/maps/dir/<origin>/<office>/data=!4m6!4m5!2m3!6e1!7e2!8j<epoch>!3e3?hl=de
bike:                     https://www.google.com/maps/dir/<origin>/<office>/data=!4m2!4m1!3e1?hl=de
read: [...document.querySelectorAll('[data-travel_mode]')].map(e=>e.innerText.trim()).join('|') + ' ## ' + document.querySelector('[role="main"]').innerText.replace(/\s+/g,' ').slice(0,450)
```
`<epoch>` is the next weekday at 09:00 written as if it were UTC (2026-10-14 09:00 → 1791968400,
+86400 per day). The chips read Beste | car | transit | walk | bike, and the panel gives the bike km.
Set `transit_min`, `bike_min`, `walk_min` (only if under 30) and `dist_km` (bike route km). If the
ad has no house number, use the street or Stadtteil and set `approx_location`. Dismiss Google's
cookie banner with the most privacy-preserving option.

## 5. Amenities (OpenStreetMap, no browser)
Run this once for the whole batch in the background while you continue in Chrome:
```bash
python3 src/amenities.py <id> <id> ...
```
It fills `stations` and `amenities` and skips listings that already have them.

## 6. Log
```bash
python3 src/tracker.py upsert <id> <id> ...
```
This scores each listing and sets the Status: Rejected for hard filters, Needs review for
unfurnished, long-lease or partly-covering ads, On hold for trick questions and holds, otherwise
New. The one-line "why" goes in Notes.

## 7. Report for the user's review
```bash
python3 src/tracker.py list --status New
python3 src/tracker.py list --status "On hold (trick Q)"
```
1. One line: how many cards were seen, opened, logged and rejected, and how many were already tracked.
2. **Shortlist** (New, best first): `# | score | rent | flatmates | transit | Stadtteil | type | link`
   plus one line per ad on what stands out.
3. **On hold**: the exact trick-question or hold text for each one.
4. **Needs review** and **Rejected**: count and one-line reasons.

Close the tab. Send a PushNotification only if the scan ran long and the user may have walked away.

## Never
Never contact anyone or open a message form. Never open more than one tab. Never hammer the
site. Never type a password.
