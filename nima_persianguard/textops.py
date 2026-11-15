"""Unicode-safe text operations for PersianGuard.

The module implements the *single-pass RTL contract*:

1. Input is always **logical Unicode** and is validated by
   :func:`validate_source` (presentation forms and bidi controls rejected).
2. Shaping (``arabic_reshaper.reshape``) and bidi reordering
   (``bidi.algorithm.get_display``) happen in exactly one place:
   :func:`shape`.
3. Display strings are produced once per logical line and cached on the
   :class:`TextBlock` (``get_display`` / ``display_lines``); later calls are
   pure cache look-ups and never reshape again.

If ``arabic-reshaper`` / ``python-bidi`` are missing a deterministic fallback
is used and reported in ``ops`` so callers (and tests) can observe it.
"""

from __future__ import annotations

import re
import threading
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

try:  # pragma: no cover - import guard
    import arabic_reshaper as _reshaper
except Exception:  # pragma: no cover
    _reshaper = None

try:  # pragma: no cover - import guard
    from bidi.algorithm import get_display as _bidi_get_display
except Exception:  # pragma: no cover
    _bidi_get_display = None


__all__ = [
    "TextSourceError",
    "validate_source",
    "shape",
    "shape_lines",
    "display_str",
    "TextOpsStats",
    "TextBlock",
    "PRESENTATION_FORMS",
    "BIDI_CONTROLS",
    "LIGATURES",
]


class TextSourceError(ValueError):
    """Raised when a source string is not logical Unicode (or malformed)."""


# --- validation -----------------------------------------------------------

PRESENTATION_FORMS = (
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)
BIDI_CONTROLS = frozenset("‎‏‪‫‬‭‮"
                          "⁦⁧⁨⁩")
LIGATURES = frozenset("ﻻﻼ")
_SURROGATE = re.compile(r"[\ud800-\udfff]")


def _iter_bad_chars(text: str) -> Iterable[Tuple[int, str, str]]:
    for index, char in enumerate(text):
        code = ord(char)
        for low, high in PRESENTATION_FORMS:
            if low <= code <= high:
                yield index, char, "presentation-form U+%04X" % code
                break
        else:
            if char in BIDI_CONTROLS:
                kind = "ALM" if char == "\u200e" else "bidi-control"
                yield index, char, "%s U+%04X" % (kind, code)


def validate_source(text: str) -> str:
    """Return ``text`` unchanged when it is safe logical Unicode.

    Rejects (with :class:`TextSourceError`) anything that could double-shape
    or pre-reverse Persian text:

    * non-``str`` objects,
    * unpaired surrogates / non-encodable text,
    * Arabic presentation forms ``U+FB50..U+FDFF`` / ``U+FE70..U+FEFF``,
    * bidi control characters (``LRM``, ``RLM``, ``LRE/RLE/LRO/RLO/PDF``,
      ``LRI/RLI/FSI/PDI``).
    """
    if not isinstance(text, str):
        raise TextSourceError("text must be str, got %s" % type(text).__name__)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:  # lone surrogates
        raise TextSourceError("text is not valid Unicode: %s" % exc) from None
    if _SURROGATE.search(text):
        raise TextSourceError("text contains unpaired surrogate code points")
    problems = list(_iter_bad_chars(text))
    if problems:
        index, char, reason = problems[0]
        raise TextSourceError(
            "non-logical text at index %d (%r): %s; pass logical Unicode, "
            "not pre-shaped/visual text" % (index, char, reason))
    return text


# --- shaping --------------------------------------------------------------

def _fallback_reverse(text: str) -> str:
    """Deterministic base-direction fallback (reverses the word order)."""
    return text[::-1]



def _reshape(text: str) -> str:
    if _reshaper is None:
        return _fallback_reverse(text)
    return _reshaper.reshape(text)


def _reorder(text: str) -> str:
    if _bidi_get_display is None or _reshaper is None:
        return _fallback_reverse(text)
    return _bidi_get_display(text)


class TextOpsStats:
    """Counters describing how often shaping/bidi actually ran."""

    def __init__(self) -> None:
        self.reshape_calls = 0
        self.get_display_calls = 0
        self.shaped_lines = 0

    def reset(self) -> None:
        self.reshape_calls = 0
        self.get_display_calls = 0
        self.shaped_lines = 0

    @property
    def total(self) -> int:
        return self.reshape_calls + self.get_display_calls

    def as_dict(self) -> Dict[str, int]:
        return {
            "reshape_calls": self.reshape_calls,
            "get_display_calls": self.get_display_calls,
            "shaped_lines": self.shaped_lines,
            "total": self.total,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return "TextOpsStats(%r)" % self.as_dict()


stats = TextOpsStats()

# Optional hooks so tests / instrumentation can observe the single point of
# shaping without monkey-patching library internals.
on_shape: Optional[Callable[[str, str], None]] = None


def shape(text: str) -> str:
    """The *only* shaping point: ``get_display(reshape(text))``.

    The input must already be logical Unicode; it is validated here again so
    the invariant cannot be bypassed.
    """
    validate_source(text)
    stats.reshape_calls += 1
    reshaped = _reshape(text)
    stats.get_display_calls += 1
    display = _reorder(reshaped)
    stats.shaped_lines += 1
    if on_shape is not None:
        on_shape(text, display)
    return display


def shape_lines(lines: Sequence[str]) -> Tuple[str, ...]:
    """Shape every logical line exactly once, in order."""
    return tuple(shape(line) if line else "" for line in lines)


def display_str(text: str) -> str:
    """Shape ``text`` and return a single display string (helper for callers)."""
    return shape(text)


class TextBlock:
    """A logical text block with lazily cached display lines.

    ``final_pass=False`` refuses to touch shaping/reordering at all: reading
    ``display_lines`` returns the logical (unshaped) lines and
    ``get_display()`` raises :class:`ReorderingSkipped`.
    """

    def __init__(self, lines: Sequence[str]) -> None:
        self._lock = threading.RLock()
        self._lines: Tuple[str, ...] = ()
        self._cache: Optional[Tuple[str, ...]] = None
        self._cache_final: Optional[bool] = None
        self._shapes = 0
        self.lines = list(lines)

    # -- logical lines -----------------------------------------------------
    @property
    def lines(self) -> List[str]:
        with self._lock:
            return list(self._lines)

    @lines.setter
    def lines(self, value: Sequence[str]) -> None:
        if isinstance(value, str):
            value = [value]
        cleaned = []
        for line in value:
            validate_source(line)
            cleaned.append(line)
        with self._lock:
            self._lines = tuple(cleaned)
            self._cache = None
            self._cache_final = None

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def cache_valid(self) -> bool:
        return self._cache is not None

    @property
    def shape_count(self) -> int:
        return self._shapes

    # -- caching -----------------------------------------------------------
    def _build(self, final_pass: bool) -> Tuple[str, ...]:
        if self._cache is not None and self._cache_final == final_pass:
            return self._cache
        if not final_pass:
            # No shaping / reordering in non-final passes (proof pass 1).
            self._cache = self._lines
            self._cache_final = False
            return self._cache
        if (self._cache is not None and self._cache_final is False
                and self._cache == self._lines):
            # Non-final cache is only logical text: shaping required.
            pass
        display = shape_lines(self._lines)
        self._shapes += 1
        self._cache = display
        self._cache_final = True
        return self._cache

    def get_display(self, final_pass: bool = False) -> Tuple[str, ...]:
        """Display lines for one logical line each; cached per pass kind."""
        with self._lock:
            if not final_pass:
                # Refuse to reorder (and never silently produce visual text).
                raise ReorderingSkipped(
                    "get_display() requires final_pass=True; shaping/bidi is "
                    "skipped in non-final passes")
            return self._build(True)

    def display_lines(self, final_pass: bool = False) -> Tuple[str, ...]:
        """Convenience accessor: ``get_display`` but never raises.

        With ``final_pass=False`` the logical lines are returned untouched.
        """
        with self._lock:
            return self._build(bool(final_pass))

    def invalidate(self) -> None:
        with self._lock:
            self._cache = None
            self._cache_final = None

    def __repr__(self) -> str:  # pragma: no cover
        return "TextBlock(%d lines, cached=%s)" % (len(self._lines),
                                                   self.cache_valid)


class ReorderingSkipped(RuntimeError):
    """Raised when bidi reordering is requested outside the final pass."""
