# Print sizing, font scaling, and custom style

This document covers everything related to output sizing and visual customisation
of the polar luminance diagram.

---

## Why `for_print()` instead of pixel sizes

The default `PolarStyle()` uses a fixed SVG canvas of ~665 × 615 px with
`scale=2.0`, producing a PNG of approximately 1330 × 1230 px.  This is fine
for screen use but does not map to a predictable physical size in a PDF or
Word document.

`PolarStyle.for_print(width_cm, dpi)` solves this by working backwards from a
physical target size:

```
width_px  = width_cm / 2.54 * dpi    # target width in pixels
k         = width_px / 665           # scale factor vs. reference canvas
diagram_r = round(250 * k)           # polar circle radius
scale     = 1.0                      # always — no retina doubling
```

With `scale=1.0`, one SVG user unit equals one pixel, so the PNG width in pixels
equals `canvas_width` in SVG units, which equals `width_px`.

---

## Basic print sizing

```python
from eulumdat_luminance import LuminancePlot, PolarStyle

plot = LuminancePlot(result)

# 8 cm wide at 300 dpi — standard datasheet quality
style = PolarStyle.for_print(width_cm=8, dpi=300)
plot.polar("polar_8cm.png", style=style)

# 12 cm wide at 300 dpi — larger report figure
plot.polar("polar_12cm.png", style=PolarStyle.for_print(width_cm=12, dpi=300))

# 12 cm wide at 150 dpi — screen / web report (smaller file)
plot.polar("polar_12cm_web.png", style=PolarStyle.for_print(width_cm=12, dpi=150))
```

Reference output sizes at 300 dpi:

| `width_cm` | PNG width | `diagram_r` |
|------------|-----------|-------------|
| 6          | ~709 px   | 266         |
| 8          | ~945 px   | 355         |
| 12         | ~1417 px  | 533         |
| 16         | ~1890 px  | 710         |

---

## Font scaling for readable print output

At 300 dpi, the default font sizes are too small when the diagram is imported
into Word or a PDF viewer.  The `font_scale` parameter multiplies all font sizes
and the text reservation areas (title, legend, angle labels) proportionally,
without changing the circle radius or stroke widths.

```python
# font_scale=2.6 produces fonts equivalent to Arial 10pt at 300 dpi
# Calculation: 10pt × 300dpi / 72 / base_font_px ≈ 2.6
style = PolarStyle.for_print(width_cm=8, dpi=300, font_scale=2.6)
plot.polar("polar_readable.png", style=style)
```

> **Note:** with `font_scale > 1`, the canvas becomes wider than `width_cm`
> because the text areas grow. The circle radius and diagram content are
> unchanged — only the surrounding whitespace for labels and title expands.

Suggested values:

| Use case                         | `font_scale` |
|----------------------------------|--------------|
| Default (screen, no scaling)     | 1.0          |
| Word/PDF at 300 dpi, ~Arial 8pt  | 2.0          |
| Word/PDF at 300 dpi, ~Arial 10pt | 2.6          |
| Word/PDF at 150 dpi, ~Arial 10pt | 1.3          |

---

## Disabling or changing the threshold circle

The red dashed threshold circle (default 3000 cd/m²) is controlled by the
`threshold` parameter.

```python
# Disable
style = PolarStyle.for_print(width_cm=8, threshold=None)

# Custom threshold value
style = PolarStyle.for_print(width_cm=8, threshold=1000.0)

# Custom color and dash pattern
style = PolarStyle.for_print(
    width_cm=8,
    threshold=3000.0,
    threshold_color="#ff6600",
    threshold_dash="4,2",
)
```

The circle is only drawn when `threshold <= r_max` (the rounded scale maximum).
If the luminaire maximum is below the threshold, the circle is silently omitted.

---

## Custom gamma colour palette

The default palette maps γ angles to a blue gradient (65° = dark, 85° = light).
Any mapping of `float -> hex color` is accepted.

```python
style = PolarStyle.for_print(
    width_cm=8,
    g_colors={
        65.0: "#1a1a1a",   # near-black
        70.0: "#444444",
        75.0: "#777777",
        80.0: "#aaaaaa",
        85.0: "#dddddd",   # light grey
    }
)
```

---

## Fine-tuning layer positions

Each SVG layer has a default position computed from the canvas geometry.
The `*_offset_x/y` parameters shift a layer from its default position without
affecting any other layer.

```python
style = PolarStyle.for_print(
    width_cm=8,
    dpi=300,
    font_scale=2.6,
    title_offset_y=5,     # move title 5 px down
    legend_offset_x=-10,  # move legend 10 px closer to the circle
    legend_offset_y=20,   # move legend 20 px down
)
```

Available offsets: `diagram_offset_x/y`, `title_offset_x/y`, `legend_offset_x/y`.

---

## Fully custom style

For complete control, construct `PolarStyle` directly.
`for_print()` is a convenience factory — it sets sensible defaults, but every
parameter it sets can also be passed explicitly to `PolarStyle()`.

```python
style = PolarStyle(
    diagram_r=400,
    padding=15,
    title_area_height=90,
    legend_area_width=140,
    bottom_area_height=50,
    left_area_width=50,
    title_font_size=36,
    subtitle_font_size=28,
    angle_label_font_size=24,
    ring_label_font_size=20,
    legend_title_font_size=24,
    legend_label_font_size=20,
    legend_bar_width=22,
    legend_bar_height=280,
    curve_stroke_width=2.5,
    grid_stroke_width=0.8,
    spoke_stroke_width=0.6,
    threshold=3000.0,
    scale=1.0,
)
plot.polar("polar_custom.png", style=style)
```

---

## Overriding scale at export time

The `scale` parameter can also be passed directly to `plot.polar()`, overriding
whatever is stored in the style object.

```python
# Generate a 2× retina PNG from a print style
style = PolarStyle.for_print(width_cm=8)   # scale=1.0
plot.polar("polar_retina.png", style=style, scale=2.0)

# Generate a low-res preview from the default style
plot.polar("polar_preview.png", scale=0.5)
```

---

## Batch export — multiple sizes from one result

```python
from pathlib import Path
from pyldt import LdtReader
from eulumdat_luminance import LuminanceCalculator, LuminancePlot, PolarStyle

ldt    = LdtReader.read("luminaire.ldt")
result = LuminanceCalculator.compute(ldt)
plot   = LuminancePlot(result)
out    = Path("output")
out.mkdir(exist_ok=True)

# SVG (resolution-independent, always useful to keep)
plot.polar(out / "polar.svg")

# Standard screen PNG (default style, retina)
plot.polar(out / "polar_screen.png")

# Print quality for reports
plot.polar(out / "polar_8cm_300dpi.png",
           style=PolarStyle.for_print(width_cm=8, dpi=300, font_scale=2.6))

# Compact thumbnail
plot.polar(out / "polar_thumb.png",
           style=PolarStyle.for_print(width_cm=4, dpi=150))
```

---

## See also

- `01_basic_usage.md` — loading, computing, and basic export
- [eulumdat-plot](https://pypi.org/project/eulumdat-plot/) — polar intensity diagrams (cd)
- [eulumdat-ugr](https://pypi.org/project/eulumdat-ugr/) — UGR glare calculation *(coming soon)*
