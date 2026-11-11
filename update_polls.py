"""Fetch new Carney government approval polls from Wikipedia and append them to the local CSV.

This data pipeline directly pulls the raw wikitext (rather than the rendered HTML) of the "Table of polls" subsection under "Government approval polls" via the
MediaWiki API and parses the syntax directly. New rows are merged
into the existing CSV (deduped on firm + date) and written back in the same
newest-first order and formatting the CSV already uses.
"""

import re
from pathlib import Path

import pandas as pd
import requests
import wikitextparser as wtp

API_URL = "https://en.wikipedia.org/w/api.php"
PAGE_TITLE = "Opinion polling for the 46th Canadian federal election"
CSV_PATH = Path("carney government approval polls.csv")
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


# See bottom for Readme.md.
EXCLUDED_FIRMS = {
    "Nanos Research",
    "Mainstreet Research",
    "Pallas Data",
    "Kolosowski Strategies",
    "Pollera",
}

HEADERS = {"User-Agent": "carney-approval-wikipedia-scraper (open source project)"}


def api_get(params: dict) -> dict:
    """
    Fetch data from the MediaWiki API.
    """
    try:
        params = {**params, "format": "json"}

        response = requests.get(
            API_URL,
            params=params,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch data from Wikipedia API: {e}")


def find_table_of_polls_section() -> str:
    """
    Locate the 'Table of polls' section nested under 'Government approval polls'.
    """
    data = api_get(
        {
            "action": "parse",
            "page": PAGE_TITLE,
            "prop": "sections",
        }
    )
    sections = data["parse"]["sections"]

    in_government_approval = False

    for section in sections:
        title = section["line"]
        level = section["toclevel"]

        if level == 1:
            in_government_approval = title == "Government approval polls"

        if in_government_approval and title == "Table of polls":
            return section["index"]

    raise RuntimeError(
        "Could not find the 'Table of polls' section under Government approval polls."
    )


def fetch_table_wikitext() -> str:
    """
    Fetch the raw wikitext of the "Table of polls" subsection."
    """
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


def clean_cell(text: str) -> str:
    """
    Clean up a cell's text by removing wiki markup, references, and extra whitespace
    """
    parsed = wtp.parse(text)

    for tag in parsed.get_tags("ref"):
        tag.string = ""

    text = parsed.plain_text()

    return text.replace("\u00a0", " ").strip()


def parse_date(cell: str) -> pd.Timestamp | None:
    """
    Parse a date from a wikitext cell.
    """
    raw_date = clean_cell(cell)

    if not raw_date:
        return None

    try:
        return pd.to_datetime(raw_date, format="%B %d, %Y")
    except (ValueError, TypeError):
        return None


def parse_percent(cell: str) -> str:
    """
    Parse a percentage from a wikitext cell.
    """
    cell = clean_cell(cell)

    if "N/A" in cell or cell in ("N/A", "-", "—"):
        return "—N/a"

    match = re.search(r"[+-]?\d+(?:\.\d+)?%", cell)

    return match.group(0) if match else cell


def parse_margin_of_error(cell: str) -> str:
    """
    Parse the margin of error from a wikitext cell.
    """
    cell = clean_cell(cell)

    if not cell or cell in ("N/A", "-", "—"):
        return "—N/a"

    return " ".join(cell.split())


def parse_row(cells):
    """
    Parse a single row of the wikitext table into a dictionary.
    """
    if len(cells) < 10:
        return None

    firm = clean_cell(cells[0])
    date = parse_date(cells[1])

    if date is None:
        return None

    approve = parse_percent(cells[3])
    disapprove = parse_percent(cells[4])
    net = parse_percent(cells[8]).lstrip("+")

    if not net or net == "—N/a":
        try:
            app_val = float(approve.rstrip("%"))
            dis_val = float(disapprove.rstrip("%"))
            diff = app_val - dis_val
            net = f"{int(diff)}%" if diff.is_integer() else f"{diff:.1f}%"
        except ValueError:
            net = "—N/a"

    return {
        "Polling_firm": firm,
        "Last_date_of_polling": date,
        "Approve": approve,
        "Disapprove": disapprove,
        "Unsure/neither": parse_percent(cells[5]),
        "Margin_of_error": parse_margin_of_error(cells[6]),
        "Sample_size": clean_cell(cells[7]),
        "Polling_method": clean_cell(cells[8]),
        "Net_approval": net,
    }


def parse_wikitext_table(wikitext: str) -> pd.DataFrame:
    """
    Parse the wikitext of the "Table of polls" into a Pandas DataFrame.
    """
    parsed = wtp.parse(wikitext)
    table = parsed.tables[0]

    rows = []

    for cells in table.data()[2:]:
        row = parse_row(cells)

        if row is not None:
            rows.append(row)

    if not rows:
        raise RuntimeError(
            "Parsed zero rows from the Government approval polls wikitext table."
        )

    return pd.DataFrame(rows, columns=CSV_COLUMNS)


def main() -> None:
    """
    Main function to update the polling data.
    """
    wikitext = fetch_table_wikitext()
    scraped = parse_wikitext_table(wikitext)

    excluded = scraped[scraped["Polling_firm"].isin(EXCLUDED_FIRMS)]
    if not excluded.empty:
        print(
            f"Skipping {len(excluded)} row(s) from excluded firms: {sorted(excluded['Polling_firm'].unique())}"
        )
    scraped = scraped[~scraped["Polling_firm"].isin(EXCLUDED_FIRMS)].copy()

    existing = pd.read_csv(CSV_PATH)
    existing["Last_date_of_polling"] = pd.to_datetime(
        existing["Last_date_of_polling"], format="%d-%b-%y"
    )

    existing_keys = set(zip(existing["Polling_firm"], existing["Last_date_of_polling"]))
    scraped["_key"] = list(
        zip(scraped["Polling_firm"], scraped["Last_date_of_polling"])
    )
    new_rows = scraped[~scraped["_key"].isin(existing_keys)].drop(columns="_key")

    if new_rows.empty:
        print("No new polls found; CSV is already up to date.")
        return

    combined = pd.concat([existing, new_rows], ignore_index=True)
  
    combined = combined.sort_values(
        "Last_date_of_polling", ascending=False, kind="mergesort"
    )
    combined["Last_date_of_polling"] = combined["Last_date_of_polling"].dt.strftime(
        "%d-%b-%y"
    )

    combined.to_csv(CSV_PATH, index=False, encoding="utf-8-sig", lineterminator="\r\n")

    new_rows = new_rows.sort_values("Last_date_of_polling", ascending=False)
    summary_lines = [
        f"- {row['Polling_firm']} ({row['Last_date_of_polling'].strftime('%d-%b-%y')}): "
        f"Approve {row['Approve']}, Disapprove {row['Disapprove']}, Net {row['Net_approval']}"
        for _, row in new_rows.iterrows()
    ]

    print(f"Added {len(new_rows)} new poll(s):")
    for line in summary_lines:
        print(f"  {line}")


if __name__ == "__main__":
    main()
