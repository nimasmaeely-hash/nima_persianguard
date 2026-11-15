"""Command-line entrypoint: ``nima-persianguard render`` / ``validate``."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .engine import NimaPersianGuard, DEFAULT_FONT_CANDIDATES
from .scene import build_scene, SCENE_WIDTH, SCENE_HEIGHT


def _common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--width", type=int, default=SCENE_WIDTH)
    parser.add_argument("--height", type=int, default=SCENE_HEIGHT)
    parser.add_argument("--font", default=None,
                        help="path to a Persian-capable TTF (default: auto)")
    parser.add_argument("--lenient", action="store_true",
                        help="do not raise on validation issues; report only")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nima-persianguard",
        description="PersianGuard: single-pass Persian shaping, validation "
                    "and infographic rendering.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_render = sub.add_parser("render", help="render the default infographic")
    _common_args(p_render)
    p_render.add_argument("-o", "--output", default="persian_infographic.png")

    p_validate = sub.add_parser("validate", help="validate and print a report")
    _common_args(p_validate)

    args = parser.parse_args(argv)
    guard = build_scene(args.width, args.height, font_path=args.font)
    guard.strict = not args.lenient

    if args.command == "validate":
        report = guard.validate()
        print(report.summary())
        return 0 if report.ok else 1

    # mandatory resize/re-render invalidation check
    w0, h0 = guard.width, guard.height
    guard.resize_canvas(int(w0 * 0.9), int(h0 * 0.9))
    guard.resize_canvas(w0, h0)
    report = guard.validate()
    if not report.ok:
        print(report.summary(), file=sys.stderr)
        return 1
    path = guard.save(args.output)
    print("rendered %s (%dx%d, %d text blocks, state=%s)"
          % (path, guard.width, guard.height, len(guard), guard.state))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
