import io
import unittest

import listsongs


def track(track_id=1, artist="Artist", title="Title"):
    return {
        "id": track_id,
        "artist": artist,
        "title": title,
        "time": "2026-08-30 11:40:16.063",
        "group": "Specialty Show",
        "streaming": [],
    }


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = iter(payloads)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(next(self.payloads))


class WITRClientTests(unittest.TestCase):
    def test_reads_tracks_and_follows_next_link(self):
        session = FakeSession(
            [
                {
                    "tracks": [track(2, "First Artist", "First Song")],
                    "_links": {
                        "next": "https://logger.witr.rit.edu/api/tracks/list?count=1&offset=1&underground=false"
                    },
                },
                {"tracks": [track(1, "Second Artist", "Second Song")], "_links": {}},
            ]
        )
        client = listsongs.WITRClient(session=session, delay=0)

        result = list(client.iter_tracks(page_size=1))

        self.assertEqual([item.id for item in result], [2, 1])
        self.assertEqual(
            session.calls[0][1]["params"], {"count": 1, "underground": "false"}
        )
        self.assertIsNone(session.calls[1][1]["params"])

    def test_translates_site_filters_to_api_parameters(self):
        session = FakeSession([{"tracks": [], "_links": {}}])
        client = listsongs.WITRClient(session=session, delay=0)

        list(
            client.iter_tracks(
                artist="Cure",
                title="Friday",
                start_ms=10,
                end_ms=20,
                underground=True,
                offset=25,
            )
        )

        self.assertEqual(
            session.calls[0][1]["params"],
            {
                "count": 100,
                "underground": "true",
                "artist": "Cure",
                "song": "Friday",
                "start": 10,
                "end": 20,
                "offset": 25,
            },
        )

    def test_rejects_pagination_to_another_origin(self):
        session = FakeSession(
            [
                {
                    "tracks": [track()],
                    "_links": {"next": "https://example.com/api/tracks/list?offset=1"},
                }
            ]
        )
        client = listsongs.WITRClient(session=session, delay=0)

        with self.assertRaises(listsongs.WITRError):
            list(client.iter_tracks())

    def test_max_pages_stops_before_next_request(self):
        session = FakeSession(
            [
                {
                    "tracks": [track()],
                    "_links": {
                        "next": "https://logger.witr.rit.edu/api/tracks/list?offset=1"
                    },
                }
            ]
        )
        client = listsongs.WITRClient(session=session, delay=0)

        self.assertEqual(len(list(client.iter_tracks(max_pages=1))), 1)
        self.assertEqual(len(session.calls), 1)

    def test_rejects_malformed_links(self):
        session = FakeSession([{"tracks": [track()], "_links": "not an object"}])
        client = listsongs.WITRClient(session=session, delay=0)

        with self.assertRaises(listsongs.WITRError):
            list(client.iter_tracks())

    def test_stops_at_public_api_offset_limit(self):
        boundary = track(10, "Boundary Artist", "Boundary Song")
        session = FakeSession(
            [
                {
                    "tracks": [boundary],
                    "_links": {
                        "next": "https://logger.witr.rit.edu/api/tracks/list?count=1000&offset=10000&underground=false"
                    },
                }
            ]
        )
        client = listsongs.WITRClient(session=session, delay=0)

        result = list(client.iter_tracks(page_size=1000))

        self.assertEqual([item.id for item in result], [10])
        self.assertEqual(len(session.calls), 1)


class OutputTests(unittest.TestCase):
    def test_default_text_format_matches_legacy_order(self):
        output = io.StringIO()
        item = listsongs.Track.from_json(track(1, "An Artist", "A Title"))

        count = listsongs.write_tracks([item], output, "text")

        self.assertEqual(count, 1)
        self.assertEqual(output.getvalue(), "An Artist - A Title\n")

    def test_date_only_end_includes_the_whole_local_day(self):
        expected = listsongs.parse_boundary("2026-08-30T23:59:59.999999", end_of_day=False)
        actual = listsongs.parse_boundary("2026-08-30", end_of_day=True)
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
