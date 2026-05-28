# Discord: A-Dawg#0001 (AE)
# Supports: Forza Horizon 5 / Forza Horizon 6 profile probing
# Officially: MS Store/XBOX PC App, Steam.
# Unofficially: Every version that isn't running on a console of via cloud gaming should work.
# License: MIT
# Year: 2022

from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class Color:
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 255

    def __post_init__(self):
        for name in ("r", "g", "b", "a"):
            val = getattr(self, name)
            if not isinstance(val, int) or not 0 <= val <= 255:
                raise ValueError(
                    f"Color.{name} must be an int in [0, 255], got {val!r}"
                )

    def get_struct(self) -> bytes:
        """Pack the color into a 4-byte BGRA struct (matches Forza memory layout)."""
        return struct.pack("BBBB", self.r, self.g, self.b, self.a)


@dataclass(frozen=True)
class Shape:
    type_id: int
    x: int
    y: int
    w: float
    h: float
    rot_deg: int
    color: Color
    is_mask: bool
