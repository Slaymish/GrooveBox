from dataclasses import dataclass
from typing import Protocol

@dataclass
class PadEvent:
    pad_id: int
    pressed: bool

class InputDevice(Protocol):
    def poll_events(self) -> list[PadEvent]:
        """Poll the input device for events and return a list of PadEvent."""
        ...