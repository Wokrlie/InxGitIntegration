"""Early lifecycle for services that must exist in Editor and Player."""

from infernux.lifecycle import InxPreload, PreloadContext


class ExamplePluginPreload(InxPreload):
    def preload(self, context: PreloadContext) -> None:
        # Import heavy runtime dependencies here once, before scene scripts run.
        # Reversible resources should be registered with context.add_cleanup().
        pass

    def unload(self) -> None:
        pass
