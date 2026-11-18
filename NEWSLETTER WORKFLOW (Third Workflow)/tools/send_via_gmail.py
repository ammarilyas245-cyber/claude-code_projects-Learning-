"""Send the assembled newsletter through the Gmail API.

Base64 images in the HTML are converted to inline CID attachments (Gmail blocks data: images).
Safe by default: with no flag it only validates and prints who it WOULD send to.

Usage:
    python tools/send_via_gmail.py --html .tmp/newsletter_<topic>.html --subject "..."            # dry run
    python tools/send_via_gmail.py --html ... --subject "..." --test                              # NEWSLETTER_TEST_RECIPIENT only
    python tools/send_via_gmail.py --html ... --subject "..." --send                              # full list in config/recipients.json
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.utils import PROJECT_ROOT, ensure_tmp_dir, get_google_credentials, load_env

DATA_URI = re.compile(r"data:image/(png|jpeg|jpg);base64,([A-Za-z0-9+/=]+)")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def split_images(html: str):
    """Replace data: URIs with cid: references, returning (html, [(cid, subtype, bytes)])."""
    images, cache = [], {}

    def repl(m):
        key = m.group(2)
        if key not in cache:
            cache[key] = f"img{len(cache) + 1}@newsletter"
            images.append(
                (cache[key], m.group(1).replace("jpg", "jpeg"), base64.b64decode(key))
            )
        return "cid:" + cache[key]

    return DATA_URI.sub(repl, html), images


def build_message(
    html: str, images, subject: str, sender: str, sender_name: str, to: str
) -> dict:
    root = MIMEMultipart("related")
    root["Subject"], root["To"] = subject, to
    if sender:
        root["From"] = formataddr((sender_name, sender))
    alt = MIMEMultipart("alternative")
    alt.attach(
        MIMEText(
            "Your email client does not display HTML. View this newsletter in a browser-based client.",
            "plain",
        )
    )
    alt.attach(MIMEText(html, "html", "utf-8"))
    root.attach(alt)
    for cid, subtype, raw in images:
        part = MIMEImage(raw, _subtype=subtype)
        part.add_header("Content-ID", f"<{cid}>")
        part.add_header("Content-Disposition", "inline")
        root.attach(part)
    return {"raw": base64.urlsafe_b64encode(root.as_bytes()).decode()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True)
    parser.add_argument("--subject", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--test", action="store_true")
    mode.add_argument("--send", action="store_true")
    args = parser.parse_args()

    load_env()
    cfg = json.loads(
        (PROJECT_ROOT / "config" / "recipients.json").read_text(encoding="utf-8")
    )
    if args.test:
        test = os.getenv("NEWSLETTER_TEST_RECIPIENT", "")
        recipients = [{"name": "Test", "email": test}] if test else []
    else:
        recipients = cfg["recipients"]

    seen, valid = set(), []
    for r in recipients:
        email = r["email"].strip()
        if (
            EMAIL.match(email)
            and not email.endswith("@example.com")
            and email.lower() not in seen
        ):
            seen.add(email.lower())
            valid.append(email)
        else:
            print(f"Skipping invalid or placeholder address: {email!r}")
    if not valid:
        print(
            "No valid recipients. Fill in config/recipients.json (or NEWSLETTER_TEST_RECIPIENT)."
        )
        return 1

    html, images = split_images(Path(args.html).read_text(encoding="utf-8"))
    print(
        f"{len(valid)} recipient(s), {len(images)} inline image(s): {', '.join(valid)}"
    )
    if not (args.test or args.send):
        print("Dry run only. Re-run with --test or --send to deliver.")
        return 0

    from googleapiclient.discovery import build

    service = build("gmail", "v1", credentials=get_google_credentials())
    # gmail.send scope cannot call getProfile (403); Gmail fills in the From address itself
    sender = ""
    log = []
    for email in valid:
        body = build_message(
            html, images, args.subject, sender, cfg.get("sender_name", ""), email
        )
        for attempt in range(3):
            try:
                resp = service.users().messages().send(userId="me", body=body).execute()
                log.append({"email": email, "status": "sent", "id": resp["id"]})
                break
            except Exception as err:
                if attempt == 2:
                    log.append({"email": email, "status": "failed", "error": str(err)})
                time.sleep(2**attempt)
        time.sleep(0.5)
    out = ensure_tmp_dir() / f"send_log_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(log, indent=2), encoding="utf-8")
    sent = sum(1 for e in log if e["status"] == "sent")
    print(f"Sent {sent}/{len(log)}. Log: {out}")
    return 0 if sent == len(log) else 2


if __name__ == "__main__":
    sys.exit(main())
