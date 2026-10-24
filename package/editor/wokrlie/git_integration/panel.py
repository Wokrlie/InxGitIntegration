"""Example panel available only inside the editor."""

from infernux.engine.interaction import PanelInteractionDescriptor
from infernux.engine.ui.editor_panel import EditorPanel
from infernux.engine.ui.panel_registry import editor_panel


@editor_panel(
    "Git integration",
    type_id="wokrlie.git_integration",
    title_key="wokrlie.git_panel",
    menu_path="Extensions/Git Integration",
    menu_path_keys=(
        "menu.extensions",
        "wokrlie.git_integration.menu_root",
    ),
    interaction=PanelInteractionDescriptor(),
)
class GitIntegrationPanel(EditorPanel):
    def __init__(self) -> None:
        super().__init__("Git Integration", "wokrlie.git_integration.panel")

    def _intial_size(self) -> tuple[float, float]:
        return 420.0, 240.0

    def on_render_content(self, ctx) -> None:
        ctx.label("Source Control")
        ctx.begin_group("Changes")

        if ctx.tree_node("Staged Changes"):
            ctx.tree_pop()
        
        if ctx.tree_node("Changes"):
            ctx.tree_pop()
        
        ctx.end_group()
