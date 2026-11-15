"""Post-layout validation for PersianGuard scenes.

Checks performed:

* **containment** — every block's bounding box must lie inside the canvas and
  inside its own declared box (if any);
* **overlap** — pairwise bounding-box intersection between blocks that are
  not explicitly allowed to intersect (e.g. a heading and its subtitle are
  usually checked, so overlaps are reported, not silently ignored);
* **font-size limits** — ``min_font`` <= size <= ``max_font``;
* **text containment** — every block must expose at least one non-empty
  logical line and display lines must not be empty when final.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = ["Issue", "ValidationReport", "validate_layout", "boxes_overlap"]


@dataclass(frozen=True)
class Issue:
    kind: str            # "overlap" | "font" | "containment" | "text"
    key: str
    detail: str
    other: Optional[str] = None

    def as_dict(self) -> Dict[str, object]:
        return {"kind": self.kind, "key": self.key, "detail": self.detail,
                "other": self.other}

    def __str__(self) -> str:
        suffix = (" [%s]" % self.other) if self.other else ""
        return "%s: %s%s - %s" % (self.kind, self.key, suffix, self.detail)


@dataclass
class ValidationReport:
    ok: bool = True
    issues: List[Issue] = field(default_factory=list)
    checked: int = 0

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)
        self.ok = False

    @property
    def errors(self) -> List[Issue]:
        return list(self.issues)

    def summary(self) -> str:
        if self.ok:
            return "OK: %d blocks validated" % self.checked
        lines = ["FAILED: %d issue(s) in %d blocks" % (len(self.issues),
                                                       self.checked)]
        lines.extend("  - %s" % issue for issue in self.issues)
        return "\n".join(lines)

    def raise_if_invalid(self) -> None:
        if not self.ok:
            raise ValidationError(self.summary())


class ValidationError(RuntimeError):
    """Raised when a scene fails validation."""


def boxes_overlap(a: Tuple[float, float, float, float],
                  b: Tuple[float, float, float, float],
                  pad: float = 0.0) -> bool:
    """True when axis-aligned boxes ``(x0, y0, x1, y1)`` intersect."""
    return (a[0] < b[2] - pad and b[0] < a[2] - pad
            and a[1] < b[3] - pad and b[1] < a[3] - pad)


def validate_layout(blocks: Sequence[object],
                    width: float,
                    height: float,
                    min_font: float = 8.0,
                    max_font: float = 400.0,
                    allow_overlap: Iterable[Tuple[str, str]] = ()) -> ValidationReport:
    """Validate positioned blocks (objects exposing the engine's block API)."""
    report = ValidationReport()
    allowed = {frozenset(pair) for pair in allow_overlap}
    positioned = []
    for block in blocks:
        report.checked += 1
        if not block.visible:
            continue
        # font-size limits
        if not (min_font <= block.font_size <= max_font):
            report.add(Issue("font", block.key,
                             "font size %.1f outside [%.1f, %.1f]"
                             % (block.font_size, min_font, max_font)))
        # text containment
        logical = block.block.lines
        if not any(line.strip() for line in logical):
            report.add(Issue("text", block.key, "block has no text"))
            continue
        box = block.bbox
        if box[2] <= box[0] or box[3] <= box[1]:
            report.add(Issue("text", block.key,
                             "empty measured box %r" % (box,)))
            continue
        positioned.append(block)
        # canvas containment
        if box[0] < 0 or box[1] < 0 or box[2] > width or box[3] > height:
            report.add(Issue("containment", block.key,
                             "box %r outside canvas %dx%d"
                             % (box, width, height)))
        declared = block.box
        if declared is not None:
            dx0, dx1 = declared[0], declared[0] + declared[2]
            if dx0 - 1 > box[0] or dx1 + 1 < box[2]:
                report.add(Issue("containment", block.key,
                                 "text wider (%.1f..%.1f) than its box "
                                 "(%.1f..%.1f)" % (box[0], box[2], dx0, dx1)))

    for i, first in enumerate(positioned):
        for second in positioned[i + 1:]:
            if frozenset((first.key, second.key)) in allowed:
                continue
            if boxes_overlap(first.bbox, second.bbox):
                report.add(Issue("overlap", first.key,
                                 "bounding boxes intersect",
                                 other=second.key))
    return report
