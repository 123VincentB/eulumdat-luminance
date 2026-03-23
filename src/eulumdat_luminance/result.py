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
                (C: 0°–355° in 15° steps, γ: 65°–85° in 5° steps).
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
