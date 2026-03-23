# Basic usage

This example covers the standard workflow:
loading an EULUMDAT file, computing the luminance table, inspecting the results,
exporting to CSV and JSON, and generating diagrams.

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

| `full`            | Grid                                                       | Shape    | Use case                          |
| ----------------- | ---------------------------------------------------------- | -------- | --------------------------------- |
| `False` (default) | UGR grid — C: 0°–345° in 15° steps, γ: 65°–85° in 5° steps | (24, 5)  | Glare evaluation, UGR calculation |
| `True`            | Native LDT grid — all angles available in the file         | (mc, ng) | Full photometric analysis         |

When the native grid does not match the UGR grid exactly, bilinear interpolation
is applied automatically (via `scipy.interpolate.RegularGridInterpolator`).

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

## 5. Generate diagrams

```python
from eulumdat_luminance import LuminancePlot

plot = LuminancePlot(result)
```

### Söllner diagram

The Söllner diagram is the standard representation for glare evaluation:
- Y axis: γ angle (45°–85°)
- X axis: luminance in cd/m², logarithmic scale
- One curve per C-plane

```python
# Default: C0, C90, C180, C270
plot.soellner("data/output/soellner.svg")
plot.soellner("data/output/soellner.png")
plot.soellner("data/output/soellner.jpg")

# Custom C-planes
plot.soellner("data/output/soellner_c0_c180.svg", c_planes=[0.0, 180.0])

# Custom γ range
plot.soellner("data/output/soellner_wide.svg", g_min=45.0, g_max=85.0)
```

### Polar luminance diagram

The polar diagram shows luminance as a radial value across all C-planes (0°–360°),
with one curve per γ angle.

```python
# Default: all γ angles in the result
plot.polar("data/output/polar.svg")
plot.polar("data/output/polar.png")

# Custom γ selection
plot.polar("data/output/polar_65_85.svg", g_angles=[65.0, 85.0])
```

### Export formats

| Extension        | Format      | Notes                           |
| ---------------- | ----------- | ------------------------------- |
| `.svg`           | SVG vector  | Recommended for reports and web |
| `.png`           | PNG raster  | Default scale ×2 (retina)       |
| `.jpg` / `.jpeg` | JPEG raster | Quality 92, via Pillow          |

---

## 6. Full workflow — minimal script

```python
from pathlib import Path
from pyldt import LdtReader
from eulumdat_luminance import LuminanceCalculator, LuminancePlot

# Paths
ldt_file = Path("data/input/sample_04.ldt")
output_dir = Path("data/output")
output_dir.mkdir(parents=True, exist_ok=True)

# Load
ldt = LdtReader.read(str(ldt_file))

# Compute (UGR grid)
result = LuminanceCalculator.compute(ldt, full=False)
print(f"{result.luminaire_name} — max {result.maximum:.0f} cd/m²")

# Export data
result.to_csv(output_dir / "luminance.csv")
result.to_json(output_dir / "luminance.json")

# Export diagrams
plot = LuminancePlot(result)
plot.soellner(output_dir / "soellner.svg")
plot.soellner(output_dir / "soellner.png")
plot.polar(output_dir / "polar.svg")
plot.polar(output_dir / "polar.png")
```

---

## See also

- [eulumdat-py](https://pypi.org/project/eulumdat-py/) — EULUMDAT parser and writer
- [eulumdat-plot](https://pypi.org/project/eulumdat-plot/) — polar intensity diagrams
- [eulumdat-ugr](https://pypi.org/project/eulumdat-ugr/) — UGR glare calculation *(coming soon)*
