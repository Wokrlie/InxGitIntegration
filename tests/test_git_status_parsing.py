"""The porcelain v2 status parser.

The samples below are the raw bytes of real ``git status --porcelain=v2 -z
--branch`` runs, captured on git 2.55 and only edited for readability.
"""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "package" / "editor" / "wokrlie"))

from git_integration.git import parse_status  # noqa: E402


class StatusParsingTests(unittest.TestCase):
    def test_unborn_branch_reports_its_name(self):
        payload = "# branch.oid (initial)\0# branch.head main\0"
        snapshot = parse_status(payload)
        self.assertEqual(snapshot.branch, "main")
        self.assertFalse(snapshot.detached)
        self.assertEqual(snapshot.oid, "")
        self.assertEqual(snapshot.staged, {})
        self.assertEqual(snapshot.unstaged, {})
        self.assertEqual(snapshot.untracked, [])

    def test_modified_and_untracked_entries(self):
        payload = (
            "# branch.oid b4ae9d58ae408c1512b316fee7c5c24e05031d24\0"
            "# branch.head main\0"
            "1 .M N... 100644 100644 100644 "
            "c1b0730e0133447badcfd47fd144e254807b06e1 "
            "c1b0730e0133447badcfd47fd144e254807b06e1 a.txt\0"
            "? new.txt\0"
        )
        snapshot = parse_status(payload)
        self.assertEqual(snapshot.branch, "main")
        self.assertEqual(snapshot.unstaged, {"a.txt": "M"})
        self.assertEqual(snapshot.staged, {})
        self.assertEqual(snapshot.untracked, ["new.txt"])

    def test_dual_state_lands_in_both_lists(self):
        payload = (
            "# branch.oid b4ae9d58ae408c1512b316fee7c5c24e05031d24\0"
            "# branch.head main\0"
            "1 AM N... 100644 100644 100644 "
            "c1b0730e0133447badcfd47fd144e254807b06e1 "
            "c1b0730e0133447badcfd47fd144e254807b06e1 both.txt\0"
        )
        snapshot = parse_status(payload)
        self.assertEqual(snapshot.staged, {"both.txt": "A"})
        self.assertEqual(snapshot.unstaged, {"both.txt": "M"})

    def test_rename_keeps_the_new_path_and_skips_the_original(self):
        payload = (
            "# branch.oid b4ae9d58ae408c1512b316fee7c5c24e05031d24\0"
            "# branch.head main\0"
            "2 RM N... 100644 100644 100644 "
            "c1b0730e0133447badcfd47fd144e254807b06e1 "
            "c1b0730e0133447badcfd47fd144e254807b06e1 R100 b.txt\0"
            "a.txt\0"
            "? new.txt\0"
        )
        snapshot = parse_status(payload)
        self.assertEqual(snapshot.staged, {"b.txt": "R"})
        self.assertEqual(snapshot.unstaged, {"b.txt": "M"})
        self.assertNotIn("a.txt", snapshot.staged)
        self.assertNotIn("a.txt", snapshot.unstaged)
        self.assertEqual(snapshot.untracked, ["new.txt"])

    def test_non_ascii_path_stays_literal(self):
        """The v1 format escaped this into octal; v2 with -z does not."""
        payload = (
            "# branch.oid 0a8c200fcc1991e1fed788f630b87005cd1c1684\0"
            "# branch.head main\0"
            "1 .M N... 100644 100644 100644 "
            "f3c6c3c68af484bd95bc7b7a38276c6c014d6aa3 "
            "f3c6c3c68af484bd95bc7b7a38276c6c014d6aa3 名字 file.txt\0"
        )
        snapshot = parse_status(payload)
        self.assertEqual(list(snapshot.unstaged), ["名字 file.txt"])
        self.assertNotIn("\\345", list(snapshot.unstaged)[0])

    def test_detached_head_is_reported(self):
        payload = (
            "# branch.oid 2876a2c1f6e9bb32f3e7538858d5ecf92d78998b\0"
            "# branch.head (detached)\0"
        )
        snapshot = parse_status(payload)
        self.assertTrue(snapshot.detached)
        self.assertEqual(snapshot.branch, "")
        self.assertEqual(snapshot.oid, "2876a2c1f6e9bb32f3e7538858d5ecf92d78998b")

    def test_the_commit_hash_is_kept_for_a_detached_head(self):
        """The header names the commit, so the tooltip can show a short sha."""
        payload = (
            "# branch.oid 2876a2c1f6e9bb32f3e7538858d5ecf92d78998b\0"
            "# branch.head (detached)\0"
        )
        snapshot = parse_status(payload)
        self.assertEqual(snapshot.oid[:7], "2876a2c")

    def test_upstream_and_ahead_behind(self):
        payload = (
            "# branch.oid 6e3dae717eaed0fd1056eef56a76715406464b8b\0"
            "# branch.head main\0"
            "# branch.upstream origin/main\0"
            "# branch.ab +3 -2\0"
        )
        snapshot = parse_status(payload)
        self.assertEqual(snapshot.upstream, "origin/main")
        self.assertEqual(snapshot.ahead, 3)
        self.assertEqual(snapshot.behind, 2)

    def test_conflict_entry_is_reported_in_both_lists(self):
        payload = (
            "# branch.oid b4ae9d58ae408c1512b316fee7c5c24e05031d24\0"
            "# branch.head main\0"
            "u UU N... 100644 100644 100644 100644 "
            "c1b0730e0133447badcfd47fd144e254807b06e1 "
            "c1b0730e0133447badcfd47fd144e254807b06e1 "
            "c1b0730e0133447badcfd47fd144e254807b06e1 conflict.txt\0"
        )
        snapshot = parse_status(payload)
        self.assertEqual(snapshot.staged, {"conflict.txt": "U"})
        self.assertEqual(snapshot.unstaged, {"conflict.txt": "U"})

    def test_ignored_entries_are_skipped(self):
        payload = (
            "# branch.oid b4ae9d58ae408c1512b316fee7c5c24e05031d24\0"
            "# branch.head main\0"
            "! ignored.txt\0"
        )
        snapshot = parse_status(payload)
        self.assertEqual(snapshot.staged, {})
        self.assertEqual(snapshot.unstaged, {})
        self.assertEqual(snapshot.untracked, [])

    def test_empty_payload_is_an_empty_snapshot(self):
        snapshot = parse_status("")
        self.assertEqual(snapshot.branch, "")
        self.assertFalse(snapshot.detached)
        self.assertEqual(snapshot.change_count, 0)


if __name__ == "__main__":
    unittest.main()
