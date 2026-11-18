"""Modal deployment of the YouTube analysis. Runs on demand only (no schedule).

Only tools/, config/, assets/ and Brand_Assets/ are packaged into the image. .env and token.json
never enter the image; they live in the Modal secret "youtube-analysis-secrets". The three files
the tools rewrite are kept in the Modal volume "youtube-analysis-state".

One-time setup:
    python -m pip install modal
    python -m modal setup
    python -m modal volume create youtube-analysis-state
    python -m modal secret create youtube-analysis-secrets --from-json <file>   (see workflow SOP)
    python -m modal deploy modal_app.py

On-demand runs (nothing runs automatically):
    python -m modal run modal_app.py --no-send        # build everything, skip the email
    python -m modal run modal_app.py                  # full run, sends the email
"""

from pathlib import Path

import modal

PROJECT = Path(__file__).resolve().parent
REMOTE = "/app"

app = modal.App("youtube-analysis")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements(str(PROJECT / "requirements.txt"))
    .env({"STATE_DIR": "/state", "PYTHONIOENCODING": "utf-8"})
    .workdir(REMOTE)
    # Local files go last so code edits do not force an image rebuild.
    .add_local_dir(
        str(PROJECT / "tools"), f"{REMOTE}/tools", ignore=["__pycache__", "*.pyc"]
    )
    .add_local_dir(str(PROJECT / "config"), f"{REMOTE}/config")
    .add_local_dir(str(PROJECT / "assets"), f"{REMOTE}/assets")
    .add_local_dir(str(PROJECT / "Brand_Assets"), f"{REMOTE}/Brand_Assets")
)

secret = modal.Secret.from_name("youtube-analysis-secrets")
state = modal.Volume.from_name("youtube-analysis-state", create_if_missing=True)


@app.function(
    image=image,
    secrets=[secret],
    volumes={"/state": state},
    timeout=60 * 60,
    retries=0,  # a retry could append sheet rows twice or send two emails
)
def run_weekly(no_send: bool = False, topic_index: int = -1) -> None:
    import sys

    sys.path.insert(0, REMOTE)
    from tools.run_weekly_pipeline import run_pipeline

    code = run_pipeline(
        no_send=no_send,
        skip_upload=False,
        topic_index=None if topic_index < 0 else topic_index,
    )
    state.commit()
    if code:
        raise RuntimeError(
            "Weekly YouTube analysis failed. See the failure email for the step."
        )


@app.local_entrypoint()
def main(no_send: bool = False, topic_index: int = -1) -> None:
    run_weekly.remote(no_send=no_send, topic_index=topic_index)
