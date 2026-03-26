"""
Polar luminance diagram — smoke tests for all 10 LDT samples.

All tests use the project reference print style:
    PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11)
    (Arial 9pt equivalent at 150 dpi)

SVG tests verify that the file is created and non-empty.
PNG tests additionally verify that the output width matches STYLE.canvas_width.

font_scale derivation
---------------------
    k = (10 / 2.54 * 150) / 665  ~= 0.889
    target px for a base label (10 SVG units at k=1):
        9pt * 150 dpi / 72 = 18.75 px
    font_scale = (18.75 / 10) / k  ~= 2.11

Output
------
    data/output/diagrams/<sample_XX>/polar.svg
    data/output/diagrams/<sample_XX>/polar.png

Usage
-----
    pytest tests/test_polar_diagram.py -v -s
    pytest tests/test_polar_diagram.py -v -s -k svg
    pytest tests/test_polar_diagram.py -v -s -k png
    pytest tests/test_polar_diagram.py -v -s -k sample_04
"""

from pathlib import Path

import pytest
from PIL import Image

from pyldt import LdtReader
from eulumdat_luminance import LuminanceCalculator, LuminancePlot, PolarStyle

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
THIS_DIR   = Path(__file__).parent
ROOT_DIR   = THIS_DIR.parent
INPUT_DIR  = ROOT_DIR / "data" / "input"
OUTPUT_DIR = ROOT_DIR / "data" / "output" / "diagrams"

SAMPLES = [f"sample_{i:02d}" for i in range(1, 11)]

# ---------------------------------------------------------------------------
# Reference print style (shared by all tests)
# ---------------------------------------------------------------------------
_k = (10 / 2.54 * 150) / 665          # ~= 0.889
_FONT_SCALE = round((18.75 / 10) / _k, 2)  # ~= 2.11

STYLE = PolarStyle.for_print(width_cm=10, dpi=150, font_scale=_FONT_SCALE)


def _out(sample: str) -> Path:
    d = OUTPUT_DIR / sample
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# SVG smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sample_name", SAMPLES)
def test_polar_svg(sample_name: str) -> None:
    """Generate the polar diagram as SVG for each sample."""
    ldt_path = INPUT_DIR / f"{sample_name}.ldt"
    if not ldt_path.exists():
        pytest.skip(f"{ldt_path} not found")
    ldt    = LdtReader.read(str(ldt_path))
    result = LuminanceCalculator.compute(ldt, full=False)
    out    = _out(sample_name) / "polar.svg"
    LuminancePlot(result).polar(str(out), style=STYLE)
    assert out.exists() and out.stat().st_size > 0
    print(f"\n  [OK] {sample_name} SVG -> {out}")


# ---------------------------------------------------------------------------
# PNG smoke tests + canvas width validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sample_name", SAMPLES)
def test_polar_png(sample_name: str) -> None:
    """
    Generate the polar diagram as PNG for each sample.
    Verifies that the output width matches STYLE.canvas_width.
    """
    ldt_path = INPUT_DIR / f"{sample_name}.ldt"
    if not ldt_path.exists():
        pytest.skip(f"{ldt_path} not found")
    ldt    = LdtReader.read(str(ldt_path))
    result = LuminanceCalculator.compute(ldt, full=False)
    out    = _out(sample_name) / "polar.png"
    LuminancePlot(result).polar(str(out), style=STYLE)
    assert out.exists() and out.stat().st_size > 0
    img = Image.open(out)
    w, h = img.size
    assert w == STYLE.canvas_width, (
        f"{sample_name}: expected {STYLE.canvas_width}px, got {w}px"
    )
    print(f"\n  [OK] {sample_name} PNG -> {w}x{h}px -> {out}")
