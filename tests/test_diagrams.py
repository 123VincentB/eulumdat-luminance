"""
Génération des diagrammes polaires pour validation visuelle.

Usage :
    pytest tests/test_diagrams.py -v -s
    pytest tests/test_diagrams.py -v -s -k sample_04
    pytest tests/test_diagrams.py -v -s -k "svg"
    pytest tests/test_diagrams.py -v -s -k "for_print"

Les fichiers sont générés dans :
    data/output/diagrams/<sample_XX>/polar.svg / .png

Ce script ne fait PAS de vérification automatique du contenu visuel.
Il échoue uniquement si la génération lève une exception ou si le
fichier n'est pas créé.
"""

import pytest
from pathlib import Path

from pyldt import LdtReader
from eulumdat_luminance import LuminanceCalculator, LuminancePlot, PolarStyle

# ---------------------------------------------------------------------------
# Chemins — toujours relatifs à ce fichier, indépendant du CWD
# ---------------------------------------------------------------------------
THIS_DIR   = Path(__file__).parent
ROOT_DIR   = THIS_DIR.parent
INPUT_DIR  = ROOT_DIR / "data" / "input"
OUTPUT_DIR = ROOT_DIR / "data" / "output" / "diagrams"

SAMPLES = [f"sample_{i:02d}" for i in range(1, 11)]


def get_output_dir(sample_name: str) -> Path:
    d = OUTPUT_DIR / sample_name
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Tests paramétrés — style par défaut
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("sample_name", SAMPLES)
def test_polar_svg(sample_name: str) -> None:
    """Génère le diagramme polaire en SVG pour chaque sample."""
    ldt_path = INPUT_DIR / f"{sample_name}.ldt"
    if not ldt_path.exists():
        pytest.skip(f"{ldt_path} introuvable")

    ldt    = LdtReader.read(str(ldt_path))
    result = LuminanceCalculator.compute(ldt, full=False)
    plot   = LuminancePlot(result)

    out = get_output_dir(sample_name) / "polar.svg"
    plot.polar(str(out))

    assert out.exists(), f"Fichier non créé : {out}"
    assert out.stat().st_size > 0, f"Fichier vide : {out}"
    print(f"\n  [OK] {sample_name} — Polaire SVG → {out}")


@pytest.mark.parametrize("sample_name", SAMPLES)
def test_polar_png(sample_name: str) -> None:
    """Génère le diagramme polaire en PNG pour chaque sample."""
    ldt_path = INPUT_DIR / f"{sample_name}.ldt"
    if not ldt_path.exists():
        pytest.skip(f"{ldt_path} introuvable")

    ldt    = LdtReader.read(str(ldt_path))
    result = LuminanceCalculator.compute(ldt, full=False)
    plot   = LuminancePlot(result)

    out = get_output_dir(sample_name) / "polar.png"
    plot.polar(str(out))

    assert out.exists(), f"Fichier non créé : {out}"
    assert out.stat().st_size > 0, f"Fichier vide : {out}"
    print(f"\n  [OK] {sample_name} — Polaire PNG → {out}")


# ---------------------------------------------------------------------------
# Test for_print() — image 8 cm à 300 dpi (sample_04 uniquement)
# for_print() calcule diagram_r depuis width_cm + dpi.
# scale=1.0 toujours : 1 SVG unit = 1 px, pas de doublement retina.
# ---------------------------------------------------------------------------
def test_polar_png_for_print() -> None:
    """
    Vérifie que PolarStyle.for_print(width_cm=8, dpi=300) produit un PNG
    dont la largeur est proche de 8 cm à 300 dpi (soit ~945 px, ±10 px).
    """
    from PIL import Image

    ldt_path = INPUT_DIR / "sample_04.ldt"
    if not ldt_path.exists():
        pytest.skip(f"{ldt_path} introuvable")

    ldt    = LdtReader.read(str(ldt_path))
    result = LuminanceCalculator.compute(ldt, full=False)
    plot   = LuminancePlot(result)

    style = PolarStyle.for_print(width_cm=8, dpi=300)
    assert style.scale == 1.0, f"scale attendu 1.0, obtenu {style.scale}"

    out = get_output_dir("sample_04") / "polar_8cm_300dpi.png"
    plot.polar(str(out), style=style)

    assert out.exists(), f"Fichier non créé : {out}"
    assert out.stat().st_size > 0, f"Fichier vide : {out}"

    img = Image.open(out)
    w, h = img.size
    target_px = round(8 / 2.54 * 300)  # 945 px
    assert abs(w - target_px) <= 10, (
        f"Largeur attendue ~{target_px}px, obtenu {w}px"
    )
    print(f"\n  [OK] sample_04 — for_print(8cm, 300dpi) → {w}x{h}px → {out}")


# ---------------------------------------------------------------------------
# Test for_print() avec font_scale — fonts lisibles à 10pt dans Word/PDF
# ---------------------------------------------------------------------------
def test_polar_png_for_print_font_scale() -> None:
    """
    Vérifie que font_scale=2.6 produit un PNG de même taille que sans font_scale.
    Les dimensions de l'image ne changent pas, seules les fontes sont agrandies.
    """
    from PIL import Image

    ldt_path = INPUT_DIR / "sample_04.ldt"
    if not ldt_path.exists():
        pytest.skip(f"{ldt_path} introuvable")

    ldt    = LdtReader.read(str(ldt_path))
    result = LuminanceCalculator.compute(ldt, full=False)
    plot   = LuminancePlot(result)

    style = PolarStyle.for_print(width_cm=8, dpi=300, font_scale=2.6)
    out = get_output_dir("sample_04") / "polar_8cm_300dpi_fontscale.png"
    plot.polar(str(out), style=style)

    assert out.exists()
    assert out.stat().st_size > 0

    img = Image.open(out)
    w, h = img.size
    target_px = round(8 / 2.54 * 300)  # 945 px
    assert abs(w - target_px) <= 10, (
        f"Largeur attendue ~{target_px}px, obtenu {w}px"
    )
    print(f"\n  [OK] sample_04 — for_print(8cm, 300dpi, font_scale=2.6) → {w}x{h}px → {out}")
