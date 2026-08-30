#!/usr/bin/env python3
"""Build the WITR Apple Music importer as an Apple Shortcut plist."""

from __future__ import annotations

import plistlib
import uuid
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = PACKAGE_DIR / "shortcut" / "WITR Apple Music Import.shortcut"
NAMESPACE = uuid.UUID("bc096547-01a7-4cf6-a1f5-57da25721bd6")


def uid(label: str) -> str:
    return str(uuid.uuid5(NAMESPACE, label)).upper()


def output_reference(action_uuid: str, output_name: str) -> dict:
    return {
        "Value": {
            "OutputUUID": action_uuid,
            "Type": "ActionOutput",
            "OutputName": output_name,
        },
        "WFSerializationType": "WFTextTokenAttachment",
    }


def named_variable(name: str) -> dict:
    return {
        "Value": {"VariableName": name, "Type": "Variable"},
        "WFSerializationType": "WFTextTokenAttachment",
    }


def conditional_input(reference: dict) -> dict:
    return {"Type": "Variable", "Variable": reference}


def text_with_attachment(reference_value: dict, suffix: str = "") -> dict:
    return {
        "Value": {
            "string": "￼" + suffix,
            "attachmentsByRange": {"{0, 1}": reference_value},
        },
        "WFSerializationType": "WFTextTokenString",
    }


def action(identifier: str, label: str, **parameters: object) -> dict:
    return {
        "WFWorkflowActionIdentifier": identifier,
        "WFWorkflowActionParameters": {"UUID": uid(label), **parameters},
    }


def build_workflow() -> dict:
    get_inbox_id = uid("get-inbox")
    folder_contents_id = uid("folder-contents")
    filtered_batches_id = uid("filtered-batches")
    batch_file_id = uid("batch-file")
    batch_name_id = uid("batch-name")
    batch_text_id = uid("batch-text")
    split_lines_id = uid("split-lines")
    repeat_id = uid("repeat-start")
    repeat_group = uid("repeat-group")
    search_id = uid("search-itunes")
    search_if_group = uid("search-if-group")
    first_song_id = uid("first-song")
    unmatched_text_id = uid("unmatched-text")
    completed_text_id = uid("completed-text")

    repeat_item = named_variable("Repeat Item")
    search_results = output_reference(search_id, "iTunes Products")

    actions = [
        action(
            "is.workflow.actions.documentpicker.open",
            "get-inbox",
            WFGetFilePath="WITR Import/Inbox",
            WFFileErrorIfNotFound=True,
        ),
        action(
            "is.workflow.actions.file.getfoldercontents",
            "folder-contents",
            WFFolder=output_reference(get_inbox_id, "File"),
            Recursive=False,
        ),
        action(
            "is.workflow.actions.filter.files",
            "filtered-batches",
            WFContentItemInputParameter=output_reference(
                folder_contents_id, "Contents of Folder"
            ),
            WFContentItemLimitEnabled=True,
            WFContentItemLimitNumber=1,
            WFContentItemSortProperty="Name",
            WFContentItemSortOrder="A to Z",
        ),
        action(
            "is.workflow.actions.getitemfromlist",
            "batch-file",
            WFInput=output_reference(filtered_batches_id, "Files"),
            WFItemSpecifier="First Item",
        ),
        action(
            "is.workflow.actions.getitemname",
            "batch-name",
            WFInput=output_reference(batch_file_id, "Item from List"),
        ),
        action(
            "is.workflow.actions.detect.text",
            "batch-text",
            WFInput=output_reference(batch_file_id, "Item from List"),
        ),
        action(
            "is.workflow.actions.text.split",
            "split-lines",
            text=output_reference(batch_text_id, "Text"),
        ),
        action(
            "is.workflow.actions.repeat.each",
            "repeat-start",
            WFInput=output_reference(split_lines_id, "Split Text"),
            GroupingIdentifier=repeat_group,
            WFControlFlowMode=0,
        ),
        action(
            "is.workflow.actions.searchitunes",
            "search-itunes",
            WFSearchTerm=repeat_item,
        ),
        action(
            "is.workflow.actions.conditional",
            "search-if-start",
            WFInput=conditional_input(search_results),
            WFCondition=100,
            GroupingIdentifier=search_if_group,
            WFControlFlowMode=0,
        ),
        action(
            "is.workflow.actions.getitemfromlist",
            "first-song",
            WFInput=search_results,
            WFItemSpecifier="First Item",
        ),
        action(
            "is.workflow.actions.addtoplaylist",
            "add-to-playlist",
            WFInput=output_reference(first_song_id, "Item from List"),
            WFPlaylistName="WITR Songs",
        ),
        action(
            "is.workflow.actions.conditional",
            "search-if-otherwise",
            GroupingIdentifier=search_if_group,
            WFControlFlowMode=1,
        ),
        action(
            "is.workflow.actions.gettext",
            "unmatched-text",
            WFTextActionText=text_with_attachment(
                {"VariableName": "Repeat Item", "Type": "Variable"}, "\n"
            ),
        ),
        action(
            "is.workflow.actions.file.append",
            "append-unmatched",
            WFFilePath="WITR Import/Logs/unmatched.txt",
            WFInput=output_reference(unmatched_text_id, "Text"),
            WFAppendFileWriteMode="Append",
        ),
        action(
            "is.workflow.actions.conditional",
            "search-if-end",
            GroupingIdentifier=search_if_group,
            WFControlFlowMode=2,
        ),
        action("is.workflow.actions.nothing", "clear-repeat-output"),
        action(
            "is.workflow.actions.repeat.each",
            "repeat-end",
            GroupingIdentifier=repeat_group,
            WFControlFlowMode=2,
        ),
        action(
            "is.workflow.actions.gettext",
            "completed-text",
            WFTextActionText=text_with_attachment(
                {
                    "OutputUUID": batch_name_id,
                    "Type": "ActionOutput",
                    "OutputName": "Name",
                },
                "\n",
            ),
        ),
        action(
            "is.workflow.actions.file.append",
            "append-completed",
            WFFilePath="WITR Import/Logs/completed-batches.txt",
            WFInput=output_reference(completed_text_id, "Text"),
            WFAppendFileWriteMode="Append",
        ),
        action(
            "is.workflow.actions.file.delete",
            "delete-batch",
            WFInput=output_reference(batch_file_id, "Item from List"),
            WFDeleteImmediatelyDelete=True,
        ),
        action(
            "is.workflow.actions.notification",
            "finished-notification",
            WFNotificationActionBody=(
                "Finished and deleted the batch. Run again for the next batch."
            ),
            WFNotificationActionSound=True,
        ),
    ]

    return {
        "WFWorkflowName": "WITR Apple Music Import",
        "WFWorkflowActions": actions,
        "WFWorkflowClientRelease": "3.0",
        "WFWorkflowClientVersion": "4045.0.4",
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowHasShortcutInputVariables": False,
        "WFWorkflowIcon": {
            "WFWorkflowIconGlyphNumber": 59790,
            "WFWorkflowIconStartColor": 4271458815,
        },
        "WFWorkflowImportQuestions": [],
        "WFWorkflowInputContentItemClasses": [],
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowTypes": [],
    }


def main() -> int:
    workflow = build_workflow()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("wb") as shortcut_file:
        plistlib.dump(workflow, shortcut_file, fmt=plistlib.FMT_BINARY, sort_keys=False)
    print(f"Wrote {OUTPUT_PATH} with {len(workflow['WFWorkflowActions'])} actions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
