#!/usr/bin/env python3
"""Export Yandex Music library (likes, playlists) to local JSON files."""

import argparse
import json
import sys
from pathlib import Path

from yandex_music import Client


def load_token(path: Path) -> str:
    token = path.read_text().strip()
    if not token:
        raise SystemExit(f"empty token file: {path}")
    return token


def track_to_dict(track) -> dict:
    return {
        "id": str(track.id) if track.id is not None else None,
        "title": track.title,
        "version": track.version,
        "artists": [a.name for a in (track.artists or [])],
        "artist_ids": [str(a.id) for a in (track.artists or []) if a.id is not None],
        "albums": [
            {"id": str(a.id), "title": a.title, "year": a.year}
            for a in (track.albums or [])
        ],
        "duration_ms": track.duration_ms,
        "available": track.available,
        "lyrics_available": bool(track.lyrics_available),
        "explicit": track.content_warning == "explicit" if track.content_warning else False,
    }


def export_liked(client: Client) -> list[dict]:
    likes = client.users_likes_tracks()
    if not likes:
        return []
    full = likes.fetch_tracks()
    return [track_to_dict(t) for t in full]


def export_playlists(client: Client) -> list[dict]:
    result = []
    for pl in client.users_playlists_list() or []:
        result.append({
            "kind": pl.kind,
            "title": pl.title,
            "track_count": pl.track_count,
            "duration_ms": pl.duration_ms,
            "modified": str(pl.modified) if pl.modified else None,
            "visibility": pl.visibility,
        })
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--token-file", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=Path("data"))
    args = ap.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    token = load_token(args.token_file)
    print(f"[info] token loaded ({len(token)} chars)", file=sys.stderr)

    client = Client(token).init()
    status = client.account_status()
    acc = status.account
    print(f"[info] logged in as: {acc.display_name} (uid={acc.uid})", file=sys.stderr)

    liked = export_liked(client)
    print(f"[info] liked tracks: {len(liked)}", file=sys.stderr)
    (args.output / "liked.json").write_text(
        json.dumps(liked, ensure_ascii=False, indent=2)
    )

    playlists = export_playlists(client)
    print(f"[info] own playlists: {len(playlists)}", file=sys.stderr)
    (args.output / "playlists.json").write_text(
        json.dumps(playlists, ensure_ascii=False, indent=2)
    )

    artists = sorted({a for t in liked for a in t["artists"]})
    print(f"[info] unique liked artists: {len(artists)}", file=sys.stderr)

    print(f"[done] output in {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
