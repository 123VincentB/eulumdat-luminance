# Basic usage

This example covers the standard workflow:
loading an EULUMDAT file, computing the luminance table, inspecting the results,
exporting to CSV and JSON, and generating a polar luminance diagram.

---

## 1. Load an EULUMDAT file

`eulumdat-luminance` reads `.ldt` files through
[eulumdat-py](https://pypi.org/project/eulumdat-py/).
The installed module name is `pyldt`.

```python
from pyldt import LdtReader

ldt = LdtReader.read("data/input/sample_04.ldt")
```

`LdtReader.read()` handles all symmetry types (ISYM 0–4) and always returns a
fully expanded intensity matrix covering C 0°–360° and γ 0°–180°.

---

## 2. Compute the luminance table

```python
from eulumdat_luminance import LuminanceCalculator

result = LuminanceCalculator.compute(ldt, full=False)
```

The `full` parameter controls the angle grid used for the output:

| `full`            | Grid                                                         | Shape    | Use case                          |
| ----------------- | ------------------------------------------------------------ | -------- | --------------------------------- |
| `False` (default) | UGR grid — C: 0°–345° in 15° steps, γ: 65°–85° in 5° steps | (24, 5)  | Glare evaluation, UGR calculation |
| `True`            | Native LDT grid — all angles available in the file           | (mc, ng) | Full photometric analysis         |

When the native LDT resolution does not match the UGR grid exactly (e.g. 2.5°
step files), bilinear interpolation is applied automatically via
`scipy.interpolate.RegularGridInterpolator`.

---

## 3. Inspect the result

```python
print(result.luminaire_name)   # str — from the LDT header
print(result.maximum)          # float — maximum luminance in cd/m²
print(result.full)             # bool — True if native grid, False if UGR grid
print(result.table.shape)      # (n_c, n_g) — rows = C-planes, columns = γ angles
print(result.c_axis)           # np.ndarray — C-plane angles in degrees
print(result.g_axis)           # np.ndarray — γ angles in degrees
```

Example output for `sample_04.ldt` (linear luminaire 1480 × 63 mm, 12334 lm):

```
sample_04
5603.4
False
(24, 5)
[  0.  15.  30.  45.  60.  75.  90. 105. 120. 135. 150. 165. 180. 195.
 210. 225. 240. 255. 270. 285. 300. 315. 330. 345.]
[65. 70. 75. 80. 85.]
```

Access individual values by index:

```python
import numpy as np

# Luminance at C=0°, γ=65°
idx_c = int(np.searchsorted(result.c_axis, 0.0))
idx_g = int(np.searchsorted(result.g_axis, 65.0))
print(result.table[idx_c, idx_g])   # → 5603 cd/m²

# Luminance at C=0°, γ=85°
idx_g85 = int(np.searchsorted(result.g_axis, 85.0))
print(result.table[idx_c, idx_g85]) # → 463 cd/m²
```

---

## 4. Export to CSV and JSON

```python
result.to_csv("data/output/luminance.csv")
result.to_json("data/output/luminance.json")
```

### CSV format

Rows = C-plane angles, columns = γ angles. The first row is the header.

```
C \ γ (°),65.0,70.0,75.0,80.0,85.0
0.0,5603.4,3821.7,2109.8,983.2,463.1
15.0,5598.1,3817.4,2107.2,982.0,462.5
...
```

### JSON format

```json
{
  "luminaire_name": "sample_04",
  "full": false,
  "maximum_cd_m2": 5603.4,
  "c_axis_deg": [0.0, 15.0, 30.0, "..."],
  "g_axis_deg": [65.0, 70.0, 75.0, 80.0, 85.0],
  "table_cd_m2": [
    [5603.4, 3821.7, 2109.8, 983.2, 463.1],
    "..."
  ]
}
```

---

## 5. Generate the polar luminance diagram

```python
from eulumdat_luminance import LuminancePlot

plot = LuminancePlot(result)
```

### SVG output

SVG is the recommended format for embedding in reports or web pages.
It is resolution-independent and can be scaled without quality loss.

```python
plot.polar("data/output/polar.svg")
```

### PNG output

PNG is rasterised from the SVG via `vl-convert-python`.
The default style uses `scale=2.0` (retina): the SVG canvas is 665 × 615 px
and the output PNG is approximately 1330 × 1230 px.

```python
plot.polar("data/output/polar.png")
```

### JPG output

```python
plot.polar("data/output/polar.jpg")   # quality 92, via Pillow
```

### Selecting γ angles

By default all γ angles available in the result are drawn (65°, 70°, 75°, 80°, 85°
for a UGR grid).  Pass `g_angles` to restrict the selection:

```python
plot.polar("data/output/polar_65_85.svg", g_angles=[65.0, 85.0])
```

---

## 6. Full workflow — minimal script

```python
from pathlib import Path
from pyldt import LdtReader
from eulumdat_luminance import LuminanceCalculator, LuminancePlot

ldt_file   = Path("data/input/sample_04.ldt")
output_dir = Path("data/output")
output_dir.mkdir(parents=True, exist_ok=True)

ldt    = LdtReader.read(str(ldt_file))
result = LuminanceCalculator.compute(ldt, full=False)
print(f"{result.luminaire_name} — max {result.maximum:.0f} cd/m²")

result.to_csv(output_dir / "luminance.csv")
result.to_json(output_dir / "luminance.json")

plot = LuminancePlot(result)
plot.polar(output_dir / "polar.svg")
plot.polar(output_dir / "polar.png")
```

---

## See also

- [eulumdat-py](https://pypi.org/project/eulumdat-py/) — EULUMDAT parser and writer
- [eulumdat-plot](https://pypi.org/project/eulumdat-plot/) — polar intensity diagrams
- [eulumdat-ugr](https://pypi.org/project/eulumdat-ugr/) — UGR glare calculation *(coming soon)*
- `02_resize_and_export.md` — print sizing, font scaling, custom style
