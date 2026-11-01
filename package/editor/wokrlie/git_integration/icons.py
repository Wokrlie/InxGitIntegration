"""Vector icons for the Git panel.

The icon geometry comes from Lucide (https://lucide.dev), which is released
under the ISC License and is free for commercial use. The ISC license asks
that the copyright notice travels with redistributed copies, so it is
reproduced in ``package/plugin_pages/license.md``, which ships inside the
plugin archive as the plugin's License page.

Every icon is stored as the inner markup of a 24x24 Lucide SVG. They are
rasterized at runtime through the Engine's LunaSVG backend and uploaded as
pinned ImGui textures, so one vector asset can be drawn in any colour without
shipping a pre-rendered PNG per colour.

Icons are embedded in the module rather than shipped as files so that the
plugin never depends on where its package happens to be unpacked, and so the
build stays byte-for-byte deterministic.
"""

from __future__ import annotations

from infernux import Debug
from infernux.lib import TextureLoader


#: Version of the Lucide release the geometry below was taken from.
LUCIDE_VERSION = "0.544.0"

#: Inner markup of each 24x24 Lucide SVG, keyed by the name used here.
ICON_PATHS: dict[str, str] = {
    # -- action buttons -------------------------------------------------
    "stage": '<path d="M5 12h14" /><path d="M12 5v14" />',
    "unstage": '<path d="M5 12h14" />',
    "stage-all": (
        '<path d="M16 5H3" /><path d="M11 12H3" /><path d="M16 19H3" />'
        '<path d="M18 9v6" /><path d="M21 12h-6" />'
    ),
    "refresh": (
        '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />'
        '<path d="M21 3v5h-5" />'
        '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />'
        '<path d="M8 16H3v5" />'
    ),
    # -- file status ----------------------------------------------------
    "added": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4" />'
        '<path d="M9 15h6" /><path d="M12 18v-6" />'
    ),
    "modified": (
        '<path d="M12.5 22H18a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v9.5" />'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4" />'
        '<path d="M13.378 15.626a1 1 0 1 0-3.004-3.004l-5.01 5.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z" />'
    ),
    "deleted": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4" />'
        '<path d="M9 15h6" />'
    ),
    "renamed": (
        '<path d="m10 18 3-3-3-3" />'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4" />'
        '<path d="M4 11V4a2 2 0 0 1 2-2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h7" />'
    ),
    "copied": (
        '<rect width="14" height="14" x="8" y="8" rx="2" ry="2" />'
        '<path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />'
    ),
    "conflicted": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />'
        '<path d="M12 9v4" /><path d="M12 17h.01" />'
    ),
    "untracked": (
        '<path d="M12 17h.01" />'
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z" />'
        '<path d="M9.1 9a3 3 0 0 1 5.82 1c0 2-3 3-3 3" />'
    ),
    "ignored": (
        '<path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49" />'
        '<path d="M14.084 14.158a3 3 0 0 1-4.242-4.242" />'
        '<path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143" />'
        '<path d="m2 2 20 20" />'
    ),
}

#: Git porcelain status code -> icon name.
STATUS_ICONS: dict[str, str] = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "U": "conflicted",
    "?": "untracked",
    "!": "ignored",
}

#: Git porcelain status code -> RGBA colour.
STATUS_COLORS: dict[str, tuple[float, float, float, float]] = {
    "A": (0.30, 0.76, 0.45, 1.0),   # green
    "M": (0.89, 0.71, 0.30, 1.0),   # yellow
    "D": (0.92, 0.34, 0.34, 1.0),   # red
    "R": (0.45, 0.65, 0.95, 1.0),   # blue
    "C": (0.45, 0.65, 0.95, 1.0),   # blue
    "U": (0.95, 0.55, 0.20, 1.0),   # orange
    "?": (0.40, 0.72, 0.88, 1.0),   # cyan
    "!": (0.55, 0.55, 0.55, 1.0),   # grey
}

#: Git porcelain status code -> translation key naming that status.
STATUS_LABELS: dict[str, str] = {
    "A": "wokrlie.git_integration.status_added",
    "M": "wokrlie.git_integration.status_modified",
    "D": "wokrlie.git_integration.status_deleted",
    "R": "wokrlie.git_integration.status_renamed",
    "C": "wokrlie.git_integration.status_copied",
    "U": "wokrlie.git_integration.status_conflicted",
    "?": "wokrlie.git_integration.status_untracked",
    "!": "wokrlie.git_integration.status_ignored",
}

#: Neutral colour for the action buttons, matching the Engine text tone.
NEUTRAL_COLOR = (0.84, 0.84, 0.84, 1.0)


def _to_hex(color: tuple[float, float, float, float]) -> str:
    """Convert an RGBA float tuple into an ``#rrggbb`` string."""
    r, g, b = (max(0.0, min(1.0, channel)) for channel in color[:3])
    return "#{:02x}{:02x}{:02x}".format(
        int(round(r * 255.0)), int(round(g * 255.0)), int(round(b * 255.0))
    )


def _svg_document(body: str, color: str, edge: int) -> bytes:
    """Build a standalone SVG document for one Lucide icon."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{edge}" height="{edge}" '
        'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    ).format(edge=edge, color=color, body=body).encode("utf-8")


class IconCache:
    """Rasterize Lucide icons and publish them as pinned ImGui textures.

    The Engine uploads textures asynchronously, so an icon can report a
    texture id of ``0`` for the first frames while it is still in flight.
    Nothing is cached in that case, and the next render retries.
    """

    def __init__(self, native_engine, edge: int = 32) -> None:
        self._native = native_engine
        self._edge = max(8, int(edge))
        self._textures: dict[tuple[str, str], int] = {}

    def get(self, name: str, color: tuple[float, float, float, float] = NEUTRAL_COLOR) -> int:
        """Return the ImGui texture id for *name* in *color*, or ``0``."""
        body = ICON_PATHS.get(name)
        if body is None or self._native is None:
            return 0

        hex_color = _to_hex(color)
        key = (name, hex_color)
        cached = self._textures.get(key)
        if cached:
            return cached

        texture_name = f"wokrlie.git_integration.icon.{name}.{hex_color[1:]}"
        try:
            if not self._native.has_imgui_texture(texture_name):
                image = TextureLoader.load_from_memory(
                    _svg_document(body, hex_color, self._edge),
                    svg_max_size=self._edge,
                )
                if image is None or not image.is_valid():
                    return 0
                self._native.submit_imgui_texture(
                    texture_name,
                    image.get_pixels(),
                    int(image.width),
                    int(image.height),
                    False,
                    True,
                )
            texture_id = int(self._native.get_imgui_texture_id(texture_name) or 0)
        except RuntimeError as exc:
            Debug.log_suppressed("GitIntegrationPanel.icon", exc)
            return 0

        if texture_id:
            self._textures[key] = texture_id
        return texture_id

    def status_icon(self, status: str) -> int:
        """Return the texture id for a git porcelain status code."""
        name = STATUS_ICONS.get(status)
        if name is None:
            return 0
        return self.get(name, STATUS_COLORS.get(status, NEUTRAL_COLOR))
