"""Example gameplay component shipped to the player build."""

from infernux.components import InxComponent, serialized_field
from infernux.lib import Vector3, quatf


class ExampleRotator(InxComponent):
    speed: float = serialized_field(default=30.0)

    def update(self, delta_time: float) -> None:
        self.transform.rotation = (
            quatf.angle_axis(self.speed * delta_time, Vector3(0.0, 1.0, 0.0))
            * self.transform.rotation
        )
