import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "apple-music-shortcut" / "prepare_batches.py"
SPEC = importlib.util.spec_from_file_location("prepare_batches", MODULE_PATH)
prepare_batches = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(prepare_batches)


class NormalizeSongTests(unittest.TestCase):
    def test_normalizes_entities_whitespace_and_unicode(self):
        display, key = prepare_batches.normalize_song("  AC/DC  -  Rock &amp; Roll  ")

        self.assertEqual(display, "AC/DC - Rock & Roll")
        self.assertEqual(key, ("ac/dc", "rock & roll"))

    def test_preserves_hyphens_in_title(self):
        display, _ = prepare_batches.normalize_song("Artist - Part One - Part Two")

        self.assertEqual(display, "Artist - Part One - Part Two")

    def test_rejects_malformed_lines(self):
        self.assertIsNone(prepare_batches.normalize_song("No separator"))
        self.assertIsNone(prepare_batches.normalize_song(" - No artist"))
        self.assertIsNone(prepare_batches.normalize_song("No title - "))


class BatchTests(unittest.TestCase):
    def test_load_unique_songs_preserves_first_occurrence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "first.txt"
            second = Path(temp_dir) / "second.txt"
            first.write_text("Artist - Song\n", encoding="utf-8")
            second.write_text("ARTIST - SONG\nOther - Track\n", encoding="utf-8")

            songs = prepare_batches.load_unique_songs((first, second))

        self.assertEqual(songs, ["Artist - Song", "Other - Track"])

    def test_write_batches_replaces_only_generated_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            stale = output_dir / "witr-batch-9999.txt"
            keep = output_dir / "notes.txt"
            stale.write_text("stale\n", encoding="utf-8")
            keep.write_text("keep\n", encoding="utf-8")

            written = prepare_batches.write_batches(
                ["A - One", "B - Two", "C - Three"], output_dir, 2
            )

            self.assertEqual([path.name for path in written], [
                "witr-batch-0001.txt",
                "witr-batch-0002.txt",
            ])
            self.assertFalse(stale.exists())
            self.assertTrue(keep.exists())
            self.assertEqual(written[0].read_text(encoding="utf-8"), "A - One\nB - Two\n")
            self.assertEqual(written[1].read_text(encoding="utf-8"), "C - Three\n")


if __name__ == "__main__":
    unittest.main()
