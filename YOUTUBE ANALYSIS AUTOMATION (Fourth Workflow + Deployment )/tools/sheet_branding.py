"""Shared brand styling for the tracking Google Sheets (banner, header row, colors, logo)."""

from pathlib import Path

from googleapiclient.http import MediaFileUpload

BANNER_ROWS = 3
HEADER_ROW_INDEX = BANNER_ROWS  # zero-based; the header sits in sheet row 4
LOGO_HEIGHT, LOGO_WIDTH = 120, 234
COLUMN_WIDTH = 180


def rgb(hex_color: str) -> dict:
    h = hex_color.lstrip("#")
    return {
        "red": int(h[0:2], 16) / 255,
        "green": int(h[2:4], 16) / 255,
        "blue": int(h[4:6], 16) / 255,
    }


def upload_logo(drive, logo: Path) -> str:
    meta = {"name": "Brand logo (tracker banner)", "mimeType": "image/png"}
    media = MediaFileUpload(str(logo), mimetype="image/png")
    file_id = (
        drive.files().create(body=meta, media_body=media, fields="id").execute()["id"]
    )
    drive.permissions().create(
        fileId=file_id, body={"type": "anyone", "role": "reader"}
    ).execute()
    return f"https://drive.google.com/uc?export=view&id={file_id}"


def banner_rows(
    title: str, columns: int, logo_url: str | None, style: dict
) -> list[list]:
    first = (
        f'=IMAGE("{logo_url}",4,{LOGO_HEIGHT},{LOGO_WIDTH})'
        if logo_url
        else style["company"]
    )
    rows = [[first], [title], [f"{style['company']}  |  {style['tagline']}"]]
    return [row + [""] * (columns - 1) for row in rows]


def format_requests(sheet_id: int, columns: int, style: dict) -> list[dict]:
    p = style["palette"]
    navy, blue = rgb(p["background"]), rgb(p["accent"])
    white, muted = rgb(p["heading"]), rgb(p["muted"])
    heading, body = style["font_heading"], style["font_body"]

    def grid(r0, r1, c0, c1):
        return {
            "sheetId": sheet_id,
            "startRowIndex": r0,
            "endRowIndex": r1,
            "startColumnIndex": c0,
            "endColumnIndex": c1,
        }

    def text(font, size, bold, color):
        return {
            "fontFamily": font,
            "fontSize": size,
            "bold": bold,
            "foregroundColor": color,
        }

    def repeat(r0, r1, c0, c1, fmt, fields):
        return {
            "repeatCell": {
                "range": grid(r0, r1, c0, c1),
                "cell": {"userEnteredFormat": fmt},
                "fields": f"userEnteredFormat({fields})",
            }
        }

    def row_height(index, px):
        return {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": index,
                    "endIndex": index + 1,
                },
                "properties": {"pixelSize": px},
                "fields": "pixelSize",
            }
        }

    return [
        repeat(
            0,
            BANNER_ROWS,
            0,
            columns,
            {"backgroundColor": navy, "textFormat": text(body, 10, False, white)},
            "backgroundColor,textFormat",
        ),
        repeat(
            1, 2, 0, 1, {"textFormat": text(heading, 18, True, white)}, "textFormat"
        ),
        repeat(2, 3, 0, 1, {"textFormat": text(body, 10, False, muted)}, "textFormat"),
        repeat(
            HEADER_ROW_INDEX,
            HEADER_ROW_INDEX + 1,
            0,
            columns,
            {"backgroundColor": blue, "textFormat": text(heading, 10, True, white)},
            "backgroundColor,textFormat",
        ),
        row_height(0, 140),
        row_height(1, 34),
        row_height(2, 26),
        row_height(HEADER_ROW_INDEX, 30),
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": columns,
                },
                "properties": {"pixelSize": COLUMN_WIDTH},
                "fields": "pixelSize",
            }
        },
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": HEADER_ROW_INDEX + 1},
                    "tabColor": blue,
                },
                "fields": "gridProperties.frozenRowCount,tabColor",
            }
        },
    ]


def sheet_ids(sheets, sid: str) -> dict:
    meta = sheets.get(
        spreadsheetId=sid, fields="sheets(properties(sheetId,title))"
    ).execute()
    return {
        s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]
    }


def setup_tabs(
    sheets,
    sid: str,
    headers: dict,
    ids: dict,
    title_prefix: str,
    logo_url: str | None,
    style: dict,
) -> None:
    value_data, format_reqs = [], []
    for tab, header in headers.items():
        rows = banner_rows(f"{title_prefix}: {tab}", len(header), logo_url, style) + [
            header
        ]
        value_data.append({"range": f"'{tab}'!A1", "values": rows})
        format_reqs += format_requests(ids[tab], len(header), style)
    sheets.values().batchUpdate(
        spreadsheetId=sid,
        body={"valueInputOption": "USER_ENTERED", "data": value_data},
    ).execute()
    sheets.batchUpdate(spreadsheetId=sid, body={"requests": format_reqs}).execute()


def append_rows(sheets, sid: str, tab: str, rows: list[list]) -> None:
    if rows:
        sheets.values().append(
            spreadsheetId=sid,
            range=f"'{tab}'!A{HEADER_ROW_INDEX + 1}",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()
