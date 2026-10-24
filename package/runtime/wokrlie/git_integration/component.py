"""Example gameplay component shipped to the player build."""

from infernux.components import InxComponent, serialized_field
from infernux.lib import Vector3, quatf
from infernux import Debug


class Null(InxComponent):
    msg = "This plugin does not include any runtime components." 

    def start(self):
        Debug.log(self.msg)

    def update(self, delta_time: float) -> None:
        """Called when updated"""