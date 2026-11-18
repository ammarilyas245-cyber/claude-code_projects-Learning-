#!/usr/bin/env python3
"""
Export job listings JSON to a formatted Excel spreadsheet.

Usage:
    python tools/export_jobs_excel.py --input .tmp/jobs_full.json --output .tmp/social_media_jobs.xlsx
"""

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

load_dotenv()

COLUMNS = [
    ("Title", "title"),
    ("Company", "company"),
    ("Job Type", "job_type"),
    ("Location", "location"),
    ("Salary", "salary"),
    ("Experience", "experience"),
    ("Category", "category"),
    ("Date Posted", "date_posted"),
    ("Tags", "tags"),
    ("Description Snippet", "description_snippet"),
    ("Full Description", "full_description"),
    ("Job URL", "job_url"),
]

HEADER_FILL = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
URL_FONT = Font(color="0563C1", underline="single")

# Max column widths (in Excel character units)
MAX_WIDTHS = {
    "Title": 45,
    "Company": 30,
    "Job Type": 14,
    "Location": 25,
    "Salary": 20,
    "Experience": 18,
    "Category": 20,
    "Date Posted": 18,
    "Tags": 35,
    "Description Snippet": 60,
    "Full Description": 80,
    "Job URL": 55,
}


def build_excel(jobs: list, output_path: Path) -> int:
    wb = Workbook()
    ws = wb.active
    ws.title = "Job Listings"

    # Header row
    for col_idx, (header, _) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=False
        )

    ws.row_dimensions[1].height = 20
    ws.freeze_panes = "A2"

    # Data rows
    for row_idx, job in enumerate(jobs, start=2):
        for col_idx, (header, field) in enumerate(COLUMNS, start=1):
            value = job.get(field, "") or ""
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(
                vertical="top", wrap_text=(header == "Full Description")
            )

            if header == "Job URL" and value:
                cell.hyperlink = value
                cell.font = URL_FONT
                cell.value = value

    # Auto-width columns (sample first 100 rows for performance)
    for col_idx, (header, field) in enumerate(COLUMNS, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = len(header)
        sample_rows = jobs[:100]
        for job in sample_rows:
            val = str(job.get(field, "") or "")
            # For multi-line fields, use the longest line
            cell_len = max((len(line) for line in val.split("\n")), default=0)
            max_len = max(max_len, cell_len)

        # Clamp to defined maximum
        clamped = min(max_len + 2, MAX_WIDTHS.get(header, 30))
        ws.column_dimensions[col_letter].width = clamped

    # Row height for description rows (auto-sized by Excel; set a reasonable default)
    for row_idx in range(2, len(jobs) + 2):
        ws.row_dimensions[row_idx].height = 15

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return len(jobs)


def main():
    parser = argparse.ArgumentParser(description="Export job listings JSON to Excel")
    parser.add_argument("--input", required=True, help="Path to jobs JSON file")
    parser.add_argument("--output", required=True, help="Output .xlsx file path")
    args = parser.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            raw = json.load(f)
        jobs = raw.get("data", raw) if isinstance(raw, dict) else raw

        if not jobs:
            raise ValueError("No job records found in input file")

        output_path = Path(args.output)
        count = build_excel(jobs, output_path)

        # Auto-open the file with the default application
        resolved = output_path.resolve()
        if platform.system() == "Windows":
            os.startfile(str(resolved))
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(resolved)])
        else:
            subprocess.Popen(["xdg-open", str(resolved)])

        result = {
            "status": "success",
            "count": count,
            "output_path": str(resolved),
        }
        print(json.dumps(result))
        return 0

    except Exception as e:
        print(
            json.dumps(
                {"status": "error", "error": str(e), "error_type": type(e).__name__}
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
