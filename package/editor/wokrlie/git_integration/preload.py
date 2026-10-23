"""Editor-only lifecycle and UI registration."""

from importlib import import_module

from infernux.lifecycle import InxPreload, PreloadContext


class ExamplePluginEditorPreload(InxPreload):
    def preload(self, context: PreloadContext) -> None:
        # Imports performed here are attributed to this lifecycle transaction.
        # The Editor removes contributed panels, commands, and shortcuts before
        # reloading this file, disabling the plugin, or closing the project.
        import_module("your_studio.example_plugin_editor.panel")

    def unload(self) -> None:
        pass
