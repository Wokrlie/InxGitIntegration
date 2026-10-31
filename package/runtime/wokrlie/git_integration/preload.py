"""Runtime lifecycle hook for the Git Integration plugin.

The plugin only provides an Editor panel, so there is nothing to register in
the player runtime. The hook is kept so the package keeps a stable runtime
role, and it is the documented place to initialise runtime services later.
"""

from infernux.lifecycle import InxPreload, PreloadContext


class GitIntegrationRuntimePreload(InxPreload):
    """Runtime preload for a plugin that ships no runtime services."""

    def preload(self, context: PreloadContext) -> None:
        # Import heavy runtime dependencies here once, before scene scripts run.
        # Reversible resources should be registered with context.add_cleanup().
        pass

    def unload(self) -> None:
        pass
