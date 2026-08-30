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
5. Open
   [`shortcut/WITR Apple Music Import.shortcut`](shortcut/WITR%20Apple%20Music%20Import.shortcut)
   on the iPhone or iPad and add it to Shortcuts.

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

## Rebuild the Shortcut file

The checked-in `.shortcut` is generated directly as an Apple binary property
list. To reproduce it after changing the workflow:

```console
python apple-music-shortcut/build_shortcut.py
```

The destination playlist is `WITR Songs`. Change `WFPlaylistName` in the
builder and regenerate the file to use a different playlist.
