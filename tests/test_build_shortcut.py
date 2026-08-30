import importlib.util
import plistlib
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "apple-music-shortcut" / "build_shortcut.py"
SPEC = importlib.util.spec_from_file_location("build_shortcut", MODULE_PATH)
build_shortcut = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(build_shortcut)


class ShortcutBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = build_shortcut.build_workflow()
        cls.actions = cls.workflow["WFWorkflowActions"]

    def test_checked_in_shortcut_is_binary_plist(self):
        data = build_shortcut.OUTPUT_PATH.read_bytes()

        self.assertTrue(data.startswith(b"bplist00"))
        self.assertEqual(plistlib.loads(data), self.workflow)

    def test_contains_expected_music_and_file_actions(self):
        identifiers = [
            action["WFWorkflowActionIdentifier"] for action in self.actions
        ]

        self.assertEqual(len(identifiers), 22)
        self.assertIn("is.workflow.actions.searchitunes", identifiers)
        self.assertIn("is.workflow.actions.addtoplaylist", identifiers)
        self.assertIn("is.workflow.actions.file.delete", identifiers)

        add_action = next(
            action
            for action in self.actions
            if action["WFWorkflowActionIdentifier"]
            == "is.workflow.actions.addtoplaylist"
        )
        self.assertEqual(
            add_action["WFWorkflowActionParameters"]["WFPlaylistName"],
            "WITR Songs",
        )

    def test_delete_occurs_after_repeat_finishes(self):
        identifiers = [
            action["WFWorkflowActionIdentifier"] for action in self.actions
        ]
        repeat_indexes = [
            index
            for index, identifier in enumerate(identifiers)
            if identifier == "is.workflow.actions.repeat.each"
        ]
        delete_index = identifiers.index("is.workflow.actions.file.delete")

        self.assertEqual(len(repeat_indexes), 2)
        self.assertLess(repeat_indexes[1], delete_index)
        self.assertEqual(
            self.actions[repeat_indexes[0]]["WFWorkflowActionParameters"][
                "GroupingIdentifier"
            ],
            self.actions[repeat_indexes[1]]["WFWorkflowActionParameters"][
                "GroupingIdentifier"
            ],
        )

    def test_control_flow_metadata_is_canonical(self):
        for action in self.actions:
            self.assertNotIn("UUID", action)
            self.assertNotIn("GroupingIdentifier", action)
            self.assertIn("UUID", action["WFWorkflowActionParameters"])

        conditional_actions = [
            action
            for action in self.actions
            if action["WFWorkflowActionIdentifier"]
            == "is.workflow.actions.conditional"
        ]
        self.assertEqual(
            [
                action["WFWorkflowActionParameters"]["WFControlFlowMode"]
                for action in conditional_actions
            ],
            [0, 1, 2],
        )
        self.assertEqual(
            conditional_actions[0]["WFWorkflowActionParameters"]["WFCondition"],
            100,
        )


if __name__ == "__main__":
    unittest.main()
