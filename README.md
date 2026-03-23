# eulumdat-luminance

Luminance table generation from EULUMDAT (.ldt) photometric files — extension to [eulumdat-py](https://pypi.org/project/eulumdat-py/).

## Features

- Luminance table (cd/m²) computed from intensity distribution and luminous area geometry
- Full angle grid (all directions available in the LDT file) or UGR grid (C: 0°–355° in 15° steps, γ: 65°–85° in 5° steps) with interpolation
- Söllner diagram (SVG + PNG/JPG export): luminance vs. angle γ on a logarithmic scale, per C-plane
- Polar luminance diagram (SVG + PNG/JPG export): luminance vs. C-angle, one curve per γ angle
- CSV and JSON export

## Installation

```bash
pip install eulumdat-luminance
```

## Dependencies

- [eulumdat-py](https://pypi.org/project/eulumdat-py/) — EULUMDAT parser
- numpy
- scipy
- vl-convert-python
- Pillow

## Usage

```python
from pyldt import LdtReader
from eulumdat_luminance import LuminanceCalculator, LuminancePlot

# Load an EULUMDAT file
ldt = LdtReader.read("path/to/file.ldt")

# Compute luminance table (UGR grid by default)
result = LuminanceCalculator.compute(ldt, full=False)

print(result.maximum)       # Maximum luminance in cd/m²
print(result.table)         # numpy array (C × γ)
print(result.c_axis)        # C-plane angles in degrees
print(result.g_axis)        # γ angles in degrees

# Export
result.to_csv("output/luminance.csv")
result.to_json("output/luminance.json")

# Plot
plot = LuminancePlot(result)
plot.soellner("output/soellner.svg")
plot.soellner("output/soellner.png")
plot.polar("output/polar.svg")
plot.polar("output/polar.png")
```

## License

MIT
