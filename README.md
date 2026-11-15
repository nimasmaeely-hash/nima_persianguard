# nima_persianguard

A clean, modular Python package extracted from the original PersianGuard
infographic scripts (`nima_persianguard.py`,
`Persian_Infographic-Nima_PersianGuard.py`). It preserves the exact text
content, layout constants and rendering behavior while separating concerns
into validation, layout, shaping and rendering modules with a stable public
API and CLI.

## Single-pass RTL contract

The package enforces the audited contract from
`shaping_bidi_review_report.txt`:

1. **Logical source only** — every text entering the engine is validated by
   `validate_source`: Arabic presentation forms (`U+FB50..U+FDFF`,
   `U+FE70..U+FEFF`) and bidi control characters (`LRE/RLE/LRO/RLO/PDF/
   LRI/RLI/FSI/PDI`) are rejected, so pre-shaped or visual-order text can
   never enter the pipeline.
2. **Shaping exactly once** — `arabic_reshaper.reshape` and
   `bidi.algorithm.get_display` are combined only inside `shape()`. The final
   display strings are produced once per line in the layout pass and cached
   on the block (`display_lines`); the render pass draws the cached strings
   verbatim and never reshapes. Intermediate measurement/wrapping passes are
   direction-agnostic (they shape candidates only transiently to obtain
   metrics and never store them).
3. **No mirroring** — no canvas/coordinate flip or `ImageOps.mirror` exists;
   directional work happens solely through Pillow text anchors
   (`"ra"`, `"ma"`, `"la"`).

The pytest suite (`tests/`) asserts these properties directly, e.g. that the
render pass never re-applies `get_display` to already-final display lines and
that a double-shaped source is rejected by `validate_source`.

## Public API

```python
from nima_persianguard import NimaPersianGuard, build_scene

guard = build_scene(3000, 2000)      # full default infographic
image = guard.render()               # validates + renders (single pass)
guard.update_text("title", "...")    # any change marks the scene dirty
image = guard.render()               # full re-validation + re-render
```

Other entry points:

- `NimaPersianGuard(width, height, font_path)` — empty canvas engine;
  `add_text`, `update_text`, `set_font_size`, `resize_canvas`, `validate`,
  `render`, `save`.
- `nima_persianguard.validation.validate_source(text)` — logical-Unicode gate.
- `nima_persianguard.textops.shape(text)` — the single shaping point
  (`get_display(reshape(text))`).

## CLI

```
python -m nima_persianguard --width 3000 --height 2000 -o out.png
```

Running the module rebuilds the default infographic, performs the mandatory
resize/re-render invalidation check (2700×1800 → 3000×2000), exercises the
font-size / text-update hooks and writes an optimized PNG.

## Dependencies

- Required: `Pillow`
- Optional extras (recommended, used by the original renderer when
  available): `arabic-reshaper`, `python-bidi`

```
pip install Pillow
pip install arabic-reshaper python-bidi   # optional
```

Font: the original scripts use `/usr/share/fonts/truetype/Vazir.ttf`
(`Vazir.ttf`); pass an alternative path via `NimaPersianGuard(font_path=...)`
or `--font`.

## Example

`examples/recreate_infographic.py` recreates the original infographic with
the packaged API:

```
python examples/recreate_infographic.py -o persian_infographic.png
```

## Tests

```
pytest tests/
```

Tests focus on the single-pass RTL contract: `shape` is the only shaping
point, final display lines are cached and never reshaped again, and the
render pass consumes cached strings.

## Zeno v2 submission note

For the Zeno v2 submission of *Nima Persiangard*:

1. **What to submit**
   - the full source archive `nima_persianguard_package.zip` (this package:
     `nima_persianguard/`, `examples/`, `tests/`, `pyproject.toml`,
     `README.md`, `LICENSE`), and
   - the final rendered PNG produced by the example/CLI
     (`persian_infographic_persianguard_v2.png`, 3000×2000, optimized).
2. **How to describe the single-pass RTL guarantee** (use this wording or a
   close paraphrase):
   > "Every Persian string is supplied as logical Unicode and is validated at
   > the boundary (`validate_source` rejects presentation forms and bidi
   > control characters). Shaping (`arabic_reshaper.reshape`) followed by bidi
   > reordering (`bidi.algorithm.get_display`) is applied exactly once, only
   > in the final render pass, on cached per-line display strings. All
   > intermediate measurement and layout passes are direction-agnostic and
   > never produce or mutate display strings. There is no canvas flip, no
   > mirror and no second shaping, so text cannot be reversed or
   > double-shaped; this is enforced by automated contract tests in
   > `tests/test_contract.py`."
3. Reference `docs/shaping_bidi_review_report.txt` (verbatim audit report)
   and `docs/current_texts.txt` (verbatim user Persian text) as supporting
   evidence.

## License

MIT — see `LICENSE`.

© copyright 2026 nima esmaeili
