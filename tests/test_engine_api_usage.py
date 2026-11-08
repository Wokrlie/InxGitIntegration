"""The plugin must only call Engine APIs that actually exist.

``Debug.error`` looks perfectly reasonable, but the Engine exposes
``Debug.log_error`` and nothing else with that name. The call therefore
raised ``AttributeError`` at runtime, so every Git failure in the panel was
reported as an unrelated Python traceback and the real message never
reached the Console.

A review will not catch that reliably, so this test scans the plugin
sources and fails on any method the Engine does not provide.

The allowlists below were transcribed from the Engine sources:

* ``python/infernux/debug.py`` — the ``Debug`` class.
* ``cpp/infernux/function/resources/.../InxGUIContext.h`` and
  ``python/infernux/engine/ui/BindingGUI.cpp`` — the ImGui context.

They were checked against the upstream ``master`` branch on 2026-11-06.
``input_uint`` and ``push_id_str`` were dropped from the allowlist in that
pass: the Engine no longer declares them, so keeping them would let a
call to a method that does not exist pass this test and then fail at
runtime with the very ``AttributeError`` this test exists to prevent.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "package" / "editor"

#: Methods of ``infernux.debug.Debug``.
DEBUG_METHODS = frozenset({
    "log",
    "log_warning",
    "log_error",
    "log_exception",
    "log_suppressed",
    "log_assert",
    "clear_console",
    "clear_source_entries",
    "log_internal",
    "log_debug",
    "report_script_error",
    "report_internal_error",
    "report_recovered",
})

#: Methods of ``infernux.lib.InxGUIContext``.
CONTEXT_METHODS = frozenset({
    # text and simple widgets
    "label", "field_label", "text_wrapped", "button", "radio_button",
    "checkbox", "checkbox_inspector", "checkbox_flags", "separator",
    "spacing", "dummy", "new_line", "same_line", "align_text_to_frame_padding",
    "progress_bar", "text_input", "text_area", "input_text_with_hint",
    "input_int", "input_float", "int_slider", "float_slider",
    "drag_float", "drag_int", "color_edit", "color_picker", "vector2_control",
    "vector3_control", "vector4_control", "input_text_multiline",
    # lists, combos and popups
    "selectable", "selectable_row", "selectable_list_clipped", "combo",
    "searchable_combo", "list_box", "tree_node", "tree_node_ex", "tree_pop",
    "open_popup", "begin_popup", "begin_popup_modal", "begin_popup_context_item",
    "begin_popup_context_window", "end_popup", "close_current_popup",
    "begin_tooltip", "end_tooltip", "set_tooltip",
    # containers
    "begin_group", "end_group", "begin_framed_group", "end_framed_group",
    "begin_child", "end_child", "begin_window", "end_window", "begin_tab_bar",
    "end_tab_bar", "begin_tab_item", "end_tab_item", "begin_main_menu_bar",
    "end_main_menu_bar", "begin_menu", "end_menu", "menu_item",
    "collapsing_header", "render_compact_section_header", "begin_table",
    "end_table", "table_setup_column", "table_headers_row", "table_next_row",
    "table_set_column_index", "table_next_column", "invisible_button",
    # images and drawing
    "image", "image_button", "draw_rect", "draw_filled_rect",
    "draw_filled_rect_rotated", "draw_line", "draw_circle",
    "draw_filled_circle", "draw_image_rect", "draw_text", "draw_text_aligned",
    # style and state
    "push_style_color", "pop_style_color", "push_style_var_float",
    "push_style_var_vec2", "pop_style_var", "begin_disabled", "end_disabled",
    "push_id", "pop_id", "set_next_item_width",
    "set_next_item_open", "set_next_item_allow_overlap", "set_next_window_size",
    "set_next_window_pos", "set_next_window_focus", "set_window_focus",
    "set_window_font_scale", "set_keyboard_focus_here", "set_cursor_pos_x",
    "set_cursor_pos_y", "set_cursor_screen_pos", "set_scroll_x", "set_scroll_y",
    "set_scroll_here_y", "set_clipboard_text", "get_clipboard_text",
    "set_mouse_cursor",
    # queries
    "is_item_clicked", "is_item_active", "is_item_edited", "is_any_item_active",
    "is_item_hovered", "is_item_focused", "is_item_deactivated",
    "is_item_deactivated_after_edit", "is_window_focused", "is_window_hovered",
    "is_mouse_button_down", "is_mouse_button_clicked", "is_mouse_double_clicked",
    "is_mouse_dragging", "is_key_down", "is_key_pressed", "is_key_released",
    "is_current_window_content_presented", "is_virtualized_region_visible",
    "want_text_input", "get_mouse_pos_x", "get_mouse_pos_y",
    "get_mouse_wheel_delta", "get_mouse_drag_delta_x", "get_mouse_drag_delta_y",
    "get_window_pos_x", "get_window_pos_y", "get_window_width",
    "get_item_rect_min_x", "get_item_rect_min_y", "get_item_rect_max_x",
    "get_item_rect_max_y", "get_cursor_pos_x", "get_cursor_pos_y",
    "get_content_region_avail_width", "get_content_region_avail_height",
    "get_scroll_y", "get_scroll_max_y", "get_dpi_scale", "calc_text_width",
    "get_main_viewport_bounds", "get_display_bounds", "get_global_mouse_pos_x",
    "get_global_mouse_pos_y",
})

CALL = re.compile(r"\b(Debug|ctx)\.([a-z_][a-z0-9_]*)\s*\(")


def editor_sources():
    for path in sorted(EDITOR.rglob("*.py")):
        yield path, path.read_text(encoding="utf-8")


class EngineApiUsageTests(unittest.TestCase):
    def test_allowlists_are_populated(self):
        self.assertGreater(len(DEBUG_METHODS), 5)
        self.assertGreater(len(CONTEXT_METHODS), 20)

    def test_plugin_only_calls_engine_apis_that_exist(self):
        unknown = []
        for path, source in editor_sources():
            for prefix, name in CALL.findall(source):
                allowed = DEBUG_METHODS if prefix == "Debug" else CONTEXT_METHODS
                if name not in allowed:
                    unknown.append(f"{path.relative_to(ROOT)}: {prefix}.{name}")
        self.assertEqual(
            unknown, [],
            "These Engine methods do not exist. The call will raise "
            "AttributeError at runtime: " + ", ".join(sorted(set(unknown))),
        )

    def test_debug_errors_use_the_method_that_exists(self):
        """The regression that started this: ``Debug.error`` is not an API."""
        for path, source in editor_sources():
            self.assertNotIn(
                "Debug.error(", source,
                f"{path.relative_to(ROOT)} still calls the non-existent Debug.error",
            )


if __name__ == "__main__":
    unittest.main()
