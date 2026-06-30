#!/usr/bin/env python3
"""Import Yandex Music liked tracks into ListenBrainz as historical listens.

Reads data/liked.json, submits each as a listen to POST /1/submit-listens with
type=import. Timestamps are spread evenly across the past year so the history
looks organic (one track every N seconds). Batches of 1000 per request.
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

import requests

LBZ_API = "https://api.listenbrainz.org/1/submit-listens"
BATCH_SIZE = 1000


def load_token(path: Path) -> str:
    token = path.read_text().strip()
    if not token:
        raise SystemExit(f"empty token file: {path}")
    return token


def load_liked(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def make_listen(track: dict, ts: int) -> dict:
    artist = track["artists"][0] if track["artists"] else "Unknown Artist"
    album = track["albums"][0]["title"] if track["albums"] else None
    duration_ms = track.get("duration_ms") or 0

    additional: dict = {
        "submission_client": "yamusic-export",
        "submission_client_version": "0.1",
        "music_service": "music.yandex.ru",
    }
    if duration_ms:
        additional["duration_ms"] = duration_ms
    if track.get("artist_ids"):
        additional["artist_mbids"] = []  # unknown, leave empty
    if track.get("id"):
        additional["music_service_name"] = "yandex_music"
        additional["origin_url"] = f"https://music.yandex.ru/track/{track['id']}"
    if track["artists"]:
        additional["artist_names"] = track["artists"]
    if album:
        additional["release_name"] = album

    listen = {
        "listened_at": ts,
        "track_metadata": {
            "artist_name": artist,
            "track_name": track["title"] or "Unknown Track",
            "additional_info": additional,
        },
    }
    if album:
        listen["track_metadata"]["release_name"] = album
    return listen


def distribute_timestamps(count: int, end_ts: int | None = None, span_days: int = 365) -> list[int]:
    """Spread `count` listens across the last `span_days`, slightly jittered."""
    if end_ts is None:
        end_ts = int(time.time())
    start_ts = end_ts - span_days * 86400
    span = end_ts - start_ts
    step = span / max(count, 1)
    timestamps = []
    for i in range(count):
        base = start_ts + int(i * step)
        # jitter ±step/2 so timestamps aren't perfectly evenly spaced
        jitter = random.randint(-int(step / 2), int(step / 2))
        timestamps.append(base + jitter)
    timestamps.sort()
    return timestamps


def submit_batch(token: str, listens: list[dict]) -> dict:
    payload = {
        "listen_type": "import",
        "payload": listens,
    }
    r = requests.post(
        LBZ_API,
        headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token-file", type=Path, required=True)
    ap.add_argument("--liked", type=Path, default=Path("data/liked.json"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--span-days", type=int, default=365)
    args = ap.parse_args()

    token = load_token(args.token_file)
    liked = load_liked(args.liked)

    available = [t for t in liked if t.get("available") and t.get("title") and t.get("artists")]
    print(f"[info] total tracks in liked.json: {len(liked)}", file=sys.stderr)
    print(f"[info] usable (available + titled): {len(available)}", file=sys.stderr)

    timestamps = distribute_timestamps(len(available), span_days=args.span_days)

    listens = [make_listen(track, ts) for track, ts in zip(available, timestamps)]

    if args.dry_run:
        print("\n[dry-run] first 3 listens:", file=sys.stderr)
        print(json.dumps(listens[:3], ensure_ascii=False, indent=2))
        print(f"\n[dry-run] last listen ts: {listens[-1]['listened_at']}", file=sys.stderr)
        return 0

    print(f"[info] submitting {len(listens)} listens in batches of {BATCH_SIZE}...", file=sys.stderr)
    submitted = 0
    for i in range(0, len(listens), BATCH_SIZE):
        batch = listens[i:i + BATCH_SIZE]
        try:
            resp = submit_batch(token, batch)
            submitted += len(batch)
            print(f"[batch {i // BATCH_SIZE + 1}] ok, total submitted: {submitted}", file=sys.stderr)
        except requests.HTTPError as e:
            print(f"[batch {i // BATCH_SIZE + 1}] FAILED: {e}", file=sys.stderr)
            print(f"response: {e.response.text[:500] if e.response else ''}", file=sys.stderr)
            return 1
        time.sleep(1.0)

    print(f"[done] {submitted} listens imported", file=sys.stderr)
    print("[info] daily jams will appear after listenbrainz cron ~04:00 UTC", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
