"""Keep the editor translation catalog and the panel that consumes it in sync.

The Editor resolves a panel title through ``t(title_key)`` and falls back to
the raw key when the key is not declared. These tests make that failure
impossible to merge: every key the panel asks for must exist in both locales.
"""

from pathlib import Path
import ast
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package"
EDITOR = PACKAGE / "editor"
PANEL = EDITOR / "wokrlie" / "git_integration" / "panel.py"
ICONS = EDITOR / "wokrlie" / "git_integration" / "icons.py"
CATALOG = EDITOR / "translations.json"

LOCALES = ("en", "zh")


def _catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _requested_keys() -> set[str]:
    """Every translation key the panel asks the Editor to resolve."""
    tree = ast.parse(PANEL.read_text(encoding="utf-8"), filename=str(PANEL))
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name != "t" or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                keys.add(first.value)
    return keys


def _status_label_keys() -> set[str]:
    """Every translation key the status table points at.

    These are resolved through a variable rather than a literal, so the panel
    scan above cannot see them.
    """
    return _table_values("STATUS_LABELS")


def _table_keys(name: str) -> set[str]:
    """Read the keys of one module-level table in ``icons.py``."""
    return _table(name, values=False)


def _table_values(name: str) -> set[str]:
    """Read the string values of one module-level table in ``icons.py``."""
    return _table(name, values=True)


def _table(name: str, *, values: bool) -> set[str]:
    tree = ast.parse(ICONS.read_text(encoding="utf-8"), filename=str(ICONS))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        elif isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                continue
            target, value = node.targets[0], node.value
        else:
            continue
        if not isinstance(target, ast.Name) or target.id != name:
            continue
        if not isinstance(value, ast.Dict):
            continue
        entries = value.values if values else value.keys
        for entry in entries:
            if isinstance(entry, ast.Constant) and isinstance(entry.value, str):
                found.add(entry.value)
    return found


def _declared_title_key() -> str:
    """The ``title_key`` passed to the ``@editor_panel`` decorator."""
    tree = ast.parse(PANEL.read_text(encoding="utf-8"), filename=str(PANEL))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "id", None) or getattr(func, "attr", None)
        if name != "editor_panel":
            continue
        for keyword in node.keywords:
            if keyword.arg == "title_key" and isinstance(keyword.value, ast.Constant):
                return str(keyword.value.value)
    raise AssertionError("panel.py does not declare a title_key")


class TranslationCatalogTests(unittest.TestCase):
    def test_catalog_declares_exactly_the_schema_and_locales(self):
        document = _catalog()
        self.assertEqual(set(document), {"$schema", "locales"})
        self.assertEqual(document["$schema"], "infernux.editor_translations")

    def test_catalog_locales_match_the_editor_locales(self):
        self.assertEqual(set(_catalog()["locales"]), set(LOCALES))

    def test_catalog_locales_declare_identical_key_sets(self):
        locales = _catalog()["locales"]
        english = set(locales["en"])
        chinese = set(locales["zh"])
        self.assertEqual(english, chinese)

    def test_catalog_keys_are_namespaced_and_non_empty(self):
        for locale, entries in _catalog()["locales"].items():
            for key, value in entries.items():
                with self.subTest(locale=locale, key=key):
                    self.assertIn(".", key)
                    self.assertTrue(value.strip())

    def test_every_requested_key_is_declared_in_every_locale(self):
        locales = _catalog()["locales"]
        for key in sorted(_requested_keys()):
            for locale in LOCALES:
                with self.subTest(key=key, locale=locale):
                    self.assertIn(key, locales[locale])

    def test_every_status_label_is_declared_in_every_locale(self):
        locales = _catalog()["locales"]
        for key in sorted(_status_label_keys()):
            for locale in LOCALES:
                with self.subTest(key=key, locale=locale):
                    self.assertIn(key, locales[locale])

    def test_status_table_covers_every_icon(self):
        """Every status that has a colour must also have a label and an icon."""
        icons = _table_keys("STATUS_ICONS")
        colors = _table_keys("STATUS_COLORS")
        labels = _table_keys("STATUS_LABELS")
        self.assertTrue(icons)
        self.assertEqual(icons, colors)
        self.assertEqual(icons, labels)

    def test_panel_title_key_is_declared(self):
        locales = _catalog()["locales"]
        title_key = _declared_title_key()
        for locale in LOCALES:
            with self.subTest(locale=locale):
                self.assertIn(title_key, locales[locale])

    def test_panel_does_not_request_keys_outside_its_namespace(self):
        for key in sorted(_requested_keys()):
            with self.subTest(key=key):
                self.assertTrue(key.startswith("wokrlie.git_integration."))


if __name__ == "__main__":
    unittest.main()
