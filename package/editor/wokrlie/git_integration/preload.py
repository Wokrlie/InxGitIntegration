"""Editor-only lifecycle and UI registration."""

from importlib import import_module

from infernux.lifecycle import InxPreload, PreloadContext


class GitIntegrationEditorPreload(InxPreload):
    def preload(self, context: PreloadContext) -> None:
        # Imports performed here are attributed to this lifecycle transaction.
        # The Editor removes contributed panels, commands, and shortcuts before
        # reloading this file, disabling the plugin, or closing the project.
        import_module("wokrlie.git_integration.panel")

    def unload(self) -> None:
        pass
