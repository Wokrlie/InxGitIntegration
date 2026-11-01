"""The bundled icon artwork must stay renderable by the Engine's SVG backend.

The Engine rasterizes these documents through LunaSVG at runtime, so a
malformed document only fails once the panel is open in the Editor. These
checks keep that failure out of the repository.
"""

from pathlib import Path
import ast
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / "package" / "editor" / "wokrlie" / "git_integration" / "icons.py"

SVG_NS = "{http://www.w3.org/2000/svg}"


def _load_module() -> dict:
    """Import ``icons.py`` with the Engine modules stubbed out."""
    import sys
    import types

    infernux = types.ModuleType("infernux")

    class Debug:
        @staticmethod
        def log_suppressed(*args, **kwargs):
            pass

    infernux.Debug = Debug
    lib = types.ModuleType("infernux.lib")
    lib.TextureLoader = object()
    previous = {name: sys.modules.get(name) for name in ("infernux", "infernux.lib")}
    sys.modules["infernux"] = infernux
    sys.modules["infernux.lib"] = lib
    try:
        tree = ast.parse(ICONS.read_text(encoding="utf-8"), filename=str(ICONS))
        namespace = {"__name__": "icons_under_test"}
        exec(compile(tree, str(ICONS), "exec"), namespace)
        return namespace
    finally:
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


class IconAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()
        cls.paths = cls.module["ICON_PATHS"]
        cls.status_icons = cls.module["STATUS_ICONS"]

    def test_every_icon_is_a_well_formed_svg_document(self):
        for name, body in self.paths.items():
            with self.subTest(icon=name):
                document = self.module["_svg_document"](body, "#d6d6d6", 32)
                root = ET.fromstring(document.decode("utf-8"))
                self.assertEqual(root.tag, SVG_NS + "svg")
                self.assertEqual(root.get("viewBox"), "0 0 24 24")
                self.assertEqual(root.get("stroke"), "#d6d6d6")
                self.assertTrue(list(root), "icon has no drawable content")

    def test_icons_use_the_lucide_stroke_conventions(self):
        """LunaSVG needs a concrete stroke colour, not ``currentColor``."""
        for name, body in self.paths.items():
            with self.subTest(icon=name):
                self.assertNotIn("currentColor", body)
                root = ET.fromstring(
                    self.module["_svg_document"](body, "#d6d6d6", 32).decode("utf-8")
                )
                self.assertEqual(root.get("fill"), "none")
                self.assertEqual(root.get("stroke-width"), "2")

    def test_every_status_icon_exists(self):
        for status, icon in self.status_icons.items():
            with self.subTest(status=status):
                self.assertIn(icon, self.paths)

    def test_action_icons_exist(self):
        for icon in ("stage", "unstage", "stage-all", "refresh"):
            with self.subTest(icon=icon):
                self.assertIn(icon, self.paths)

    def test_colour_conversion_produces_valid_hex(self):
        to_hex = self.module["_to_hex"]
        self.assertEqual(to_hex((0.0, 0.0, 0.0, 1.0)), "#000000")
        self.assertEqual(to_hex((1.0, 1.0, 1.0, 1.0)), "#ffffff")
        self.assertEqual(to_hex((0.5, 0.25, 0.75, 1.0)), "#8040bf")
        # Out-of-range channels are clamped instead of producing invalid hex.
        self.assertEqual(to_hex((2.0, -1.0, 0.5, 1.0)), "#ff0080")


if __name__ == "__main__":
    unittest.main()
