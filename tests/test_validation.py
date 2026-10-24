"""A plugin fork may replace every starter example with its own payload."""

from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest


class PackageValidationTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        validator = Path(__file__).resolve().parents[1] / ".infernux-dev/validate.py"
        self.script = self.root / ".infernux-dev/validate.py"
        self.script.parent.mkdir()
        shutil.copyfile(validator, self.script)
        self.package = self.root / "package"
        self.package.mkdir()
        self.manifest = {
            "reference": "test/hello", "name": "Hello", "version": "0.1.1",
            "engine": ">=0.4,<0.5",
        }
        self.write_manifest()
        for name in ("README.md", "README.zh-CN.md", "LICENSE", "package.py"):
            (self.root / name).write_text("", encoding="utf-8")

    def write_manifest(self):
        (self.package / "inx_package.json").write_text(
            json.dumps(self.manifest), encoding="utf-8"
        )

    def write(self, relative, text):
        destination = self.package / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")

    def validate(self):
        return subprocess.run(
            [sys.executable, "-S", str(self.script)], cwd=self.root,
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_component_only_plugin_without_preloads_is_valid(self):
        self.write("runtime/hello.py", "import infernux as inx\nclass Hello(inx.InxComponent):\n    pass\n")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_asset_only_plugin_without_python_is_valid(self):
        self.write("runtime/data/settings.json", '{"speed": 3}')
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_short_bilingual_guide_does_not_need_the_starter_tutorial(self):
        self.write("plugin_pages/guide.md", "Attach Hello and press Play.\n")
        self.write("plugin_pages/guide.zh-CN.md", "挂载 Hello，然后进入播放。\n")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_python_remains_rejected(self):
        self.write("runtime/hello.py", "class Hello(\n")
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SyntaxError", result.stderr)

    def test_missing_manifest_field_remains_rejected(self):
        del self.manifest["version"]
        self.write_manifest()
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing manifest fields: version", result.stderr)

    def test_unsupported_manifest_dependency_field_remains_rejected(self):
        self.manifest["dependencies"] = []
        self.write_manifest()
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported manifest fields: dependencies", result.stderr)

    def test_runtime_editor_imports_are_rejected_in_both_package_spellings(self):
        for source in (
            "import infernux.engine.ui\n",
            "from infernux.engine.ui import Panel\n",
            "from infernux.engine import ui\n",
            "import Infernux.engine.ui\n",
        ):
            with self.subTest(source=source):
                self.write("runtime/hello.py", source)
                result = self.validate()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Runtime source imports Editor code", result.stderr)

    def test_runtime_cannot_import_the_plugins_actual_editor_package(self):
        self.write("editor/studio/tools/__init__.py", "")
        for source in (
            "import studio.tools\n",
            "from studio import tools\n",
            "from studio.tools import Panel\n",
        ):
            with self.subTest(source=source):
                self.write("runtime/hello.py", source)
                result = self.validate()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Runtime source imports Editor code", result.stderr)

    def test_editor_names_in_comments_and_strings_are_valid(self):
        self.write(
            "runtime/hello.py",
            '# Infernux.engine.ui belongs in Editor code.\n'
            'description = "example_plugin_editor documentation"\n',
        )
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runtime_subpackages_and_external_libraries_are_valid(self):
        self.write("editor/studio/tools/__init__.py", "")
        self.write("runtime/studio/game/__init__.py", "")
        self.write(
            "runtime/hello.py",
            "import infernux.renderstack\nimport numpy\n"
            "from packaging.version import Version\nfrom studio import game\n",
        )
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_external_modules_in_a_shared_namespace_are_valid(self):
        self.write("editor/studio/tools/__init__.py", "")
        self.write("runtime/hello.py", "from studio import external_library\n")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_relative_editor_import_is_rejected(self):
        self.write("editor/studio/editor_tools.py", "")
        self.write("runtime/studio/hello.py", "from . import editor_tools\n")
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Runtime source imports Editor code", result.stderr)

    def test_editor_source_can_import_editor_apis(self):
        self.write("editor/studio/tools.py", "from infernux.engine.ui import Panel\n")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
