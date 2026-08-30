# ListSongsWITR

Export the song history displayed at [witr.rit.edu/songs](https://witr.rit.edu/songs).

The current site is a JavaScript application. Its Songs page reads paginated JSON from WITR's public logger API, so this tool uses that same API rather than trying to parse an empty application shell.

## Setup

Python 3.9 or newer is required.

```console
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

## Usage

Write every FM playlist entry to a text file in the original `ARTIST - TITLE` format:

```console
python listsongs.py --output songs.txt
```

Run a small export or select a richer format:

```console
python listsongs.py --max-songs 20
python listsongs.py --max-pages 5 --format csv --output songs.csv
python listsongs.py --format jsonl --output songs.jsonl
```

Use the filters exposed by the website:

```console
python listsongs.py --artist "The Cure" --title "Friday"
python listsongs.py --start 2026-08-01 --end 2026-08-31 --output august.txt
python listsongs.py --underground --max-songs 100
```

If a long export is interrupted after (for example) 10,000 songs, resume without duplicating the completed portion:

```console
python listsongs.py --offset 10000 --append --output songs.txt
```

Dates without a timezone are interpreted in `America/New_York`, WITR's local timezone. A date-only `--end` value includes the whole day. The scraper retries transient failures, validates pagination URLs before following them, and waits 0.1 seconds between pages by default. Use `--delay` to adjust that pause.

WITR's public logger currently returns HTTP 500 at offset 10,000, including when only one additional record is requested. An unfiltered full run therefore exports the 10,000 play records the public service makes accessible and stops before the known-failing request.

Run `python listsongs.py --help` for every option.

## Legacy version

The original 2017 Python 2 scripts, dependency pins, and historical `songs.txt` are preserved in [`legacy/`](legacy/README.md).

## Apple Music import

The [`apple-music-shortcut/`](apple-music-shortcut/README.md) package contains
deduplicated 100-song batches and a ready-made iOS/iPadOS `.shortcut` file. The
Shortcut loads one batch from an iCloud Drive folder, searches by artist and
song, adds matches to an Apple Music playlist, and deletes the completed batch.
