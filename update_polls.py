#!/usr/bin/env python3
#by Claude Sonnet 5
"""Fetch new Carney government approval polls from Wikipedia and append them to the local CSV.

Rather than scraping rendered HTML (which buries the numbers in citation
templates, sort keys, and colour-shading markup), this pulls the raw wikitext
of the "Table of polls" subsection under "Government approval polls" via the
MediaWiki API and parses the wiki-table syntax directly. New rows are merged
into the existing CSV (deduped on firm + date) and written back in the same
newest-first order and formatting the CSV already uses.
"""
import re
from pathlib import Path

import pandas as pd
import requests

API_URL = "https://en.wikipedia.org/w/api.php"
PAGE_TITLE = "Opinion polling for the 46th Canadian federal election"
CSV_PATH = Path("carney government approval polls.csv")
NEW_POLLS_SUMMARY_PATH = Path("new_polls.txt")
CSV_COLUMNS = [
    "Polling_firm",
    "Last_date_of_polling",
    "Approve",
    "Disapprove",
    "Unsure/neither",
    "Margin_of_error",
    "Sample_size",
    "Polling_method",
    "Net_approval",
]

# Firms to exclude even if they show up in the table (they poll Carney/PM
# favourability or something else rather than government/PM approval).
# See "Which polling firms to inlcude.md".
EXCLUDED_FIRMS = {
    "Nanos Research",
    "Mainstreet Research",
    "Pallas Data",
    "Kolosowski Strategies",
    "Pollera",
}

HEADERS = {"User-Agent": "carney-approval-wikipedia-scraper (open source project)"}


def api_get(params):
    params = {**params, "format": "json"}
    response = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def find_table_of_polls_section():
    """Locate the 'Table of polls' section nested under 'Government approval polls'."""
    data = api_get({"action": "parse", "page": PAGE_TITLE, "prop": "sections"})
    sections = data["parse"]["sections"]

    in_government_approval = False
    for section in sections:
        if section["line"] == "Government approval polls" and section["toclevel"] == 1:
            in_government_approval = True
            continue
        if in_government_approval and section["toclevel"] == 1:
            # Reached the next top-level section without finding our table.
            break
        if in_government_approval and section["line"] == "Table of polls":
            return section["index"]

    raise RuntimeError("Could not find the 'Table of polls' section under Government approval polls.")


def fetch_table_wikitext():
    section_index = find_table_of_polls_section()
    data = api_get(
        {
            "action": "parse",
            "page": PAGE_TITLE,
            "prop": "wikitext",
            "section": section_index,
        }
    )
    return data["parse"]["wikitext"]["*"]


def strip_wikilinks(text):
    # [[Target|Label]] -> Label, [[Target]] -> Target
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    return text


def clean_cell(text):
    text = strip_wikilinks(text)
    text = re.sub(r"<ref[^>]*/?>.*?</ref>|<ref[^>]*/>", "", text, flags=re.DOTALL)
    text = re.sub(r"style\s*=\s*\"[^\"]*\"\s*\|", "", text)
    text = text.replace("'''", "")
    text = re.sub(r"\{\{white\|(.*?)\}\}", r"\1", text)
    text = re.sub(r"\{\{nowrap\|(.*?)\}\}", r"\1", text)
    text = text.replace("\u00A0", " ")
    text = text.strip()
    return text


def parse_date(cell):
    match = re.search(r"\{\{dts\|([^}]+)\}\}", cell)
    if not match:
        return None
    raw_date = match.group(1).strip()
    return pd.to_datetime(raw_date, format="%B %d, %Y")


def parse_percent(cell):
    cell = clean_cell(cell)
    if "N/A" in cell or cell in ("", "-", "\u2014"):
        return "\u2014N/a"
    match = re.search(r"[+-]?\d+(?:\.\d+)?%", cell)
    return match.group(0) if match else cell


def parse_margin_of_error(cell):
    cell = clean_cell(cell)
    if "N/A" in cell or cell in ("", "-", "\u2014"):
        return "\u2014N/a"
    return re.sub(r"\s+", " ", cell)


def parse_row(row_text):
    cells = row_text.split("||")
    if len(cells) < 10:
        return None

    firm = clean_cell(cells[0].strip().lstrip("|").strip())
    date = parse_date(cells[1])
    if date is None:
        return None

    approve = parse_percent(cells[3])
    disapprove = parse_percent(cells[4])
    unsure = parse_percent(cells[5])
    moe = parse_margin_of_error(cells[6])
    sample_size = clean_cell(cells[7])
    method = clean_cell(cells[8])
    net_approval = parse_percent(cells[9]).lstrip("+")

    return {
        "Polling_firm": firm,
        "Last_date_of_polling": date,
        "Approve": approve,
        "Disapprove": disapprove,
        "Unsure/neither": unsure,
        "Margin_of_error": moe,
        "Sample_size": sample_size,
        "Polling_method": method,
        "Net_approval": net_approval,
    }


def parse_wikitext_table(wikitext):
    rows = []
    for row_text in wikitext.split("\n|-"):
        if "{{dts|" not in row_text:
            continue
        row = parse_row(row_text)
        if row is not None:
            rows.append(row)

    if not rows:
        raise RuntimeError("Parsed zero rows from the Government approval polls wikitext table.")

    return pd.DataFrame(rows, columns=CSV_COLUMNS)


def main():
    wikitext = fetch_table_wikitext()
    scraped = parse_wikitext_table(wikitext)

    excluded = scraped[scraped["Polling_firm"].isin(EXCLUDED_FIRMS)]
    if not excluded.empty:
        print(f"Skipping {len(excluded)} row(s) from excluded firms: {sorted(excluded['Polling_firm'].unique())}")
    scraped = scraped[~scraped["Polling_firm"].isin(EXCLUDED_FIRMS)].copy()

    existing = pd.read_csv(CSV_PATH)
    existing["Last_date_of_polling"] = pd.to_datetime(existing["Last_date_of_polling"], format="%d-%b-%y")

    existing_keys = set(zip(existing["Polling_firm"], existing["Last_date_of_polling"]))
    scraped["_key"] = list(zip(scraped["Polling_firm"], scraped["Last_date_of_polling"]))
    new_rows = scraped[~scraped["_key"].isin(existing_keys)].drop(columns="_key")

    if new_rows.empty:
        print("No new polls found; CSV is already up to date.")
        NEW_POLLS_SUMMARY_PATH.write_text("", encoding="utf-8")
        return

    combined = pd.concat([existing, new_rows], ignore_index=True)
    # Stable sort so ties on the same date keep their existing relative order
    # (Wikipedia orders same-date polls by publication time; a quicksort
    # would needlessly shuffle rows that are already in the right order).
    combined = combined.sort_values("Last_date_of_polling", ascending=False, kind="mergesort")
    combined["Last_date_of_polling"] = combined["Last_date_of_polling"].dt.strftime("%d-%b-%y")

    # Match the CSV's existing conventions: CRLF line endings and a UTF-8 BOM.
    combined.to_csv(CSV_PATH, index=False, encoding="utf-8-sig", lineterminator="\r\n")

    new_rows = new_rows.sort_values("Last_date_of_polling", ascending=False)
    summary_lines = [
        f"- **{row['Polling_firm']}** ({row['Last_date_of_polling'].strftime('%d-%b-%y')}): "
        f"Approve {row['Approve']}, Disapprove {row['Disapprove']}, Net {row['Net_approval']}"
        for _, row in new_rows.iterrows()
    ]
    NEW_POLLS_SUMMARY_PATH.write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"Added {len(new_rows)} new poll(s):")
    for line in summary_lines:
        print(f"  {line}")


if __name__ == "__main__":
    main()
