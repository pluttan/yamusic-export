#!/usr/bin/env python3
"""Download Yandex Music liked tracks to a local library tree.

Layout:  <output>/<artist>/<album>/<title>.{mp3,m4a}
         <output>/<artist>/<album>/cover.jpg
"""

import argparse
import re
import socket
import sys
import time
from pathlib import Path

import requests
from mutagen.id3 import APIC, ID3, ID3NoHeaderError, TALB, TDRC, TIT2, TPE1, TRCK
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from tqdm import tqdm
from yandex_music import Client


# ============================================================
# DNS cache + IPv4-preferred monkey patch
# On some hosts glibc returns only IPv6 records for yandex domains,
# and IPv6 isn't routed — python then fails with "name resolution"
# while dig@1.1.1.1 works fine. We cache successful lookups and
# strip IPv6 results so the first working v4 address wins.
# ============================================================
_original_getaddrinfo = socket.getaddrinfo
_dns_cache: dict = {}


def _patched_getaddrinfo(host, port, *args, **kwargs):
    key = (host, port, args, tuple(sorted(kwargs.items())))
    if key in _dns_cache:
        return _dns_cache[key]
    last_err = None
    for attempt in range(8):
        try:
            result = _original_getaddrinfo(host, port, *args, **kwargs)
            v4 = [r for r in result if r[0] == socket.AF_INET]
            if v4:
                _dns_cache[key] = v4
                return v4
            if result:
                _dns_cache[key] = result
                return result
            raise socket.gaierror("no addresses")
        except socket.gaierror as e:
            last_err = e
            time.sleep(min(10.0, (2 ** attempt) * 0.5))
    raise last_err if last_err else socket.gaierror("exhausted retries")


socket.getaddrinfo = _patched_getaddrinfo


def sanitize(s: str | None, max_len: int = 180) -> str:
    if not s:
        return "unknown"
    s = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "_", s)
    s = s.strip(" .")
    return s[:max_len] or "unknown"


def load_token(path: Path) -> str:
    token = path.read_text().strip()
    if not token:
        raise SystemExit(f"empty token file: {path}")
    return token


def download_cover(track, dirpath: Path, session: requests.Session) -> Path | None:
    cover_path = dirpath / "cover.jpg"
    if cover_path.exists() and cover_path.stat().st_size > 0:
        return cover_path
    if not track.cover_uri:
        return None
    url = "https://" + track.cover_uri.replace("%%", "600x600")
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200 and r.content:
            cover_path.write_bytes(r.content)
            return cover_path
    except Exception as e:
        print(f"[warn] cover failed {track.id}: {e}", file=sys.stderr)
    return None


def tag_mp3(path: Path, track, cover: Path | None) -> None:
    audio = MP3(path, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()
    tags = audio.tags
    tags.clear()
    tags.add(TIT2(encoding=3, text=track.title or ""))
    tags.add(TPE1(encoding=3, text=", ".join(a.name for a in (track.artists or []))))
    if track.albums:
        album = track.albums[0]
        tags.add(TALB(encoding=3, text=album.title or ""))
        if album.year:
            tags.add(TDRC(encoding=3, text=str(album.year)))
    if cover and cover.exists():
        tags.add(
            APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="cover",
                data=cover.read_bytes(),
            )
        )
    audio.save(v2_version=3)


def tag_m4a(path: Path, track, cover: Path | None) -> None:
    f = MP4(path)
    f["\xa9nam"] = track.title or ""
    f["\xa9ART"] = ", ".join(a.name for a in (track.artists or []))
    if track.albums:
        album = track.albums[0]
        f["\xa9alb"] = album.title or ""
        if album.year:
            f["\xa9day"] = str(album.year)
    if cover and cover.exists():
        f["covr"] = [
            MP4Cover(cover.read_bytes(), imageformat=MP4Cover.FORMAT_JPEG)
        ]
    f.save()


def retry_net(fn, label: str, retries: int = 6):
    """Retry a function on network errors with exponential backoff."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            if "name resolution" not in msg.lower() and "timed out" not in msg.lower() \
                    and "connection" not in msg.lower():
                raise
            last_err = e
            if attempt < retries - 1:
                wait = min(30.0, (2 ** attempt) * 0.5)
                time.sleep(wait)
    raise last_err if last_err else RuntimeError(f"{label}: unknown retry failure")


def download_one(track, library: Path, session: requests.Session) -> str:
    if not track.available:
        return "skip_unavailable"

    artist = sanitize(track.artists[0].name if track.artists else None)
    album = sanitize(track.albums[0].title if track.albums else None)
    title = sanitize(track.title or f"track_{track.id}")

    dirpath = library / artist / album
    dirpath.mkdir(parents=True, exist_ok=True)

    try:
        dl_info = retry_net(lambda: track.get_download_info(), "get_download_info")
    except Exception as e:
        return f"err_info:{e}"
    if not dl_info:
        return "no_info"

    best = max(
        dl_info,
        key=lambda di: (di.bitrate_in_kbps, 1 if di.codec == "mp3" else 0),
    )
    ext = "mp3" if best.codec == "mp3" else "m4a"
    filepath = dirpath / f"{title}.{ext}"

    if filepath.exists() and filepath.stat().st_size > 1000:
        return "skip_exists"

    try:
        retry_net(lambda: best.download(str(filepath)), "download")
    except Exception as e:
        return f"err_dl:{e}"

    cover = download_cover(track, dirpath, session)
    try:
        if ext == "mp3":
            tag_mp3(filepath, track, cover)
        else:
            tag_m4a(filepath, track, cover)
    except Exception as e:
        print(f"[warn] tag failed {filepath.name}: {e}", file=sys.stderr)

    return "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token-file", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--rate-limit", type=float, default=0.25)
    args = ap.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    token = load_token(args.token_file)
    client = retry_net(lambda: Client(token).init(), "client_init")
    print(f"[info] logged in, fetching likes...", file=sys.stderr)

    likes = retry_net(lambda: client.users_likes_tracks(), "users_likes_tracks")
    tracks = retry_net(lambda: likes.fetch_tracks(), "fetch_tracks")
    print(f"[info] {len(tracks)} tracks to process", file=sys.stderr)

    session = requests.Session()
    stats: dict[str, int] = {}

    errlog_path = args.output.parent / "download-errors.log"
    errlog = errlog_path.open("a", encoding="utf-8")
    errlog.write(f"\n=== run at {time.strftime('%F %T')} ===\n")

    bar = tqdm(tracks, desc="download", unit="tr", dynamic_ncols=True)
    for track in bar:
        status = download_one(track, args.output, session)
        key = status.split(":", 1)[0]
        stats[key] = stats.get(key, 0) + 1
        bar.set_postfix_str(
            f"ok={stats.get('ok',0)} skip={stats.get('skip_exists',0)} err={stats.get('err_dl',0)+stats.get('err_info',0)+stats.get('no_info',0)}"
        )
        if key.startswith("err") or key == "no_info":
            artist = track.artists[0].name if track.artists else "?"
            title = track.title or "?"
            errlog.write(f"{key}\t{track.id}\t{artist} - {title}\t{status}\n")
            errlog.flush()
        if key == "ok":
            time.sleep(args.rate_limit)

    errlog.close()

    bar.close()
    print(f"\n[done] {stats}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
