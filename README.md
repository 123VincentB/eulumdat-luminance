# eulumdat-luminance

[![PyPI version](https://img.shields.io/pypi/v/eulumdat-luminance.svg)](https://pypi.org/project/eulumdat-luminance/)
[![Python](https://img.shields.io/pypi/pyversions/eulumdat-luminance.svg)](https://pypi.org/project/eulumdat-luminance/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/1184236889.svg)](https://doi.org/10.5281/zenodo.19223062)

Luminance table generation from EULUMDAT (.ldt) photometric files — extension to [eulumdat-py](https://pypi.org/project/eulumdat-py/).

## Features

- Luminance table (cd/m²) computed from intensity distribution and luminous area geometry
- UGR grid (C: 0°–345° in 15° steps, γ: 65°–85° in 5° steps) with automatic bilinear interpolation when the native LDT resolution does not match
- Full native grid mode for detailed photometric analysis
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

plot = LuminancePlot(result)
plot.polar("polar.svg")
plot.polar("polar.png")

# Print-ready: 8 cm wide at 300 dpi
plot.polar("polar_print.png", style=PolarStyle.for_print(width_cm=8, dpi=300))
```

## Running the tests

```bash
# All tests (numerical validation + diagram generation)
pytest

# Numerical tests only (fast, ~10 s)
pytest tests/test_calculator.py

# Visual diagram generation only
pytest tests/test_diagrams.py

# Verbose with print output
pytest -v -s

# Filter by sample
pytest -k sample_04

# Filter by test type
pytest -k "svg"                  # SVG generation only
pytest -k "png"                  # PNG generation only
pytest -k "for_print"            # print/PDF sizing tests
pytest -k "Relux"                # Relux numerical validation (30 tests)
pytest -k "not Smoke"            # exclude smoke tests

# Coverage
pytest --cov=eulumdat_luminance tests/test_calculator.py
```

## License

MIT
