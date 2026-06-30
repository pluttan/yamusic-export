![Header](header.png)

<div align="center">

# yamusic-export

**Yandex Music library exporter with ListenBrainz import**

[![License](https://img.shields.io/badge/license-MIT-2C2C2C?style=for-the-badge&labelColor=1E1E1E)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-2C2C2C?style=for-the-badge&logo=python&labelColor=1E1E1E)]()
[![Yandex Music](https://img.shields.io/badge/yandex-music-2C2C2C?style=for-the-badge&labelColor=1E1E1E)]()

</div>

Dumps a Yandex Music account's liked tracks and playlists to JSON, downloads the actual audio files with embedded metadata (ID3/MP4 tags + cover art), and imports listening history into ListenBrainz. Full pipeline from export to local library to scrobble history.

## ■ Features

- ❖ **Library export** — liked tracks and playlists to structured JSON
- ❖ **Audio download** — full tracks in mp3/m4a with artist/album directory layout
- ❖ **Metadata tagging** — ID3 (MP3) and MP4 tags: artist, title, album, year, cover art
- ❖ **ListenBrainz import** — submits listening history as historical scrobbles (batches of 1000)
- ❖ **IPv4 DNS fix** — patches socket to prefer IPv4 on hosts where IPv6 is not routed
- ❖ **Progress bars** — tqdm-powered download progress

## ■ Stack

| Component | Technology |
|-----------|------------|
| API Client | yandex-music (Python SDK) |
| Tagging | mutagen (ID3, MP4) |
| Import | ListenBrainz REST API |
| Downloads | requests + tqdm |

## ■ Usage

```bash
make install        # create venv, install dependencies
make export         # export liked tracks + playlists to data/*.json
make download       # download audio files to data/music/library/
make all            # install + export + download

# ListenBrainz import
venv/bin/python import_lbz.py --token-file <path>
```

## ■ License

MIT © [pluttan](https://github.com/pluttan)
