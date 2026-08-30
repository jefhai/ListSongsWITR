#!/usr/bin/env python3
"""Build Apple Music Shortcut input batches from the WITR song lists."""

from __future__ import annotations

import argparse
import html
import re
import unicodedata
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
REPOSITORY_DIR = PACKAGE_DIR.parent
DEFAULT_INPUTS = (REPOSITORY_DIR / "songs.txt", REPOSITORY_DIR / "legacy" / "songs.txt")
DEFAULT_OUTPUT_DIR = PACKAGE_DIR / "Inbox"
WHITESPACE = re.compile(r"\s+")


def normalize_song(raw_line: str) -> tuple[str, tuple[str, str]] | None:
    """Return a display line and case-insensitive deduplication key."""

    line = unicodedata.normalize("NFC", html.unescape(raw_line.strip()))
    if " - " not in line:
        return None

    artist, title = line.split(" - ", 1)
    artist = WHITESPACE.sub(" ", artist).strip()
    title = WHITESPACE.sub(" ", title).strip()
    if not artist or not title:
        return None

    return f"{artist} - {title}", (artist.casefold(), title.casefold())


def load_unique_songs(input_paths: tuple[Path, ...]) -> list[str]:
    """Read sources in order and preserve the first normalized occurrence."""

    songs: list[str] = []
    seen: set[tuple[str, str]] = set()

    for path in input_paths:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            normalized = normalize_song(raw_line)
            if normalized is None:
                continue
            display_line, key = normalized
            if key in seen:
                continue
            seen.add(key)
            songs.append(display_line)

    return songs


def write_batches(songs: list[str], output_dir: Path, batch_size: int) -> list[Path]:
    """Replace generated batch files and return the files written."""

    output_dir.mkdir(parents=True, exist_ok=True)
    for old_batch in output_dir.glob("witr-batch-*.txt"):
        old_batch.unlink()

    written: list[Path] = []
    for index, start in enumerate(range(0, len(songs), batch_size), start=1):
        path = output_dir / f"witr-batch-{index:04d}.txt"
        path.write_text("\n".join(songs[start : start + batch_size]) + "\n", encoding="utf-8")
        written.append(path)

    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="songs per file (default: 100)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="folder that receives witr-batch-NNNN.txt files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1")

    songs = load_unique_songs(DEFAULT_INPUTS)
    batches = write_batches(songs, args.output_dir, args.batch_size)
    final_size = len(songs) % args.batch_size or (args.batch_size if songs else 0)
    print(
        f"Wrote {len(songs):,} unique songs to {len(batches):,} batches "
        f"in {args.output_dir} (last batch: {final_size})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
