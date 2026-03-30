# eulumdat-luminance

[![PyPI version](https://img.shields.io/pypi/v/eulumdat-luminance.svg)](https://pypi.org/project/eulumdat-luminance/)
[![Python](https://img.shields.io/pypi/pyversions/eulumdat-luminance.svg)](https://pypi.org/project/eulumdat-luminance/)
[![License: MIT](https://img.shields.io/github/license/123VincentB/eulumdat-luminance)](https://github.com/123VincentB/eulumdat-luminance/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/1184236889.svg)](https://doi.org/10.5281/zenodo.19223062)

Luminance table generation from EULUMDAT (.ldt) photometric files — extension to [eulumdat-py](https://pypi.org/project/eulumdat-py/).

## Features

- Luminance table (cd/m²) computed from intensity distribution and luminous area geometry
- UGR grid (C: 0°–345° in 15° steps, γ: 65°–85° in 5° steps) with automatic bilinear interpolation when the native LDT resolution does not match
- Full native grid mode for detailed photometric analysis
- `result.at(c_deg, g_deg)` — bilinear interpolation at arbitrary (C, γ) angles
- `result.projected_area(c_deg, g_deg)` — projected luminous area (m²) at arbitrary angles, required by `eulumdat-ugr` for solid-angle computation
- Polar luminance diagram (SVG + PNG/JPG): all 24 C-planes visible simultaneously, one curve per γ angle, blue gradient palette, optional threshold circle
- Print-ready output via `PolarStyle.for_print(width_cm, dpi)` — exact physical dimensions for PDF/Word documents
- CSV and JSON export

## Installation

```bash
pip install eulumdat-luminance
```

## Dependencies

- [eulumdat-py](https://pypi.org/project/eulumdat-py/) — EULUMDAT parser
- numpy, scipy
- vl-convert-python — SVG rasterisation
- Pillow — JPG conversion

## Quick start

```python
from pyldt import LdtReader
from eulumdat_luminance import LuminanceCalculator, LuminancePlot, PolarStyle

ldt    = LdtReader.read("luminaire.ldt")
result = LuminanceCalculator.compute(ldt)

print(f"{result.luminaire_name} — {result.maximum:.0f} cd/m²")

# Interpolate luminance at arbitrary (C, γ)
lum  = result.at(c_deg=12.0, g_deg=67.0)           # float, cd/m²

# Projected luminous area at arbitrary (C, γ) — used by eulumdat-ugr
area = result.projected_area(c_deg=0.0, g_deg=65.0) # float, m²

plot = LuminancePlot(result)
plot.polar("polar.svg")
plot.polar("polar.png")

# Print-ready: 10 cm at 150 dpi, fonts equivalent to Arial 9pt
plot.polar("polar_report.png", style=PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11))
```

## Example output

![Polar luminance diagram — sample_04, 10 cm at 150 dpi](https://raw.githubusercontent.com/123VincentB/eulumdat-luminance/main/examples/polar_sample04_word.png)

*Sample 04 — linear luminaire 1480 × 63 mm, 12 334 lm — `PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11)`*

## Running the tests

```bash
# All tests (numerical validation + diagram generation)
pytest

# Numerical tests only (fast)
pytest tests/test_calculator.py

# Diagram generation only
pytest tests/test_polar_diagram.py

# Verbose with print output
pytest -v -s

# Filter by sample
pytest -k sample_04

# Filter by test type
pytest -k "svg"                  # SVG generation only
pytest -k "png"                  # PNG generation only
pytest -k "for_print"            # print sizing test (8 cm / 300 dpi)
pytest -k "word"                 # Word/PDF report test (10 cm / 150 dpi)
pytest -k "Relux"                # Relux numerical validation (30 tests)
pytest -k "not Smoke"            # exclude smoke tests

# Coverage
pytest --cov=eulumdat_luminance tests/test_calculator.py
```

## License

MIT
