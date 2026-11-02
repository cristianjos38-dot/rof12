import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SamRegion:
    kind: str
    coordinates: tuple


def parse_sam_markers(text: str, source_width: float, source_height: float, page_width: float, page_height: float) -> tuple:
    if source_width <= 0 or source_height <= 0:
        raise ValueError("source dimensions must be positive")
    scale_x, scale_y = page_width / source_width, page_height / source_height
    regions = []
    for kind, body in re.findall(r"<\|(box|mask);([^|]+)\|>", text):
        values = tuple(float(value.strip()) for value in body.split(","))
        if len(values) != 4:
            raise ValueError("SAM region must have four coordinates")
        regions.append(SamRegion(kind, (values[0] * scale_x, values[1] * scale_y, values[2] * scale_x, values[3] * scale_y)))
    return tuple(regions)
