#!/usr/bin/env python3
"""Export the song history shown at https://witr.rit.edu/songs."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, time as datetime_time
from pathlib import Path
from typing import Any, Iterable, Iterator, TextIO
from urllib.parse import parse_qs, urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_BASE_URL = "https://logger.witr.rit.edu"
DEFAULT_PAGE_SIZE = 100
API_MAX_OFFSET = 10_000
WITR_TIME_ZONE = ZoneInfo("America/New_York")


class WITRError(RuntimeError):
    """Raised when WITR returns malformed or unsafe pagination data."""


@dataclass(frozen=True)
class Track:
    id: int
    artist: str
    title: str
    time: str
    group: str
    streaming: list[dict[str, Any]]

    @classmethod
    def from_json(cls, value: object) -> "Track":
        if not isinstance(value, dict):
            raise WITRError("A track in the response was not a JSON object")

        try:
            track_id = int(value["id"])
            artist = str(value["artist"])
            title = str(value["title"])
        except (KeyError, TypeError, ValueError) as exc:
            raise WITRError("A track was missing a valid id, artist, or title") from exc

        streaming = value.get("streaming", [])
        if not isinstance(streaming, list):
            raise WITRError(f"Track {track_id} had an invalid streaming field")

        return cls(
            id=track_id,
            artist=artist,
            title=title,
            time=str(value.get("time", "")),
            group=str(value.get("group", "")),
            streaming=streaming,
        )


def build_session() -> requests.Session:
    """Create a session with retries suitable for a long paginated export."""
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "ListSongsWITR/2.0 (+https://github.com/jefhai/ListSongsWITR)"}
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class WITRClient:
    """Small client for the public API used by WITR's Songs page."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 30.0,
        delay: float = 0.1,
        session: Any | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.delay = delay
        self.session = session or build_session()
        self._owns_session = session is None

        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("base_url must be an absolute HTTP(S) URL")

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def __enter__(self) -> "WITRClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def iter_tracks(
        self,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        underground: bool = False,
        artist: str | None = None,
        title: str | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        offset: int = 0,
        max_pages: int | None = None,
    ) -> Iterator[Track]:
        params: dict[str, str | int] = {
            "count": page_size,
            "underground": str(underground).lower(),
        }
        if artist:
            params["artist"] = artist
        if title:
            # The website labels this field Title, but the API calls it "song".
            params["song"] = title
        if start_ms is not None:
            params["start"] = start_ms
        if end_ms is not None:
            params["end"] = end_ms
        if offset:
            params["offset"] = offset

        next_url: str | None = f"{self.base_url}/api/tracks/list"
        request_params: dict[str, str | int] | None = params
        seen_requests: set[str] = set()
        yielded_ids: set[int] = set()
        page_number = 0

        while next_url:
            request_key = f"{next_url}|{sorted((request_params or {}).items())}"
            if request_key in seen_requests:
                raise WITRError(f"WITR returned a pagination loop at {next_url}")
            seen_requests.add(request_key)

            response = self.session.get(
                next_url,
                params=dict(request_params) if request_params is not None else None,
                timeout=self.timeout,
            )
            response.raise_for_status()
            try:
                payload = response.json()
            except (requests.JSONDecodeError, ValueError) as exc:
                raise WITRError("WITR returned a non-JSON response") from exc

            if not isinstance(payload, dict) or not isinstance(payload.get("tracks"), list):
                raise WITRError("WITR returned JSON without a tracks list")

            page_number += 1
            raw_tracks = payload["tracks"]
            parsed_tracks = [Track.from_json(raw_track) for raw_track in raw_tracks]
            for track in parsed_tracks:
                if track.id not in yielded_ids:
                    yielded_ids.add(track.id)
                    yield track

            if max_pages is not None and page_number >= max_pages:
                break

            links = payload.get("_links", {})
            if not isinstance(links, dict):
                raise WITRError("WITR returned an invalid _links object")
            raw_next = links.get("next")
            if not raw_next or not raw_tracks:
                break
            validated_next = self._validated_next_url(str(raw_next))
            next_offset = int(
                parse_qs(urlparse(validated_next).query).get("offset", ["0"])[0]
            )
            if next_offset >= API_MAX_OFFSET:
                # The public service returns HTTP 500 for every request at offset
                # 10,000, even with count=1. Treat its accessible-record ceiling as
                # the end instead of sending a request that is known to fail.
                break
            next_url = validated_next
            request_params = None

            if self.delay:
                time.sleep(self.delay)

    def _validated_next_url(self, value: str) -> str:
        """Only follow pagination links back to the configured tracks API."""
        candidate = urljoin(f"{self.base_url}/", value)
        base = urlparse(self.base_url)
        parsed = urlparse(candidate)
        if (
            parsed.scheme != base.scheme
            or parsed.hostname != base.hostname
            or parsed.port != base.port
            or parsed.path != "/api/tracks/list"
        ):
            raise WITRError(f"Refusing unexpected pagination URL: {candidate}")
        return candidate


def parse_boundary(value: str, *, end_of_day: bool) -> int:
    """Parse an ISO date/time as WITR local time and return epoch milliseconds."""
    date_only = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"{value!r} is not an ISO date or date/time"
        ) from exc

    if date_only and end_of_day:
        parsed = datetime.combine(parsed.date(), datetime_time.max)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=WITR_TIME_ZONE)
    return int(parsed.timestamp() * 1000)


def write_tracks(
    tracks: Iterable[Track],
    output: TextIO,
    output_format: str,
    *,
    write_header: bool = True,
) -> int:
    count = 0
    if output_format == "csv":
        writer = csv.DictWriter(
            output, fieldnames=("id", "artist", "title", "time", "group", "streaming")
        )
        if write_header:
            writer.writeheader()
        for track in tracks:
            row = asdict(track)
            row["streaming"] = json.dumps(row["streaming"], ensure_ascii=False)
            writer.writerow(row)
            count += 1
        return count

    for track in tracks:
        if output_format == "jsonl":
            output.write(json.dumps(asdict(track), ensure_ascii=False) + "\n")
        else:
            output.write(f"{track.artist} - {track.title}\n")
        count += 1
    return count


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the song history displayed at https://witr.rit.edu/songs."
    )
    parser.add_argument("-o", "--output", default="-", help="Output path (default: stdout)")
    parser.add_argument(
        "--format", choices=("text", "csv", "jsonl"), default="text", help="Output format"
    )
    parser.add_argument("--artist", help="Only return matches for this artist search")
    parser.add_argument("--title", help="Only return matches for this title search")
    parser.add_argument("--start", help="Earliest ISO date/time, interpreted in WITR local time")
    parser.add_argument("--end", help="Latest ISO date/time; a date includes its entire day")
    parser.add_argument(
        "--underground", action="store_true", help="Export the Underground stream instead of FM"
    )
    parser.add_argument("--page-size", type=positive_int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--max-pages", type=positive_int, help="Stop after this many API pages")
    parser.add_argument("--max-songs", type=positive_int, help="Stop after this many songs")
    parser.add_argument(
        "--offset", type=non_negative_int, default=0, help="Resume at this API offset"
    )
    parser.add_argument(
        "--append", action="store_true", help="Append to --output instead of replacing it"
    )
    parser.add_argument(
        "--delay",
        type=non_negative_float,
        default=0.1,
        help="Seconds to wait between pages (default: 0.1)",
    )
    parser.add_argument("--timeout", type=positive_int, default=30, help="HTTP timeout in seconds")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        start_ms = parse_boundary(args.start, end_of_day=False) if args.start else None
        end_ms = parse_boundary(args.end, end_of_day=True) if args.end else None
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    if start_ms is not None and end_ms is not None and start_ms > end_ms:
        parser.error("--start must not be later than --end")
    if args.append and args.output == "-":
        parser.error("--append requires a file specified with --output")

    output: TextIO
    should_close = args.output != "-"
    if should_close:
        output_path = Path(args.output)
        output_had_content = (
            args.append and output_path.exists() and output_path.stat().st_size > 0
        )
        output = output_path.open("a" if args.append else "w", encoding="utf-8", newline="")
    else:
        output_path = None
        output_had_content = False
        output = sys.stdout
        if hasattr(output, "reconfigure"):
            output.reconfigure(encoding="utf-8", newline="")

    try:
        with WITRClient(
            args.base_url,
            timeout=args.timeout,
            delay=args.delay,
        ) as client:
            tracks: Iterable[Track] = client.iter_tracks(
                page_size=args.page_size,
                underground=args.underground,
                artist=args.artist,
                title=args.title,
                start_ms=start_ms,
                end_ms=end_ms,
                offset=args.offset,
                max_pages=args.max_pages,
            )
            if args.max_songs is not None:
                tracks = itertools.islice(tracks, args.max_songs)
            count = write_tracks(
                tracks, output, args.format, write_header=not output_had_content
            )
    except (requests.RequestException, WITRError) as exc:
        parser.exit(1, f"error: {exc}\n")
    finally:
        if should_close:
            output.close()

    if output_path is not None:
        print(f"Wrote {count} songs to {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
