# -*- coding: utf-8 -*-
"""
tests/test_calculator.py
------------------------
Tests for LuminanceCalculator, LuminanceResult, and LuminancePlot.

Test organisation
-----------------
TestLuminanceResult
    Unit tests on LuminanceResult using synthetic data.
    No LDT file required.

TestProjectedArea
    Unit tests on the geometry calculation (_projected_area).
    No LDT file required.  Verifiable by hand.

TestAllSamples
    Parametrised over every *.ldt file found in data/input/.
    Tests structural invariants that must hold for any valid LDT file.
    Tests are skipped individually if the file is missing.

TestSample04
    Spot-checks with expected numerical values for sample_04.ldt.
    (linear luminaire 1480x63 mm, flat, 1 lamp x 12334 lm, ISYM=4)
    Expected values computed by hand and cross-checked against the
    legacy luminance_table.py reference script.

TestLuminancePlotSmoke
    Smoke tests for LuminancePlot: verify that SVG/PNG export runs
    without crashing, using synthetic data.
    Skipped if vl-convert-python is not installed.

Running
-------
    pytest                           # all tests
    pytest -v                        # verbose (shows parametrised names)
    pytest -k sample_04              # only tests involving sample_04
    pytest tests/test_calculator.py  # this file only
"""

import json
from pathlib import Path

import numpy as np
import pytest

from eulumdat_luminance.calculator import LuminanceCalculator
from eulumdat_luminance.result import LuminanceResult

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data" / "input"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_ldt(path: Path):
    """
    Load a Ldt object from a path.

    Uses pyldt.LdtReader (installed package name: eulumdat-py,
    importable module name: pyldt).
    """
    from pyldt import LdtReader  # noqa: PLC0415
    return LdtReader.read(str(path))


def collect_ldt_files() -> list:
    """Return all *.ldt files in data/input/, sorted by name."""
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("*.ldt"))


# All LDT files found at collection time -- used for parametrize
ALL_LDT_FILES = collect_ldt_files()


# ---------------------------------------------------------------------------
# TestLuminanceResult -- unit tests, no LDT file needed
# ---------------------------------------------------------------------------


class TestLuminanceResult:
    """Tests for LuminanceResult using synthetic data."""

    def _make_result(self, full=False):
        c_axis = np.array([0.0, 90.0, 180.0, 270.0])
        g_axis = np.array([65.0, 70.0, 75.0, 80.0, 85.0])
        table = np.array([
            [1000.0, 1200.0, 1400.0, 1600.0, 1800.0],
            [ 900.0, 1100.0, 1300.0, 1500.0, 1700.0],
            [ 950.0, 1150.0, 1350.0, 1550.0, 1750.0],
            [ 850.0, 1050.0, 1250.0, 1450.0, 1650.0],
        ])
        return LuminanceResult(
            table=table, c_axis=c_axis, g_axis=g_axis,
            full=full, luminaire_name="TEST-001",
        )

    def test_maximum(self):
        assert self._make_result().maximum == pytest.approx(1800.0)

    def test_table_shape(self):
        assert self._make_result().table.shape == (4, 5)

    def test_repr_ugr(self):
        r = repr(self._make_result(full=False))
        assert "UGR" in r and "TEST-001" in r

    def test_repr_full(self):
        assert "full" in repr(self._make_result(full=True))

    def test_to_csv(self, tmp_path):
        result = self._make_result()
        out = tmp_path / "test.csv"
        result.to_csv(out)
        content = out.read_text(encoding="utf-8")
        assert "65.0" in content and "85.0" in content
        assert "0.0" in content and "270.0" in content

    def test_to_json(self, tmp_path):
        result = self._make_result()
        out = tmp_path / "test.json"
        result.to_json(out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["luminaire_name"] == "TEST-001"
        assert data["maximum_cd_m2"] == pytest.approx(1800.0)
        assert len(data["c_axis_deg"]) == 4
        assert len(data["g_axis_deg"]) == 5
        assert len(data["table_cd_m2"]) == 4
        assert len(data["table_cd_m2"][0]) == 5

    def test_to_json_roundtrip(self, tmp_path):
        result = self._make_result()
        out = tmp_path / "rt.json"
        result.to_json(out)
        data = json.loads(out.read_text(encoding="utf-8"))
        np.testing.assert_allclose(np.array(data["table_cd_m2"]), result.table, rtol=1e-4)


# ---------------------------------------------------------------------------
# TestProjectedArea -- geometry unit tests, no LDT file needed
# ---------------------------------------------------------------------------


class TestProjectedArea:
    """Unit tests for LuminanceCalculator._projected_area."""

    def test_flat_luminaire_at_nadir(self):
        """At gamma=0 only the bottom area contributes (sin=0)."""
        a = LuminanceCalculator._projected_area(
            np.array([0.0]), np.array([0.0]),
            a_bottom=1.0, length=1.0, width=1.0,
            h_c0=0.0, h_c90=0.0, h_c180=0.0, h_c270=0.0, circular=False,
        )
        assert a[0, 0] == pytest.approx(1.0)

    def test_flat_luminaire_at_90deg(self):
        """At gamma=90 with all heights=0, A_proj must be 0."""
        a = LuminanceCalculator._projected_area(
            np.array([0.0, 90.0]), np.array([90.0]),
            a_bottom=1.0, length=1.0, width=1.0,
            h_c0=0.0, h_c90=0.0, h_c180=0.0, h_c270=0.0, circular=False,
        )
        assert a[0, 0] == pytest.approx(0.0)
        assert a[1, 0] == pytest.approx(0.0)

    def test_rectangular_gamma45(self):
        """600x600 mm flat, gamma=45: A_proj = 0.36 * cos(45)."""
        a = LuminanceCalculator._projected_area(
            np.array([0.0]), np.array([45.0]),
            a_bottom=0.36, length=0.6, width=0.6,
            h_c0=0.0, h_c90=0.0, h_c180=0.0, h_c270=0.0, circular=False,
        )
        assert a[0, 0] == pytest.approx(0.36 * np.cos(np.radians(45.0)), rel=1e-5)

    def test_circular_nadir(self):
        """Circular D=600 mm at gamma=0: A_proj = pi*(0.3)^2."""
        a_bottom = np.pi * 0.3 ** 2
        a = LuminanceCalculator._projected_area(
            np.array([0.0]), np.array([0.0]),
            a_bottom=a_bottom, length=0.6, width=0.0,
            h_c0=0.0, h_c90=0.0, h_c180=0.0, h_c270=0.0, circular=True,
        )
        assert a[0, 0] == pytest.approx(a_bottom, rel=1e-5)

    def test_height_contribution_at_90(self):
        """600x600 mm, h_c0=100 mm, C=0, gamma=90: A_proj = 0.6*0.1 = 0.06 m2."""
        a = LuminanceCalculator._projected_area(
            np.array([0.0]), np.array([90.0]),
            a_bottom=0.36, length=0.6, width=0.6,
            h_c0=0.1, h_c90=0.0, h_c180=0.0, h_c270=0.0, circular=False,
        )
        assert a[0, 0] == pytest.approx(0.06, rel=1e-5)

    def test_symmetry_square_equal_heights(self):
        """Square luminaire with equal heights: A_proj at C=45 == C=135."""
        a = LuminanceCalculator._projected_area(
            np.array([45.0, 135.0]), np.array([75.0]),
            a_bottom=0.36, length=0.6, width=0.6,
            h_c0=0.05, h_c90=0.05, h_c180=0.05, h_c270=0.05, circular=False,
        )
        assert a[0, 0] == pytest.approx(a[1, 0], rel=1e-5)

    def test_output_shape(self):
        """Output shape must be (n_c, n_g)."""
        c = np.arange(0.0, 360.0, 15.0)
        g = np.arange(65.0, 86.0, 5.0)
        a = LuminanceCalculator._projected_area(
            c, g, a_bottom=0.1, length=0.4, width=0.25,
            h_c0=0.0, h_c90=0.0, h_c180=0.0, h_c270=0.0, circular=False,
        )
        assert a.shape == (24, 5)


# ---------------------------------------------------------------------------
# TestAllSamples -- parametrised structural invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ldt_path", ALL_LDT_FILES, ids=lambda p: p.name)
class TestAllSamples:
    """
    Structural invariants that must hold for every valid LDT file.
    Parametrised over all *.ldt files in data/input/.
    """

    def test_ugr_grid_shape(self, ldt_path):
        """UGR grid must return shape (24, 5)."""
        result = LuminanceCalculator.compute(load_ldt(ldt_path), full=False)
        assert result.table.shape == (24, 5)

    def test_ugr_c_axis(self, ldt_path):
        """UGR C axis: 0, 15, ..., 345 deg."""
        result = LuminanceCalculator.compute(load_ldt(ldt_path), full=False)
        np.testing.assert_allclose(result.c_axis, np.arange(0.0, 360.0, 15.0))

    def test_ugr_g_axis(self, ldt_path):
        """UGR gamma axis: 65, 70, 75, 80, 85 deg."""
        result = LuminanceCalculator.compute(load_ldt(ldt_path), full=False)
        np.testing.assert_allclose(result.g_axis, np.arange(65.0, 86.0, 5.0))

    def test_all_luminances_non_negative(self, ldt_path):
        """No luminance value may be negative."""
        result = LuminanceCalculator.compute(load_ldt(ldt_path), full=False)
        assert np.all(result.table >= 0.0), (
            f"Negative luminance: min={result.table.min():.2f} cd/m2"
        )

    def test_maximum_positive(self, ldt_path):
        """Maximum luminance must be strictly positive."""
        result = LuminanceCalculator.compute(load_ldt(ldt_path), full=False)
        assert result.maximum > 0.0

    def test_maximum_matches_table(self, ldt_path):
        """result.maximum must equal np.max(result.table)."""
        result = LuminanceCalculator.compute(load_ldt(ldt_path), full=False)
        assert result.maximum == pytest.approx(np.max(result.table), rel=1e-6)

    def test_full_grid_shape(self, ldt_path):
        """Full grid shape must match native LDT resolution (mc x ng)."""
        from pyldt import LdtReader  # noqa: PLC0415
        ldt = LdtReader.read(str(ldt_path))
        result = LuminanceCalculator.compute(ldt, full=True)
        assert result.table.shape == (ldt.header.mc, ldt.header.ng)
        assert result.full is True

    def test_full_grid_at_least_as_large_as_ugr(self, ldt_path):
        """Full grid must contain at least as many values as the UGR grid."""
        ldt = load_ldt(ldt_path)
        assert (
            LuminanceCalculator.compute(ldt, full=True).table.size
            >= LuminanceCalculator.compute(ldt, full=False).table.size
        )

    def test_result_full_flag(self, ldt_path):
        """result.full must reflect the full= argument."""
        ldt = load_ldt(ldt_path)
        assert LuminanceCalculator.compute(ldt, full=False).full is False
        assert LuminanceCalculator.compute(ldt, full=True).full is True

    def test_luminaire_name_is_string(self, ldt_path):
        """result.luminaire_name must be a string."""
        result = LuminanceCalculator.compute(load_ldt(ldt_path), full=False)
        assert isinstance(result.luminaire_name, str)

    def test_csv_export_dimensions(self, ldt_path, tmp_path):
        """to_csv(): 1 header row + 24 data rows."""
        result = LuminanceCalculator.compute(load_ldt(ldt_path), full=False)
        out = tmp_path / f"{ldt_path.stem}.csv"
        result.to_csv(out)
        lines = out.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 25

    def test_json_export_structure(self, ldt_path, tmp_path):
        """to_json(): valid JSON with correct table dimensions."""
        result = LuminanceCalculator.compute(load_ldt(ldt_path), full=False)
        out = tmp_path / f"{ldt_path.stem}.json"
        result.to_json(out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data["table_cd_m2"]) == 24
        assert len(data["table_cd_m2"][0]) == 5


# ---------------------------------------------------------------------------
# TestSample04 -- spot-checks with expected numerical values
# ---------------------------------------------------------------------------


SAMPLE04 = DATA_DIR / "sample_04.ldt"


@pytest.mark.skipif(not SAMPLE04.exists(), reason="sample_04.ldt not found")
class TestSample04:
    """
    Numerical spot-checks for sample_04.ldt.

    Luminaire : linear, 1480 x 63 mm, flat (all heights = 0 mm)
    Lamp set  : 1 x 12334 lm  ->  flux_klm = 12.334
    ISYM      : 4 (quadrant), expanded to 24 C-planes x 37 gamma angles (5 deg step)

    Reference values computed by hand:
        C=0, gamma=65 (native index [0, 13]):
            I = 17.9 cd/klm x 12.334 = 220.78 cd
            A_proj = 1.480 x 0.063 x cos(65) = 0.03940 m2
            L = 220.78 / 0.03940 = 5603 cd/m2

        C=0, gamma=85 (native index [0, 17]):
            I = 0.305 cd/klm x 12.334 = 3.762 cd
            A_proj = 0.09324 x cos(85) = 0.008126 m2
            L = 3.762 / 0.008126 = 463 cd/m2
    """

    def test_luminaire_name(self):
        result = LuminanceCalculator.compute(load_ldt(SAMPLE04), full=False)
        assert result.luminaire_name == "sample_04"

    def test_spot_check_c0_g65(self):
        """C=0, gamma=65 -> 5603 cd/m2 (tol 2%)."""
        result = LuminanceCalculator.compute(load_ldt(SAMPLE04), full=False)
        i_c = int(np.searchsorted(result.c_axis, 0.0))
        i_g = int(np.searchsorted(result.g_axis, 65.0))
        assert result.table[i_c, i_g] == pytest.approx(5603, rel=0.02)

    def test_spot_check_c0_g85(self):
        """C=0, gamma=85 -> 463 cd/m2 (tol 2%)."""
        result = LuminanceCalculator.compute(load_ldt(SAMPLE04), full=False)
        i_c = int(np.searchsorted(result.c_axis, 0.0))
        i_g = int(np.searchsorted(result.g_axis, 85.0))
        assert result.table[i_c, i_g] == pytest.approx(463, rel=0.02)

    def test_maximum_expected(self):
        """Overall maximum ~ 5603 cd/m2 (tol 2%)."""
        result = LuminanceCalculator.compute(load_ldt(SAMPLE04), full=False)
        assert result.maximum == pytest.approx(5603, rel=0.02)

    def test_native_grid_shape(self):
        """Native grid: 24 C-planes x 37 gamma angles."""
        result = LuminanceCalculator.compute(load_ldt(SAMPLE04), full=True)
        assert result.table.shape == (24, 37)

    def test_flat_luminaire_g85_lower_than_g65(self):
        """All heights=0: L(gamma=85) < L(gamma=65) at C=0."""
        result = LuminanceCalculator.compute(load_ldt(SAMPLE04), full=False)
        i_c = int(np.searchsorted(result.c_axis, 0.0))
        i_65 = int(np.searchsorted(result.g_axis, 65.0))
        i_85 = int(np.searchsorted(result.g_axis, 85.0))
        assert result.table[i_c, i_85] < result.table[i_c, i_65]


# ---------------------------------------------------------------------------
# TestLuminancePlotSmoke -- export smoke tests, synthetic data
# ---------------------------------------------------------------------------


class TestLuminancePlotSmoke:
    """Smoke tests: verify that export methods run without crashing."""

    def _make_result(self):
        rng = np.random.default_rng(42)
        c_axis = np.arange(0.0, 360.0, 15.0)
        g_axis = np.array([65.0, 70.0, 75.0, 80.0, 85.0])
        table = rng.uniform(500, 5000, (len(c_axis), len(g_axis)))
        return LuminanceResult(
            table=table, c_axis=c_axis, g_axis=g_axis,
            full=False, luminaire_name="SMOKE-TEST",
        )

    def _require_vlc(self):
        try:
            import vl_convert  # noqa: F401
        except ImportError:
            pytest.skip("vl-convert-python not installed")

    def test_polar_svg(self, tmp_path):
        self._require_vlc()
        from eulumdat_luminance.plot import LuminancePlot
        out = tmp_path / "polar.svg"
        LuminancePlot(self._make_result()).polar(out)
        assert out.exists() and out.stat().st_size > 100

    def test_polar_png(self, tmp_path):
        self._require_vlc()
        from eulumdat_luminance.plot import LuminancePlot
        out = tmp_path / "polar.png"
        LuminancePlot(self._make_result()).polar(out)
        assert out.exists() and out.stat().st_size > 100

    def test_unsupported_format(self, tmp_path):
        from eulumdat_luminance.plot import LuminancePlot
        with pytest.raises(ValueError, match="Unsupported format"):
            LuminancePlot(self._make_result()).polar(tmp_path / "out.pdf")


# ---------------------------------------------------------------------------
# TestReluxValidation -- validation against Relux reference values
# ---------------------------------------------------------------------------

RELUX_REF = Path(__file__).parent.parent / "data" / "reference" / "relux_reference.json"


def load_relux_ref():
    """Load the Relux reference JSON. Skip all tests if the file is missing."""
    if not RELUX_REF.exists():
        pytest.skip(f"Relux reference not found: {RELUX_REF}")
    with RELUX_REF.open(encoding="utf-8") as f:
        return json.load(f)


def relux_sample_ids():
    """Return sample names from the reference file, or empty list if missing."""
    if not RELUX_REF.exists():
        return []
    with RELUX_REF.open(encoding="utf-8") as f:
        return list(json.load(f)["samples"].keys())


@pytest.mark.parametrize("sample_name", relux_sample_ids(), ids=lambda n: n)
class TestReluxValidation:
    """
    Validation of LuminanceCalculator against Relux reference values.

    Reference file : data/reference/relux_reference.json
    Tolerance      : relative 3% for values > 10 cd/m2,
                     absolute 10 cd/m2 for near-zero values
                     (Relux rounds to the nearest cd/m2, causing large
                     relative errors on values close to zero).

    Parametrised over all samples present in the reference file.
    A test is skipped if the corresponding .ldt file is missing from data/input/.
    """

    # Tolerances matching relux_reference.json["tolerance"]
    REL_TOL_PCT = 3.0    # % -- applied to values > ABS_TOL
    ABS_TOL = 10         # cd/m2 -- below this, only absolute error is checked

    def _load(self, sample_name):
        """Load LDT and compute result, skip if .ldt file is absent."""
        ldt_path = DATA_DIR / f"{sample_name}.ldt"
        if not ldt_path.exists():
            pytest.skip(f"{sample_name}.ldt not found in data/input/")
        ref = load_relux_ref()
        sdata = ref["samples"][sample_name]
        ldt = load_ldt(ldt_path)
        result = LuminanceCalculator.compute(ldt, full=False)
        g_angles = ref["grid"]["g_angles_deg"]
        c_planes = ref["grid"]["c_planes_deg"]
        ref_table = np.array(
            [[sdata["table"][str(g)][ci] for g in g_angles]
             for ci in range(len(c_planes))],
            dtype=float,
        )
        return result, ref_table, sdata

    def test_maximum(self, sample_name):
        """Maximum luminance must match Relux within REL_TOL_PCT."""
        result, _, sdata = self._load(sample_name)
        expected = sdata["maximum"]
        assert result.maximum == pytest.approx(expected, rel=self.REL_TOL_PCT / 100), (
            f"maximum: calc={result.maximum:.0f}  relux={expected}  "
            f"delta={abs(result.maximum - expected) / expected * 100:.2f}%"
        )

    def test_table_relative_tolerance(self, sample_name):
        """
        All cells with reference value > ABS_TOL must agree within REL_TOL_PCT.
        """
        result, ref_table, _ = self._load(sample_name)
        mask = ref_table > self.ABS_TOL
        if not mask.any():
            pytest.skip("No cell exceeds the absolute threshold.")
        calc = result.table[mask]
        ref  = ref_table[mask]
        rel_errors = np.abs(calc - ref) / ref * 100
        worst_idx = rel_errors.argmax()
        assert rel_errors.max() < self.REL_TOL_PCT, (
            f"Worst cell: calc={calc[worst_idx]:.0f}  relux={ref[worst_idx]:.0f}  "
            f"delta={rel_errors.max():.2f}%  (tolerance {self.REL_TOL_PCT}%)"
        )

    def test_table_absolute_tolerance(self, sample_name):
        """
        All cells with reference value <= ABS_TOL must agree within ABS_TOL cd/m2.
        """
        result, ref_table, _ = self._load(sample_name)
        mask = ref_table <= self.ABS_TOL
        if not mask.any():
            return  # no near-zero values
        abs_errors = np.abs(result.table[mask] - ref_table[mask])
        assert abs_errors.max() <= self.ABS_TOL, (
            f"Near-zero cell absolute error {abs_errors.max():.1f} cd/m2 "
            f"exceeds tolerance {self.ABS_TOL} cd/m2"
        )
