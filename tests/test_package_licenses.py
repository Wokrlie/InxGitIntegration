"""The plugin archive must carry its licence and the third-party notices.

ISC and MIT both require their notice to travel with every copy of the
artwork, so a notice that only lives in the repository root does not
satisfy them once the plugin is distributed as an archive.
"""

from pathlib import Path
import contextlib
import io
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "package" / "plugin_pages"
sys.path.insert(0, str(ROOT))

import package as packager  # noqa: E402


LUCIDE_NOTICE = """ISC License

Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2023 as part of Feather (MIT). All other copyright (c) for Lucide are held by Lucide Contributors 2025.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE."""

FEATHER_NOTICE = """The MIT License (MIT)

Copyright (c) 2013-present Cole Bemis"""


def read_entries(path: Path) -> dict[str, bytes]:
    """Return every stored payload of an InxPack archive, keyed by path."""
    data = bytearray(path.read_bytes())
    values = packager.HEADER.unpack_from(data)
    toc_offset, _toc_bytes, payload_start, _payload_bytes, count, _strings = values[5:11]
    records = toc_offset + packager.TOC_PREFIX.size
    strings = records + count * packager.ENTRY.size
    entries: dict[str, bytes] = {}
    for index in range(count):
        entry = packager.ENTRY.unpack_from(data, records + index * packager.ENTRY.size)
        name = bytes(data[strings + entry[0]:strings + entry[0] + entry[1]]).decode("utf-8")
        start = payload_start + entry[3]
        entries[name] = bytes(data[start:start + entry[5]])
    return entries


class PackageLicenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory()
        cls.archive = Path(cls.workspace.name) / "licence.inxpkg"
        with contextlib.redirect_stdout(io.StringIO()):
            packager.build(cls.archive)
        cls.entries = read_entries(cls.archive)
        cls.metadata = packager._read_metadata(cls.archive)
        cls.licence = (ROOT / "LICENSE").read_text(encoding="utf-8").strip()

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def test_package_licence_file_matches_the_repository_licence(self):
        self.assertEqual(
            (PAGES / "LICENSE").read_bytes(),
            (ROOT / "LICENSE").read_bytes(),
        )

    def test_licence_pages_reproduce_the_licence_and_the_notices(self):
        for name in ("license.md", "license.zh-CN.md"):
            with self.subTest(page=name):
                text = (PAGES / name).read_text(encoding="utf-8")
                self.assertIn(self.licence, text)
                self.assertIn(LUCIDE_NOTICE, text)
                self.assertIn(FEATHER_NOTICE, text)

    def test_archive_carries_the_licence_and_the_notices(self):
        self.assertEqual(
            self.entries["package/plugin_pages/LICENSE"],
            (ROOT / "LICENSE").read_bytes(),
        )
        for name in ("license.md", "license.zh-CN.md"):
            with self.subTest(page=name):
                self.assertEqual(
                    self.entries[f"package/plugin_pages/{name}"],
                    (PAGES / name).read_bytes(),
                )

    def test_archive_has_no_superseded_notice_copy(self):
        self.assertNotIn("package/THIRD_PARTY_NOTICES.md", self.entries)
        self.assertNotIn("THIRD_PARTY_NOTICES.md", self.entries)

    def test_archive_carries_exactly_one_licence_file(self):
        # A second copy at the archive root would install into the project's
        # asset tree instead of next to the plugin it belongs to.
        self.assertNotIn("package/LICENSE", self.entries)
        self.assertIn("package/plugin_pages/LICENSE", self.entries)

    def test_licence_page_uses_the_engine_licence_tab_id(self):
        pages = [
            page for page in self.metadata["pages"]
            if str(page.get("id")) == "license"
        ]
        self.assertEqual(len(pages), 2)
        self.assertEqual(
            {str(page.get("locale", "")) for page in pages},
            {"", "zh-CN"},
        )

    def test_usage_pages_point_at_the_licence_page_and_the_web_copy(self):
        for name in ("usage.md", "usage.zh-CN.md"):
            with self.subTest(page=name):
                text = (PAGES / name).read_text(encoding="utf-8")
                self.assertIn("package/plugin_pages/license", text)
                self.assertIn(
                    "https://github.com/Wokrlie/InxGitIntegration/blob/main/LICENSE",
                    text,
                )


if __name__ == "__main__":
    unittest.main()
