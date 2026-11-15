"""NimaPersianGuard: the render engine with the final-pass state machine.

State machine per render::

    CLEAN --(mutate: add/update/move/resize)--> DIRTY
    DIRTY  --(validate)--> VALIDATING --> CLEAN (ok) | INVALID (issues)

The render pass is the *final pass*; only it produces display strings, via
``textops.TextBlock.display_lines(final_pass=True)``. Measurement/wrapping
passes (``final_pass=False``) never shape or reorder text.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from . import textops
from .textops import TextBlock, TextSourceError, stats
from .validator import ValidationReport, ValidationError, validate_layout

__all__ = ["NimaPersianGuard", "TextItem", "DEFAULT_FONT_CANDIDATES"]


DEFAULT_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/Vazir.ttf",
    "Vazir.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


State = str  # "clean" | "dirty" | "validating" | "invalid"


def _find_font(explicit: Optional[str] = None) -> str:
    if explicit:
        if not os.path.exists(explicit):
            raise FileNotFoundError("font not found: %s" % explicit)
        return explicit
    for candidate in DEFAULT_FONT_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(
        "No Persian-capable TTF found; pass font_path explicitly")


@dataclass
class TextItem:
    """A positioned logical text block owned by the engine."""

    key: str
    block: TextBlock
    x: float
    y: float
    font_size: float
    color: Tuple[int, int, int]
    anchor: str = "ra"          # Pillow anchor, e.g. ra/ma/la (no mirroring)
    box: Optional[Tuple[float, float, float, float]] = None  # x, y, w, h
    align: str = "right"
    visible: bool = True
    line_spacing: float = 1.25
    _bbox: Optional[Tuple[float, float, float, float]] = None

    # -- measured bounding box --------------------------------------------
    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        if self._bbox is None:
            return (self.x, self.y, self.x, self.y)
        return self._bbox

    def set_bbox(self, box: Tuple[float, float, float, float]) -> None:
        self._bbox = box


class NimaPersianGuard:
    """Modular Persian layout/render engine.

    Contract highlights
    -------------------
    * ``final_pass=True`` is the only mode in which shaping + bidi run, and
      it runs **exactly once per logical line** (results are cached).
    * ``final_pass=False`` measures without touching shaping: reordering is
      skipped and attempting ``block.get_display()`` raises.
    * Any mutation (text, font size, canvas scale, position, ...) sets the
      dirty flag and forces re-validation before the next render.
    """

    def __init__(self, width: int = 3000, height: int = 2000,
                 font_path: Optional[str] = None,
                 background: Tuple[int, int, int] = (12, 14, 22),
                 strict: bool = True) -> None:
        self._lock = threading.RLock()
        self.width = int(width)
        self.height = int(height)
        self.background = background
        self.strict = strict
        self.font_path = _find_font(font_path)
        self._font_cache: Dict[int, ImageFont.FreeTypeFont] = {}
        self._items: Dict[str, TextItem] = {}
        self._order: List[str] = []
        self._state: State = "clean"
        self._last_report: Optional[ValidationReport] = None
        self._hooks: List[Callable[[State, str], None]] = []
        self._final_shaping_runs = 0
        self._last_scale: float = 1.0

    # ------------------------------------------------------------------ state
    @property
    def state(self) -> State:
        return self._state

    @property
    def dirty(self) -> bool:
        return self._state in ("dirty", "invalid")

    def add_hook(self, hook: Callable[[State, str], None]) -> None:
        self._hooks.append(hook)

    def _set_state(self, state: State, reason: str = "") -> None:
        self._state = state
        for hook in list(self._hooks):
            hook(state, reason)

    def _touch(self, reason: str) -> None:
        """Dirty-flag hook called by every mutator."""
        with self._lock:
            for item in self._items.values():
                item.block.invalidate()
            self._set_state("dirty", reason)

    # ------------------------------------------------------------------- text
    def add_text(self, key: str, text: str, x: float, y: float,
                 box: Optional[Tuple[float, float, float, float]] = None,
                 font_size: float = 30, color=(255, 255, 255),
                 align: str = "right", anchor: Optional[str] = None,
                 visible: bool = True) -> TextItem:
        block = TextBlock(text.split("\n") if "\n" in text else [text])
        if anchor is None:
            anchor = {"right": "ra", "center": "ma", "left": "la"}.get(align, "ra")
        item = TextItem(key=key, block=block, x=x, y=y, font_size=font_size,
                        color=tuple(color), anchor=anchor, box=box,
                        align=align, visible=visible)
        with self._lock:
            if key in self._items:
                raise KeyError("duplicate key: %s" % key)
            self._items[key] = item
            self._order.append(key)
        self._touch("add_text:%s" % key)
        return item

    def update_text(self, key: str, text: str) -> None:
        item = self._require(key)
        try:
            item.block.lines = text.split("\n") if "\n" in text else [text]
        except TextSourceError:
            raise
        self._touch("update_text:%s" % key)

    def set_font_size(self, key: str, size: float) -> None:
        item = self._require(key)
        if size <= 0:
            raise ValueError("font size must be positive")
        item.font_size = float(size)
        self._touch("set_font_size:%s" % key)

    def move_text(self, key: str, x: float, y: float) -> None:
        item = self._require(key)
        item.x, item.y = x, y
        self._touch("move_text:%s" % key)

    def set_visible(self, key: str, visible: bool) -> None:
        self._require(key).visible = bool(visible)
        self._touch("set_visible:%s" % key)

    def _require(self, key: str) -> TextItem:
        try:
            return self._items[key]
        except KeyError:
            raise KeyError("unknown text key: %s" % key) from None

    # ----------------------------------------------------------------- canvas
    def resize_canvas(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("canvas size must be positive")
        self.width, self.height = int(width), int(height)
        self._touch("resize_canvas")

    def scale_canvas(self, factor: float) -> None:
        if factor <= 0:
            raise ValueError("scale must be positive")
        self.resize_canvas(int(self.width * factor), int(self.height * factor))
        self._last_scale = factor

    # ------------------------------------------------------------------ fonts
    def get_font(self, size: float) -> ImageFont.FreeTypeFont:
        size = max(1, int(round(size)))
        font = self._font_cache.get(size)
        if font is None:
            font = ImageFont.truetype(self.font_path, size)
            self._font_cache[size] = font
        return font

    def auto_fit_font_size(self, key: str, min_size: float = 10.0,
                           max_size: float = 120.0) -> float:
        """Shrink font size until measured text fits its declared box."""
        item = self._require(key)
        if item.box is None:
            return item.font_size
        size = max(min_size, min(max_size, item.font_size))
        _, _, max_w, max_h = item.box
        while size > min_size:
            lines = self._wrap(item, size)
            if self._measure_block(item, lines, size) <= (max_w, max_h):
                break
            size -= 1.0
        if item.font_size != size:
            item.font_size = size
            self._touch("auto_fit_font_size:%s" % key)
        return size

    # --------------------------------------------------------------- measuring
    def _wrap(self, item: TextItem, size: float) -> List[str]:
        """Direction-agnostic wrapping (no shaping: character-count metrics)."""
        font = self.get_font(size)
        if item.box is None:
            return list(item.block.lines)
        max_w = item.box[2]
        out: List[str] = []
        for line in item.block.lines:
            if not line:
                out.append(line)
                continue
            try:
                width = font.getlength(line)
            except Exception:
                width = len(line) * size * 0.6
            if width <= max_w:
                out.append(line)
                continue
            words = line.split(" ")
            cur = ""
            for word in words:
                candidate = (cur + " " + word).strip()
                try:
                    w = font.getlength(candidate)
                except Exception:
                    w = len(candidate) * size * 0.6
                if cur and w > max_w:
                    out.append(cur)
                    cur = word
                else:
                    cur = candidate
            if cur:
                out.append(cur)
        return out

    def _measure_block(self, item: TextItem, lines: Sequence[str],
                       size: float) -> Tuple[float, float]:
        font = self.get_font(size)
        try:
            w = max((font.getlength(line) for line in lines), default=0.0)
        except Exception:
            w = max((len(line) for line in lines), default=0) * size * 0.6
        line_h = size * item.line_spacing
        return w, line_h * len(lines)

    def measure(self, final_pass: bool = False) -> Dict[str, Tuple[float, float, float, float]]:
        """Measure all visible blocks (no shaping when ``final_pass=False``)."""
        boxes: Dict[str, Tuple[float, float, float, float]] = {}
        with self._lock:
            items = [self._items[k] for k in self._order if self._items[k].visible]
        for item in items:
            lines = item.block.display_lines(final_pass=final_pass)
            w, h = self._measure_block(item, lines, item.font_size)
            x, y = item.x, item.y
            if item.box is not None:
                bx, by, bw, bh = item.box
                if item.align == "right":
                    x = bx + bw
                elif item.align == "center":
                    x = bx + bw / 2.0
                else:
                    x = bx
                y = by
            if item.anchor.startswith("r"):
                x0 = x - w
            elif item.anchor.startswith("m"):
                x0 = x - w / 2.0
            else:
                x0 = x
            if item.anchor.endswith("a"):
                y0 = y
            elif item.anchor.endswith("m"):
                y0 = y - h / 2.0
            else:
                y0 = y - h
            item.set_bbox((x0, y0, x0 + w, y0 + h))
            boxes[item.key] = item.bbox
        return boxes

    # -------------------------------------------------------------- validation
    @property
    def last_report(self) -> Optional[ValidationReport]:
        return self._last_report

    def validate(self, allow_overlap: Iterable[Tuple[str, str]] = (),
                 **kwargs) -> ValidationReport:
        self.measure(final_pass=False)
        with self._lock:
            items = [self._items[k] for k in self._order]
        report = validate_layout(items, self.width, self.height,
                                 allow_overlap=allow_overlap, **kwargs)
        self._last_report = report
        self._set_state("validating", "validate")
        self._set_state("clean" if report.ok else "invalid",
                        "validate:%s" % ("ok" if report.ok else "issues"))
        if self.strict and not report.ok:
            raise ValidationError(report.summary())
        return report

    # ----------------------------------------------------------------- render
    def render(self, allow_overlap: Iterable[Tuple[str, str]] = (),
               **kwargs) -> Image.Image:
        """Full render: validate (dirty -> clean) then draw the final pass."""
        if self.dirty or self._last_report is None:
            self.validate(allow_overlap=allow_overlap, **kwargs)
        image = Image.new("RGB", (self.width, self.height), self.background)
        draw = ImageDraw.Draw(image)
        stats.reset()
        self._final_shaping_runs += 1
        with self._lock:
            items = [self._items[k] for k in self._order if self._items[k].visible]
        for item in items:
            lines = item.block.display_lines(final_pass=True)  # shapes once
            self._draw_block(draw, item, lines)
        return image

    def _draw_block(self, draw: ImageDraw.ImageDraw, item: TextItem,
                    lines: Sequence[str]) -> None:
        font = self.get_font(item.font_size)
        line_h = item.font_size * item.line_spacing
        x, y = item.x, item.y
        if item.box is not None:
            bx, by, bw, bh = item.box
            if item.align == "right":
                x = bx + bw
            elif item.align == "center":
                x = bx + bw / 2.0
            else:
                x = bx
            y = by
        anchor_x = {"right": "r", "center": "m", "left": "l"}.get(item.align, "r")
        for index, display in enumerate(lines):
            draw.text((x, y + index * line_h), display, font=font,
                      fill=item.color, anchor=anchor_x + "a")

    # ------------------------------------------------------------------- save
    def save(self, path: str, **kwargs) -> str:
        image = self.render(**kwargs)
        image.save(path, optimize=True)
        return path

    # ----------------------------------------------------------------- intros
    @property
    def keys(self) -> List[str]:
        return list(self._order)

    @property
    def final_shaping_runs(self) -> int:
        return self._final_shaping_runs

    @property
    def ops_stats(self) -> Dict[str, int]:
        return stats.as_dict()

    def __len__(self) -> int:
        return len(self._items)
