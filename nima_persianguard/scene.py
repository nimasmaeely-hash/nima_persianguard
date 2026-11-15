"""Builds the 3000x2000 "Persian Layered Realities" infographic scene."""

from __future__ import annotations

from typing import Optional

from .engine import NimaPersianGuard

SCENE_WIDTH = 3000
SCENE_HEIGHT = 2000

BLUE = (96, 165, 250)
AMBER = (245, 185, 90)
VIOLET = (167, 139, 250)
MUTED = (148, 163, 184)
WHITE = (236, 240, 248)
GREEN = (110, 231, 183)
PINK = (244, 114, 182)

LEFT_ITEMS = [
    "ماتریس پایه و شبیه‌سازی حسی",
    "ماتریس شناختی و هنجارهای ساختگی",
    "ماتریس هوش مصنوعی و آگاهی فراگیر",
    "ماتریس متا و چرخه‌های بازتولید",
]
RIGHT_ITEMS = [
    "فیزیک کلاسیک و تجربی",
    "کوانتومی و عدم‌قطعیت",
    "نسبیتی و فضازمان خمیده",
    "لایه‌های فراکیهانی و چندجهانی",
]
CENTERS = [
    ("ناظر (O = I, P, B)", "موقعیت ناظر در ساخت تجربه"),
    ("فرض", "نقطه آغاز شناخت"),
    ("افق انسجام", "مرز گذار میان لایه‌ها"),
    ("تولید گلیچ", "اختلال و ناسازگاری"),
]


def build_scene(width: int = SCENE_WIDTH, height: int = SCENE_HEIGHT,
                font_path: Optional[str] = None) -> NimaPersianGuard:
    """Create the full default infographic scene (all texts logical Persian)."""
    g = NimaPersianGuard(width, height, font_path=font_path,
                         background=(10, 12, 20))
    sx = width / SCENE_WIDTH
    sy = height / SCENE_HEIGHT

    def X(v): return v * sx
    def Y(v): return v * sy
    def S(v): return v * min(sx, sy)

    # header
    g.add_text("title", "نظریه جامع جهان‌های لایه‌مند",
               X(1500), Y(110), box=(X(500), Y(80), X(2000), S(80)),
               font_size=S(64), color=WHITE, align="center")
    g.add_text("subtitle", "نویسنده و نظریه‌پرداز: نیما اسماعیلی",
               X(1500), Y(210), box=(X(700), Y(190), X(1600), S(50)),
               font_size=S(36), color=MUTED, align="center")
    g.add_text("chapter_label", "فصل ۱  •  جهان‌های لایه‌مند",
               X(1500), Y(285), box=(X(900), Y(265), X(1200), S(45)),
               font_size=S(28), color=GREEN, align="center")

    # column headings (exact 4-layer Matrix / Non-Matrix texts)
    g.add_text("left_heading", "واقعیت‌های لایه‌مند غیرواقعی",
               X(1040), Y(393), box=(X(170), Y(370), X(870), S(60)),
               font_size=S(45), color=BLUE, align="right")
    g.add_text("left_kind", "(ماتریکسی / ایزومورفیک)",
               X(1040), Y(468), box=(X(170), Y(445), X(870), S(45)),
               font_size=S(30), color=MUTED, align="right")
    g.add_text("right_heading", "واقعیت‌های لایه‌مند واقعی",
               X(2890), Y(393), box=(X(2020), Y(370), X(870), S(60)),
               font_size=S(45), color=AMBER, align="right")
    g.add_text("right_kind", "(غیر ماتریکسی / آنیزومورفیک)",
               X(2890), Y(468), box=(X(2020), Y(445), X(870), S(45)),
               font_size=S(30), color=MUTED, align="right")
    g.add_text("center_heading", "مدل گذار شناختی",
               X(1500), Y(416), box=(X(1205), Y(390), X(590), S(55)),
               font_size=S(42), color=VIOLET, align="center")

    # layers
    for i, text in enumerate(LEFT_ITEMS):
        g.add_text("L_layer_%d" % i, text,
                   X(1000), Y(590) + i * Y(170),
                   box=(X(330), Y(570) + i * Y(170), X(670), S(80)),
                   font_size=S(34), color=WHITE, align="right")
    for i, text in enumerate(RIGHT_ITEMS):
        g.add_text("R_layer_%d" % i, text,
                   X(2850), Y(590) + i * Y(170),
                   box=(X(2180), Y(570) + i * Y(170), X(670), S(80)),
                   font_size=S(34), color=WHITE, align="right")
    for i, (head, detail) in enumerate(CENTERS):
        g.add_text("center_%d_head" % i, head,
                   X(1500), Y(600) + i * Y(210),
                   box=(X(1260), Y(575) + i * Y(210), X(480), S(55)),
                   font_size=S(34), color=VIOLET, align="center")
        g.add_text("center_%d_detail" % i, detail,
                   X(1500), Y(665) + i * Y(210),
                   box=(X(1260), Y(640) + i * Y(210), X(480), S(45)),
                   font_size=S(26), color=MUTED, align="center")

    # footer
    g.add_text("footer_equation", "علم + آگاهی = ادراک واقعیت گسترده‌تر",
               X(1500), Y(1700), box=(X(800), Y(1680), X(1400), S(60)),
               font_size=S(40), color=PINK, align="center")
    g.add_text("footer_quote",
               "درک واقعیت، فراتر از آن چیزی است که می‌بینیم... (نیما اسماعیلی)",
               X(1500), Y(1800), box=(X(500), Y(1780), X(2000), S(50)),
               font_size=S(30), color=MUTED, align="center")
    g.add_text("footer_book", "این کتاب یکی از کتاب‌های سه‌گانهٔ «همه و هیچ» است.",
               X(1500), Y(1890), box=(X(700), Y(1870), X(1600), S(50)),
               font_size=S(28), color=MUTED, align="center")
    return g
