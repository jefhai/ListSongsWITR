# Shortcut: WITR Apple Music Import

Build a new Shortcut with this name. Action labels can vary slightly by iOS
release; search the action picker for the bold name shown below.

Before building, create an Apple Music playlist such as `WITR Songs`, then copy
the package's Inbox to:

`iCloud Drive/Shortcuts/WITR Import/Inbox`

Create this empty folder too:

`iCloud Drive/Shortcuts/WITR Import/Logs`

## Actions

1. **Get Contents of Folder**
   - Folder: `iCloud Drive/Shortcuts/WITR Import/Inbox`
   - Recursive: Off
2. **Filter Files**
   - Input: output of Get Contents of Folder
   - Filter: File Extension is `txt`
   - Sort by: Name
   - Order: A to Z
   - Limit: On, `1` file
3. **Count** the filtered files.
4. **If** Count is `0`:
   - **Show Notification**: `No WITR batch files remain.`
   - **Stop This Shortcut** with Result: `No batches remain`
5. **Get Item from List**: First Item from Filtered Files.
6. **Set Variable** named `Batch File` to that item.
7. **Get Text from Input** using `Batch File`.
8. **Split Text** by New Lines.
9. **Repeat with Each** item from Split Text. Inside the repeat:
   1. **Match Text** in Repeat Item with the regular expression
      `^(.+?) - (.+)$`.
   2. **If** Matched Text has any value:
      1. **Get Group from Matched Text**: Group `1`; set variable `Artist`.
      2. **Get Group from Matched Text**: Group `2`; set variable `Title`.
      3. **Text**: insert the `Title` variable, a space, then the `Artist`
         variable.
      4. **Search iTunes Store** using that Text:
         - Media: Music
         - Entity/Type: Song
         - Region: your Apple Music storefront
         - Results: `5`
      5. **If** Search Results has any value:
         - **Get Item from List**: First Item from Search Results.
         - **Add to Playlist**: add that First Item to your `WITR Songs`
           playlist.
      7. **Otherwise**:
         - **Text**: Repeat Item
         - **Append to Text File**:
           `iCloud Drive/Shortcuts/WITR Import/Logs/unmatched.txt`
      8. End the search-result If.
   3. **Otherwise**:
      - **Text**: Repeat Item
      - **Append to Text File**:
        `iCloud Drive/Shortcuts/WITR Import/Logs/invalid-lines.txt`
   4. End the matched-text If.
   5. **Nothing**. This prevents every loop result from accumulating in memory.
10. End Repeat.
11. **Get Name** of `Batch File`.
12. **Append to Text File** that name followed by a newline at:
    `iCloud Drive/Shortcuts/WITR Import/Logs/completed-batches.txt`
13. **Delete Files**: delete `Batch File`.
14. **Show Notification**: `Finished and deleted [Name]. Run again for the next batch.`

## Important editor details

- In each **If**, use `has any value`; do not compare the match or search
  result as text.
- The search input is `Title Artist`, not the original `ARTIST - TITLE` line.
- Set the iTunes Store region to the storefront used by the Apple Music account.
- Select the target playlist directly in **Add to Playlist**. Avoid creating a
  new playlist inside the loop.
- Keep **Delete Files** after the Repeat and completed-log actions. Never place
  it inside the loop.
- If **Append to Text File** is named **Append to File** on the device, use that
  action and select the same path.

## First test

For the first test, move all batches except `witr-batch-0001.txt` out of Inbox,
run the Shortcut in the editor, and confirm that:

1. Songs appear in the selected playlist.
2. Any miss is written to `Logs/unmatched.txt`.
3. `Logs/completed-batches.txt` contains `witr-batch-0001.txt`.
4. The batch file is gone from Inbox only after the loop completes.

Then copy the remaining batches back into Inbox and run the Shortcut once per
batch.
