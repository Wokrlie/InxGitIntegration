"""The shape of the panel's background actions.

``GitCommand.command`` reads ``args[0]`` to name the worker thread, so a
callable in that slot raises ``TypeError: 'function' object is not
subscriptable`` the first time the action runs. That happened once: the
unstage action passed a function where an argument list was expected.

The mistake is invisible in a review — the call looks reasonable — so the
shape of every call is checked here instead.
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
    def test_every_action_starts_with_an_argument_tuple(self):
        tree = ast.parse(PANEL.read_text(encoding="utf-8"))
        calls = list(calls_named(tree, "_start_action"))
        self.assertGreater(len(calls), 0, "no _start_action call was found")
        for call in calls:
            with self.subTest(line=call.lineno):
                self.assertTrue(
                    call.args,
                    "_start_action needs the argument list of the command",
                )
                self.assertIsInstance(
                    call.args[0],
                    ast.Tuple,
                    "the first argument of _start_action has to be a tuple "
                    "of git arguments, not a callable",
                )

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
