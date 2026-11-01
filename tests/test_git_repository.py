"""The git commands against real repositories.

These tests run the real ``git`` executable in a throwaway repository, so
they cover the command line as Git actually answers it rather than a
recorded sample.
"""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "package" / "editor" / "wokrlie"))

from git_integration.git import (  # noqa: E402
    GitCommand,
    GitRunner,
    checkout,
    create_branch,
    list_branches,
    parse_status,
    read_repository_state,
    read_status,
    validate_branch_name,
)


GIT = shutil.which("git")


@unittest.skipIf(GIT is None, "git is required for this test")
class GitRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.runner = GitRunner(str(self.repo))
        self.git("init")
        self.git("config", "user.email", "panel@example.com")
        self.git("config", "user.name", "Panel Test")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")

    def git(self, *args, cwd=None):
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd or self.repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )

    def commit(self, message="commit"):
        (self.repo / "tracked.txt").write_text(message, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-m", message)

    def snapshot(self):
        result = read_status(self.runner)
        self.assertTrue(result.ok, result.stderr)
        return parse_status(result.stdout)

    # -- status ------------------------------------------------------- #
    def test_unborn_repository_reports_the_branch_name(self):
        snapshot = self.snapshot()
        self.assertEqual(snapshot.branch, "main")
        self.assertFalse(snapshot.detached)
        self.assertEqual(snapshot.unstaged, {})

    def test_the_state_pass_carries_the_branch_list(self):
        """The branch section draws from the same background pass."""
        self.commit()
        self.git("branch", "feature/nested")
        state = read_repository_state(self.runner)
        self.assertTrue(state.inside)
        self.assertIsNotNone(state.snapshot)
        names = [branch.name for branch in state.branches]
        self.assertIn("main", names)
        self.assertIn("feature/nested", names)

    def test_a_folder_outside_a_repository_is_reported(self):
        outside = self.root / "not-a-repo"
        outside.mkdir()
        state = read_repository_state(GitRunner(str(outside)))
        self.assertFalse(state.inside)
        self.assertIsNone(state.snapshot)
        self.assertEqual(state.branches, [])
        self.assertIsNotNone(state.error)

    def test_modified_untracked_and_staged_files(self):
        self.commit()
        (self.repo / "tracked.txt").write_text("changed", encoding="utf-8")
        (self.repo / "fresh.txt").write_text("new", encoding="utf-8")

        snapshot = self.snapshot()
        self.assertEqual(snapshot.unstaged, {"tracked.txt": "M"})
        self.assertEqual(snapshot.untracked, ["fresh.txt"])

        self.git("add", "tracked.txt")
        snapshot = self.snapshot()
        self.assertEqual(snapshot.staged, {"tracked.txt": "M"})

    def test_rename_keeps_the_new_path(self):
        self.commit()
        self.git("mv", "tracked.txt", "renamed.txt")
        snapshot = self.snapshot()
        self.assertIn("renamed.txt", snapshot.staged)
        self.assertNotIn("tracked.txt", snapshot.staged)

    def test_non_ascii_path_is_reported_verbatim(self):
        (self.repo / "名字 file.txt").write_text("u", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-m", "unicode")
        (self.repo / "名字 file.txt").write_text("changed", encoding="utf-8")

        snapshot = self.snapshot()
        self.assertEqual(list(snapshot.unstaged), ["名字 file.txt"])

    def test_detached_head_is_reported(self):
        self.commit()
        self.git("checkout", "HEAD~0", "--detach")
        snapshot = self.snapshot()
        self.assertTrue(snapshot.detached)
        self.assertTrue(snapshot.oid)
        self.assertEqual(len(snapshot.oid), 40)

    # -- branches ----------------------------------------------------- #
    def test_local_branches_are_listed_with_the_current_one_marked(self):
        self.commit()
        self.git("branch", "feature/nested")
        self.git("branch", "other")

        branches = list_branches(self.runner)
        names = [branch.name for branch in branches]
        self.assertIn("main", names)
        self.assertIn("feature/nested", names)
        self.assertIn("other", names)
        current = [branch for branch in branches if branch.current]
        self.assertEqual([branch.name for branch in current], ["main"])

    def test_remote_branches_are_listed_without_the_symbolic_head(self):
        remote = self.root / "remote.git"
        self.git("init", "--bare", "-b", "main", str(remote), cwd=self.root)
        self.commit()
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "-u", "origin", "main")
        self.git("fetch", "origin")

        branches = list_branches(self.runner)
        remote_names = [branch.name for branch in branches if branch.remote]
        self.assertIn("origin/main", remote_names)
        self.assertNotIn("origin", remote_names)

    def test_upstream_is_reported_for_the_current_branch(self):
        remote = self.root / "remote.git"
        self.git("init", "--bare", "-b", "main", str(remote), cwd=self.root)
        self.commit()
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "-u", "origin", "main")

        snapshot = self.snapshot()
        self.assertEqual(snapshot.upstream, "origin/main")
        self.assertEqual(snapshot.ahead, 0)
        self.assertEqual(snapshot.behind, 0)

    # -- names -------------------------------------------------------- #
    def test_valid_branch_names_are_accepted(self):
        for name in ("main", "feature/nested", "功能/测试", "release-1.2"):
            with self.subTest(name=name):
                self.assertEqual(validate_branch_name(self.runner, name), name)

    def test_dangerous_branch_names_are_rejected(self):
        for name in ("", "   ", "-foo", "--foo", "bad name", "HEAD", "@{-1}"):
            with self.subTest(name=name):
                self.assertEqual(validate_branch_name(self.runner, name), "")

    # -- actions ------------------------------------------------------ #
    def test_create_branch_starts_from_the_current_head(self):
        self.commit()
        result = create_branch(self.runner, "feature/from-head")
        self.assertTrue(result.ok, result.stderr)
        self.assertEqual(self.snapshot().branch, "feature/from-head")

    def test_checkout_returns_to_the_previous_branch(self):
        self.commit()
        self.git("branch", "side")
        result = checkout(self.runner, "side")
        self.assertTrue(result.ok, result.stderr)
        self.assertEqual(self.snapshot().branch, "side")
        result = checkout(self.runner, "main")
        self.assertTrue(result.ok, result.stderr)
        self.assertEqual(self.snapshot().branch, "main")

    def test_checkout_reports_the_files_that_block_it(self):
        self.commit()
        self.git("checkout", "-b", "topic")
        (self.repo / "tracked.txt").write_text("topic", encoding="utf-8")
        self.git("commit", "-am", "topic change")
        self.git("checkout", "main")
        (self.repo / "tracked.txt").write_text("main", encoding="utf-8")

        result = checkout(self.runner, "topic")
        self.assertFalse(result.ok)
        self.assertIn("would be overwritten", result.summary)

    def test_a_failure_carries_the_command_line_and_the_exit_code(self):
        """The Console entry quotes both, so a failure can be run by hand."""
        result = checkout(self.runner, "no-such-branch")
        self.assertFalse(result.ok)
        self.assertEqual(result.command, "git checkout no-such-branch")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.strip())

    def test_unstage_works_without_a_commit(self):
        """``git reset HEAD -- <path>`` is enough in an empty repository."""
        (self.repo / "fresh.txt").write_text("new", encoding="utf-8")
        self.git("add", "-A")
        self.assertEqual(self.snapshot().staged, {"fresh.txt": "A"})

        result = self.runner.run("reset", "HEAD", "--", "fresh.txt")
        self.assertTrue(result.ok, result.stderr)
        snapshot = self.snapshot()
        self.assertEqual(snapshot.staged, {})
        self.assertEqual(snapshot.untracked, ["fresh.txt"])

    def test_unstage_keeps_the_file_tracked_when_a_commit_exists(self):
        self.commit()
        (self.repo / "tracked.txt").write_text("changed", encoding="utf-8")
        self.git("add", "-A")

        result = self.runner.run("reset", "HEAD", "--", "tracked.txt")
        self.assertTrue(result.ok, result.stderr)
        snapshot = self.snapshot()
        self.assertEqual(snapshot.staged, {})
        self.assertEqual(snapshot.unstaged, {"tracked.txt": "M"})

    # -- async -------------------------------------------------------- #
    def wait_for(self, command):
        """Poll a worker command until it reports a result."""
        for _ in range(500):
            result = command.poll()
            if result is not None:
                return result
            time.sleep(0.01)
        self.fail("the worker thread never finished")

    def test_command_returns_none_until_it_finishes(self):
        command = GitCommand.command(self.runner, ("status", "--porcelain=v2", "-z", "--branch"))
        self.assertIsNone(command.poll())
        command.start()
        result = self.wait_for(command)
        self.assertTrue(result.ok, result.stderr)

    def test_command_keeps_the_utf8_paths(self):
        (self.repo / "名字 file.txt").write_text("u", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-m", "unicode")
        (self.repo / "名字 file.txt").write_text("changed", encoding="utf-8")

        command = GitCommand.command(self.runner, ("status", "--porcelain=v2", "-z", "--branch"))
        command.start()
        result = self.wait_for(command)
        self.assertIn("名字 file.txt", result.stdout)


if __name__ == "__main__":
    unittest.main()
