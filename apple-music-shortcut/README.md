# WITR Apple Music Shortcut kit

This folder converts the current and legacy WITR lists into small files that an
iPhone or iPad Shortcut can search and add to an Apple Music playlist. The
prepared `Inbox/` contains 100 songs per file so a run can finish without trying
to keep a 12,000-song Shortcut alive.

The Shortcut processes **one batch per run**. It loads the Inbox folder, selects
the first batch by filename, searches the iTunes Store for each artist/title,
adds the first result to the chosen Apple Music playlist, records misses, and
deletes that batch only after its entire loop finishes. Run it again for the
next batch.

## Put the folders in iCloud Drive

1. In iCloud Drive, open `Shortcuts` and create `WITR Import` inside it.
2. Copy this package's `Inbox` folder to
   `iCloud Drive/Shortcuts/WITR Import/Inbox`.
3. Create an empty `Logs` folder beside `Inbox`.
4. In Music, create the playlist that will receive the songs, for example
   `WITR Songs`.
5. Build the Shortcut from
   [`shortcut/WITR Apple Music Import.md`](shortcut/WITR%20Apple%20Music%20Import.md).

On the first run, allow access to iCloud Drive, the iTunes Store, and Music.
The file deletion action may also ask for permission; choose the persistent
allow option if iOS offers it. The Shortcut does not open or switch to the Music
app while its built-in actions are working, but keep Shortcuts in the foreground
until that 100-song run finishes.

## Safety and retry behavior

- Files are named with zero-padded numbers, so alphabetical order is import
  order.
- The `Delete Files` action is deliberately the final file operation. If an
  action stops the Shortcut, the batch remains in Inbox and can be retried.
- A search that returns no result is written to `Logs/unmatched.txt`; it does
  not stop the rest of the batch.
- A malformed line is written to `Logs/invalid-lines.txt`.
- The completed filename is written to `Logs/completed-batches.txt` before the
  input file is deleted.
- iTunes Store search is approximate. Review the resulting playlist and the
  unmatched log; a first-result search can occasionally choose a different
  recording, remaster, or similarly named song.

## Regenerate the batches

From the repository root:

```console
python apple-music-shortcut/prepare_batches.py
```

The generator reads `songs.txt` first and then `legacy/songs.txt`, decodes HTML
entities, normalizes whitespace and Unicode, and deduplicates artist/title pairs
case-insensitively. It replaces only files named `witr-batch-*.txt` in `Inbox`.

Change the batch size if needed:

```console
python apple-music-shortcut/prepare_batches.py --batch-size 50
```

## Why the repository contains a build recipe

Apple requires shared Shortcut files to be exported and validated by Apple.
That export/signing step is available in the Shortcuts app on an Apple device,
not on Windows. The action recipe in this package is therefore the complete,
auditable Shortcut source, but it is not mislabeled as an importable
`.shortcut` file. After building it once on an iPhone, iPad, or Mac, use Share
in Shortcuts to export the validated file or create an iCloud link.
