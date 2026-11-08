"""The shape of the panel's background actions.

Every git command runs on a worker thread, and the panel hands that
thread a job: a callable that returns the command result. The job is
built on the render thread, but it must not run a git command there —
a subprocess spawn on the render thread is a visible hitch in the
Editor.

Two mistakes are easy to make and invisible in a review:

* passing the argument list of a git command where a job belongs, or
  the other way round — the first version of the unstage action did
  exactly that and raised ``TypeError: 'function' object is not
  subscriptable`` on the first click;
* running a git command on the render thread, which stalls the frame.

Both are checked here instead of by a reviewer.
"""

from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "package" / "editor" / "wokrlie" / "git_integration"
PANEL = MODULE / "panel.py"
GIT = MODULE / "git.py"


def calls_named(tree: ast.AST, name: str):
    """Every call to a function or method called *name*."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == name:
            yield node
        elif isinstance(func, ast.Name) and func.id == name:
            yield node


class ActionContractTests(unittest.TestCase):
    def test_every_action_starts_with_a_job(self):
        tree = ast.parse(PANEL.read_text(encoding="utf-8"))
        calls = list(calls_named(tree, "_start_action"))
        self.assertGreater(len(calls), 0, "no _start_action call was found")
        for call in calls:
            with self.subTest(line=call.lineno):
                self.assertTrue(
                    call.args, "_start_action needs the job to run"
                )
                self.assertIsInstance(
                    call.args[0],
                    ast.Lambda,
                    "the first argument of _start_action has to be a job, "
                    "not a list of git arguments",
                )

    def test_the_panel_never_runs_a_git_command_itself(self):
        """A git command on the render thread stalls the frame."""
        tree = ast.parse(PANEL.read_text(encoding="utf-8"))
        for call in calls_named(tree, "run"):
            with self.subTest(line=call.lineno):
                self.fail(
                    "the panel must not call .run() itself: every git "
                    "command belongs in git.py and runs on a worker thread"
                )

    def test_the_panel_does_not_import_subprocess(self):
        source = PANEL.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Import):
                continue
            for alias in node.names:
                with self.subTest(module=alias.name):
                    self.assertNotEqual(alias.name, "subprocess")
            with self.subTest(module=node.names[0].name):
                self.assertNotEqual(node.names[0].name, "subprocess")

    def test_the_command_factory_takes_a_tuple(self):
        """The annotation is the contract the factory relies on."""
        tree = ast.parse(GIT.read_text(encoding="utf-8"))
        found = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name != "command":
                continue
            found = True
            parameters = {arg.arg: arg for arg in node.args.args}
            self.assertIn("args", parameters, "command() has no args parameter")
            annotation = parameters["args"].annotation
            self.assertIsNotNone(annotation, "args needs an annotation")
            text = ast.dump(annotation)
            self.assertIn("Tuple", text)
            self.assertIn("str", text)
        self.assertTrue(found, "GitCommand.command was not found")


if __name__ == "__main__":
    unittest.main()
