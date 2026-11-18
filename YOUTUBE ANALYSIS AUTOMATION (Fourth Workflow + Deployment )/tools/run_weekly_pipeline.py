"""Run the full weekly YouTube analysis unattended (local or on Modal).

Runs the SOP steps in order by calling the existing tools. Stops at the first failing step,
emails a short failure notice to REPORT_RECIPIENT, and exits non-zero.

State: the three files the tools rewrite (tracked channels, tracking sheet, channel sheet) are
restored from STATE_DIR before the run and copied back after it. On the first run the copies
shipped with the project are used. If STATE_DIR does not exist, state is not persisted.

Usage:
    python tools/run_weekly_pipeline.py [--no-send] [--skip-upload] [--topic-index N]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.utils import PROJECT_ROOT, ensure_tmp_dir, load_config, redact

TZ = ZoneInfo("Asia/Karachi")
STATE_DIR = Path(os.getenv("STATE_DIR", "/state"))
STATE_FILES = ["tracked_channels.json", "tracking_sheet.json", "channel_sheet.json"]
TAIL_LINES = 15


class StepFailed(RuntimeError):
    def __init__(self, step: str, detail: str):
        super().__init__(f"{step} failed")
        self.step = step
        self.detail = detail


def run_step(step: str, *args: str) -> str:
    """Run one tool and return its redacted output; raise StepFailed on a non-zero exit."""
    print(f"== {step}", flush=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    output = redact(proc.stdout + proc.stderr)
    if output.strip():
        print(output.strip(), flush=True)
    if proc.returncode != 0:
        tail = "\n".join(output.strip().splitlines()[-TAIL_LINES:])
        if re.search(r"quota ?exceeded", output, re.IGNORECASE):
            tail = (
                "YouTube daily quota is used up. Not retried; the next run is Monday.\n"
                + tail
            )
        raise StepFailed(step, tail)
    return output


def pick_topic(index: int | None) -> dict:
    topics = load_config("weekly_topics.json")["topics"]
    if index is None:
        index = datetime.now(TZ).isocalendar().week
    return topics[index % len(topics)]


def restore_state() -> None:
    if not STATE_DIR.exists():
        return
    for name in STATE_FILES:
        src = STATE_DIR / name
        if src.exists():
            shutil.copy2(src, PROJECT_ROOT / "config" / name)


def save_state() -> None:
    if not STATE_DIR.exists():
        return
    for name in STATE_FILES:
        src = PROJECT_ROOT / "config" / name
        if src.exists():
            shutil.copy2(src, STATE_DIR / name)


def analyze(topic: dict | None) -> None:
    args = ["tools/analyze_youtube_trends.py"]
    if topic and topic.get("pattern"):
        args += ["--topic-pattern", topic["pattern"], "--topic-label", topic["label"]]
    run_step("analyze", *args)


def send_failure_email(step: str, detail: str) -> None:
    """Plain notice to REPORT_RECIPIENT. Never includes secrets (output is redacted)."""
    from email.mime.text import MIMEText
    import base64

    from googleapiclient.discovery import build

    from tools.utils import get_env, get_google_credentials

    msg = MIMEText(
        f"The weekly YouTube analysis stopped at step: {step}\n\nLast output lines:\n{detail}\n",
        "plain",
        "utf-8",
    )
    msg["To"] = get_env("REPORT_RECIPIENT")
    msg["Subject"] = f"YouTube analysis FAILED at {step}"
    raw = {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}
    service = build("gmail", "v1", credentials=get_google_credentials())
    service.users().messages().send(userId="me", body=raw).execute()


def run_pipeline(no_send: bool, skip_upload: bool, topic_index: int | None) -> int:
    topic = pick_topic(topic_index)
    print(f"Topic for this run: {topic['label']}", flush=True)
    ensure_tmp_dir()
    restore_state()
    try:
        run_step("discover channels", "tools/youtube_discover_channels.py")
        fetched = run_step("fetch videos", "tools/youtube_fetch_videos.py")
        match = re.search(r"Fetched (\d+) videos", fetched)
        if not match or int(match.group(1)) == 0:
            raise StepFailed(
                "fetch videos", "No videos were fetched. Check the channel list."
            )

        analyze(topic)
        run_step("charts", "tools/generate_charts.py")
        run_step(
            "narrative", "tools/generate_narrative.py", "--topic-label", topic["label"]
        )

        pdf_args = ["tools/build_pdf_report.py"]
        if skip_upload:
            pdf_args.append("--skip-upload")
        run_step("PDF report", *pdf_args)
        run_step("Slides deck", "tools/build_slides_deck.py")
        deck_url = json.loads(
            (PROJECT_ROOT / ".tmp" / "deck_result.json").read_text(encoding="utf-8")
        )["url"]

        # SOP step 5: logs and channel data use the full niche, not the topic scope.
        analyze(None)
        run_step("charts (full niche)", "tools/generate_charts.py")
        run_step(
            "tracking sheet", "tools/update_tracking_sheet.py", "--deck-url", deck_url
        )
        run_step("channel sheet", "tools/update_channel_sheet.py")

        sheet_url = load_config("tracking_sheet.json")["spreadsheet_url"]
        mail_args = [
            "tools/send_gmail_notification.py",
            "--deck-url",
            deck_url,
            "--sheet-url",
            sheet_url,
        ]
        if not no_send:
            mail_args.append("--send")
        run_step("email", *mail_args)
        print("Run complete.", flush=True)
        return 0
    except StepFailed as err:
        print(f"STOPPED: {err.step}\n{err.detail}", flush=True)
        try:
            send_failure_email(err.step, err.detail)
        except Exception as mail_err:  # the failure notice is best-effort
            print(f"Could not send failure email: {redact(str(mail_err))}", flush=True)
        return 1
    finally:
        save_state()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-send",
        action="store_true",
        help="Build everything but do not send the email.",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Keep the PDF local, do not upload to Drive.",
    )
    parser.add_argument(
        "--topic-index",
        type=int,
        default=None,
        help="Pick a topic by position instead of the week.",
    )
    args = parser.parse_args()
    return run_pipeline(args.no_send, args.skip_upload, args.topic_index)


if __name__ == "__main__":
    sys.exit(main())
