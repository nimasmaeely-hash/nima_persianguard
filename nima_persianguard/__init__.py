"""PersianGuard: Persian shaping, layout validation, and infographic rendering."""

from .engine import NimaPersianGuard, TextItem
from .scene import build_scene, SCENE_WIDTH, SCENE_HEIGHT
from .textops import (TextSourceError, ReorderingSkipped, validate_source,
                      shape, TextBlock, stats as text_stats)
from .validator import ValidationReport, ValidationError, validate_layout

__version__ = "1.1.0"

__all__ = [
    "NimaPersianGuard", "TextItem", "build_scene", "SCENE_WIDTH",
    "SCENE_HEIGHT", "validate_source", "shape", "TextBlock",
    "TextSourceError", "ReorderingSkipped", "ValidationReport",
    "ValidationError", "validate_layout", "text_stats", "__version__",
]
