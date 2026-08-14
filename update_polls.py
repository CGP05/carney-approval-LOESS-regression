#!/usr/bin/env python3
#this script was entirely made by Gemeni and it does not work at all, but i will probably use it as a reference to make one that does function
"""Fetch the Government approval polls data from Wikipedia and save it as a local CSV."""
import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

WIKI_URL = "https://en.wikipedia.org/wiki/Opinion_polling_for_the_46th_Canadian_federal_election"
CSV_PATH = Path("carney government approval polls.csv")
TARGET_COLUMNS = {
    "Polling firm": "Polling_firm",
    "Last date of polling": "Last_date_of_polling",
    "Approve": "Approve",
    "Disapprove": "Disapprove",
    "Unsure/neither": "Unsure/neither",
    "Margin of error": "Margin_of_error",
    "Sample size": "Sample_size",
    "Polling method": "Polling_method",
    "Net approval": "Net_approval",
}


def normalize_header(text):
    text = str(text)
    text = re.sub(r"\[.*?\]", "", text)
    text = text.replace("\u00A0", " ")
    text = text.strip()
    return re.sub(r"\s+", " ", text)


def clean_cell(text):
    if text is None:
        return None
    value = str(text)
    value = re.sub(r"\[.*?\]", "", value)
    value = value.replace("\u00A0", " ")
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    return value or None


def find_approval_table(soup):
    heading = soup.find(id="Government_approval_polls")
    if heading:
        section = heading.find_parent(["h2", "h3"])
        if section:
            table = section.find_next("table")
            if table is not None:
                return table

    for table in soup.find_all("table", class_="wikitable"):
        header_cells = [normalize_header(th.get_text(" ", strip=True)) for th in table.find_all("th")]
        if {"Polling firm", "Approve", "Disapprove"}.issubset(set(header_cells)):
            return table

    raise RuntimeError("Could not find the Government approval polls table on Wikipedia.")


def parse_table(table):
    rows = []
    header = None
    for tr in table.find_all("tr"):
        cells = [clean_cell(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        if not cells:
            continue

        if header is None and tr.find_all("th"):
            normalized = [normalize_header(cell) for cell in cells]
            while normalized and normalized[-1] == "":
                normalized.pop()
            header = normalized
            continue

        if header is None:
            continue

        if len(cells) < len(header):
            continue

        rows.append(cells[: len(header)])

    if header is None or not rows:
        raise RuntimeError("Could not parse rows from the approval polls table.")

    return pd.DataFrame(rows, columns=header)


def coerce_date(series):
    result = pd.to_datetime(series, dayfirst=True, errors="coerce", format="mixed")
    if result.isna().any():
        bad = series[result.isna()].tolist()
        raise ValueError(f"Unable to parse these dates: {bad}")
    return result.dt.strftime("%d-%b-%y")


def main():
    response = requests.get(WIKI_URL, headers={"User-Agent": "carney-approval-wiki-scraper/1.0"}, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    table = find_approval_table(soup)
    df = parse_table(table)

    rename_map = {col: TARGET_COLUMNS[col] for col in df.columns if normalize_header(col) in TARGET_COLUMNS}
    df = df.rename(columns={col: TARGET_COLUMNS[normalize_header(col)] for col in df.columns if normalize_header(col) in TARGET_COLUMNS})

    missing = set(TARGET_COLUMNS.values()) - set(df.columns)
    if missing:
        raise RuntimeError(f"Missing required columns after normalization: {missing}")

    df = df[list(TARGET_COLUMNS.values())]
    df["Last_date_of_polling"] = coerce_date(df["Last_date_of_polling"])
    df["Sample_size"] = df["Sample_size"].astype(str).str.replace(r"\.0$", "", regex=True)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")
    print(f"Wrote {len(df)} rows to {CSV_PATH}")


if __name__ == "__main__":
    main()
