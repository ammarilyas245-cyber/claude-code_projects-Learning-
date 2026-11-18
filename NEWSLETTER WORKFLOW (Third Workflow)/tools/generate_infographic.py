"""Generate a brand-styled infographic with Kie.ai (Nano Banana Pro).

Flow: createTask -> poll recordInfo until success -> download PNG -> write base64 sidecar.
Makes ONE paid call per run; it never retries automatically.

Usage:
    python tools/generate_infographic.py --input .tmp/research_<topic>.json
Output: .tmp/infographics/<topic>.png and <topic>.png.b64.txt
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.utils import ensure_tmp_dir, get_api_key, load_env, load_style

API = "https://api.kie.ai/api/v1/jobs"


def build_prompt(info: dict, style: dict) -> str:
    points = "\n".join(f"- {p['label']}: {p['value']}" for p in info.get("data_points", []))
    return (
        f"{style['infographic_style_anchor']}\n\n"
        f"Infographic type: {info.get('type', 'stat_cards')}. Title (exact text): \"{info['title']}\".\n"
        f"Show exactly these items with exactly this text:\n{points}\n"
        f"Layout: landscape, generous white space, clear visual hierarchy. Draw exactly {len(info.get('data_points', []))} cards, one per item, "
        "each item shown ONCE only (no repeats, no extra cards), each with one simple blue outline icon above its text (value in large bold primary blue, label in dark navy)."
    )


def create_task(prompt: str, aspect_ratio: str, resolution: str) -> str:
    resp = requests.post(
        f"{API}/createTask",
        headers={"Authorization": f"Bearer {get_api_key('KIE_API_KEY')}"},
        json={
            "model": os.getenv("KIE_IMAGE_MODEL", "nano-banana-pro"),
            "input": {
                "prompt": prompt,
                "image_input": [],
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "output_format": "png",
            },
        },
        timeout=60,
    )
    body = resp.json()
    if body.get("code") != 200:
        raise RuntimeError(f"Kie.ai createTask failed: {body}")
    return body["data"]["taskId"]


def wait_for_result(task_id: str, timeout_s: int = 600) -> str:
    headers = {"Authorization": f"Bearer {get_api_key('KIE_API_KEY')}"}
    delay, start = 3, time.time()
    while time.time() - start < timeout_s:
        body = requests.get(f"{API}/recordInfo", params={"taskId": task_id}, headers=headers, timeout=60).json()
        if body.get("code") != 200:
            raise RuntimeError(f"Kie.ai status check failed: {body}")
        data = body["data"]
        if data["state"] == "success":
            return json.loads(data["resultJson"])["resultUrls"][0]
        if data["state"] == "fail":
            raise RuntimeError(f"Kie.ai generation failed: {data.get('failCode')} {data.get('failMsg')}")
        time.sleep(delay)
        delay = min(delay + 2, 10)
    raise TimeoutError(f"Kie.ai task {task_id} did not finish within {timeout_s}s")


def generate(info: dict, name: str, aspect_ratio: str = "16:9", resolution: str = "2K") -> Path:
    load_env()
    style = load_style()
    task_id = create_task(build_prompt(info, style), aspect_ratio, resolution)
    print(f"Kie.ai task {task_id} created, waiting...")
    url = wait_for_result(task_id)
    img = requests.get(url, timeout=120)
    img.raise_for_status()  # URLs expire after 14 days, so download now
    out_dir = ensure_tmp_dir() / "infographics"
    out_dir.mkdir(exist_ok=True)
    png = out_dir / f"{name}.png"
    png.write_bytes(img.content)
    Path(str(png) + ".b64.txt").write_text(base64.b64encode(img.content).decode(), encoding="ascii")
    return png


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="research JSON from research.py")
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--resolution", default="2K", choices=["1K", "2K", "4K"])
    args = parser.parse_args()

    research = json.loads(Path(args.input).read_text(encoding="utf-8"))
    path = generate(research["infographic"], Path(args.input).stem.removeprefix("research_"), args.aspect_ratio, args.resolution)
    print(f"Saved {path}")
