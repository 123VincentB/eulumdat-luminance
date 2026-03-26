# -*- coding: utf-8 -*-
"""
result.py
---------
Data container for a computed luminance table.

The LuminanceResult object is produced by LuminanceCalculator.compute() and
holds the luminance values (cd/m²) together with their angle axes and metadata.
It provides simple export methods (CSV, JSON) and is passed to LuminancePlot
for diagram generation.
"""

import csv
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import RegularGridInterpolator


class LuminanceResult:
    """
    Container for a computed luminance table.

    Attributes
    ----------
    table : np.ndarray, shape (n_c, n_g), dtype float64
        Luminance values in cd/m². Rows = C-planes, columns = γ angles.
    c_axis : np.ndarray, shape (n_c,)
        C-plane angles in degrees.
    g_axis : np.ndarray, shape (n_g,)
        γ angles in degrees.
    maximum : float
        Maximum luminance value in the table (cd/m²).
    full : bool
        True  → table covers all angles available in the source LDT file.
        False → table is resampled to the UGR grid
                (C: 0°–345° in 15° steps, γ: 65°–85° in 5° steps).
    luminaire_name : str
        Name of the luminaire, taken from the LDT file header.
    """

    # UGR grid definition (CIE 117 / CIE 190)
    UGR_C_START = 0.0
    UGR_C_STOP = 355.0
    UGR_C_STEP = 15.0
    UGR_G_START = 65.0
    UGR_G_STOP = 85.0
    UGR_G_STEP = 5.0

    def __init__(
        self,
        table: np.ndarray,
        c_axis: np.ndarray,
        g_axis: np.ndarray,
        full: bool,
        luminaire_name: str = "",
    ):
        """
        Parameters
        ----------
        table : np.ndarray, shape (n_c, n_g)
            Luminance values in cd/m².
        c_axis : np.ndarray
            C-plane angles in degrees.
        g_axis : np.ndarray
            γ angles in degrees.
        full : bool
            True if the table covers the full LDT angle grid.
        luminaire_name : str, optional
            Name of the luminaire.
        """
        self.table = np.asarray(table, dtype=np.float64)
        self.c_axis = np.asarray(c_axis, dtype=np.float64)
        self.g_axis = np.asarray(g_axis, dtype=np.float64)
        self.full = full
        self.luminaire_name = luminaire_name
        self.maximum = float(np.max(self.table))
        self._interpolator = None  # built lazily on first call to at()

    # ------------------------------------------------------------------
    # Interpolation
    # ------------------------------------------------------------------

    def at(
        self,
        c_deg: "float | np.ndarray",
        g_deg: "float | np.ndarray",
    ) -> "float | np.ndarray":
        """
        Interpolate luminance at arbitrary (C, γ) angles.

        Uses bilinear interpolation on the stored table.  The C axis is
        extended to 360° (copy of C=0°) so angles near the wrap-around
        (e.g. C=355°) are handled correctly.

        Parameters
        ----------
        c_deg : float or np.ndarray
            C-plane angle(s) in degrees.  Must be in [0°, 360°].
        g_deg : float or np.ndarray
            γ angle(s) in degrees.  Must lie within the stored g_axis range.

        Returns
        -------
        float
            For scalar inputs.
        np.ndarray
            For array inputs, same shape as the inputs.

        Raises
        ------
        ValueError
            If any (C, γ) point lies outside the interpolation domain.

        Notes
        -----
        For best accuracy, compute the result with ``full=True`` so that the
        interpolation uses the full native LDT resolution rather than the
        coarser UGR grid.

        Examples
        --------
        ::

            result = LuminanceCalculator.compute(ldt, full=True)

            # Single point
            lum = result.at(c_deg=12.0, g_deg=67.0)

            # Batch query (vectorised)
            lums = result.at(
                c_deg=np.array([0.0, 12.0, 90.0]),
                g_deg=np.array([65.0, 67.0, 75.0]),
            )
        """
        if self._interpolator is None:
            self._interpolator = self._build_interpolator()

        scalar = np.isscalar(c_deg) and np.isscalar(g_deg)
        c = np.atleast_1d(np.asarray(c_deg, dtype=np.float64)).ravel()
        g = np.atleast_1d(np.asarray(g_deg, dtype=np.float64)).ravel()
        values = self._interpolator(np.stack([c, g], axis=-1))
        return float(values[0]) if scalar else values

    def _build_interpolator(self) -> RegularGridInterpolator:
        """
        Build the bilinear interpolator on the stored luminance table.

        The C axis is extended by one point at 360° (= copy of C=0°) so
        that angles between 345° and 360° can be interpolated without
        hitting the upper bound of the domain.
        """
        c_ext = np.append(self.c_axis, 360.0)
        table_ext = np.vstack([self.table, self.table[0:1, :]])
        return RegularGridInterpolator(
            (c_ext, self.g_axis),
            table_ext,
            method="linear",
            bounds_error=True,
        )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def to_csv(self, path: str | Path) -> None:
        """
        Export the luminance table to a CSV file.

        The file has a header row with γ angles and one data row per C-plane.
        The first column contains the C-plane angle.

        Parameters
        ----------
        path : str or Path
            Destination file path. Parent directories must exist.
        """
        path = Path(path)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Header: first cell empty, then γ angles
            writer.writerow(["C \\ γ (°)"] + [f"{g:.1f}" for g in self.g_axis])
            # One row per C-plane
            for i, c in enumerate(self.c_axis):
                writer.writerow([f"{c:.1f}"] + [f"{v:.1f}" for v in self.table[i]])

    def to_json(self, path: str | Path) -> None:
        """
        Export the luminance table to a JSON file.

        Structure
        ---------
        {
            "luminaire_name": str,
            "full": bool,
            "maximum_cd_m2": float,
            "c_axis_deg": [...],
            "g_axis_deg": [...],
            "table_cd_m2": [[...], ...]   # shape (n_c, n_g)
        }

        Parameters
        ----------
        path : str or Path
            Destination file path. Parent directories must exist.
        """
        path = Path(path)
        payload = {
            "luminaire_name": self.luminaire_name,
            "full": self.full,
            "maximum_cd_m2": round(self.maximum, 2),
            "c_axis_deg": [round(float(c), 2) for c in self.c_axis],
            "g_axis_deg": [round(float(g), 2) for g in self.g_axis],
            "table_cd_m2": [
                [round(float(v), 2) for v in row] for row in self.table
            ],
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        grid = "UGR" if not self.full else "full"
        return (
            f"LuminanceResult("
            f"grid={grid}, "
            f"shape={self.table.shape}, "
            f"maximum={self.maximum:.0f} cd/m², "
            f"luminaire='{self.luminaire_name}')"
        )
