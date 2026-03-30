# -*- coding: utf-8 -*-
"""
calculator.py
-------------
Luminance table computation from an eulumdat-py Ldt object.

Physical model
--------------
The luminance L (cd/m²) in direction (C, γ) is defined as:

    L(C, γ) = I(C, γ) / A_proj(C, γ)

where:
    I(C, γ)      = luminous intensity in cd
                 = normalised intensity (from LDT) × luminous flux [klm] × 1000
    A_proj(C, γ) = projected luminous area visible from direction (C, γ), in m²

Projected area model
--------------------
The luminous area has a bottom face (length × width or circular) and up to four
lateral faces (heights at C0, C90, C180, C270).  The projection visible from
(C, γ) is:

    A_proj = A_bottom × cos(γ) + A_side(C) × sin(γ)

For a rectangular luminaire:
    A_side(C) = l × |cos(C)| × h_effective_l  +  w × |sin(C)| × h_effective_w

where h_effective_l and h_effective_w are the heights relevant in quadrant Q(C).

For a circular luminaire (width == 0):
    A_bottom = π × (length/2)²
    A_side(C) = length × h_C0  (simplified: symmetric, only C0 height used)

Quadrant mapping for heights (matching EULUMDAT convention)
-----------------------------------------------------------
    Q0  0° ≤ C < 90°   → h_l = C0,  h_w = C90
    Q1  90° ≤ C < 180° → h_l = C180, h_w = C90
    Q2  180° ≤ C < 270° → h_l = C180, h_w = C270
    Q3  270° ≤ C < 360° → h_l = C0,  h_w = C270

UGR grid (CIE 117 / CIE 190)
-----------------------------
    C: 0°, 15°, 30°, … 345°  (24 planes)
    γ: 65°, 70°, 75°, 80°, 85°  (5 angles)

If the LDT angle grid does not match the UGR grid exactly, bilinear
interpolation (scipy.interpolate.RegularGridInterpolator) is applied.
"""

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from eulumdat_luminance.result import LuminanceResult

# eulumdat-py (package name: eulumdat-py, installed module: pyldt)
# Public API: pyldt.LdtReader.read(path) → pyldt.Ldt
#   ldt.header         → pyldt.LdtHeader
#   ldt.header.luminaire_name   str
#   ldt.header.mc / dc          int / float   number of C-planes / step (°)
#   ldt.header.ng / dg          int / float   number of γ angles / step (°)
#   ldt.header.length_lum_area  float  mm
#   ldt.header.width_lum_area   float  mm
#   ldt.header.h_lum_c0/c90/c180/c270  float  mm
#   ldt.header.c_angles         List[float]   C-plane angles (°)
#   ldt.header.g_angles         List[float]   γ angles (°)
#   ldt.header.lamp_flux        List[float]   lumen per lamp set
#   ldt.header.num_lamps        List[int]     number of lamps per set
#   ldt.intensities             List[List[float]]  cd/klm, shape [mc × ng]
#                               already expanded to full angular range


class LuminanceCalculator:
    """
    Computes a luminance table from a eulumdat-py Ldt object.

    Usage
    -----
    ::

        from pyldt import LdtReader
        from eulumdat_luminance import LuminanceCalculator

        ldt = LdtReader.read("path/to/file.ldt")
        result = LuminanceCalculator.compute(ldt, full=False)
    """

    # UGR target grid
    _UGR_C = np.arange(0.0, 360.0, 15.0)   # 0 … 345, 24 values
    _UGR_G = np.arange(65.0, 86.0, 5.0)    # 65, 70, 75, 80, 85 — 5 values

    @classmethod
    def compute(cls, ldt, full: bool = False) -> LuminanceResult:
        """
        Compute the luminance table for a luminaire.

        Parameters
        ----------
        ldt : eulumdat_py.Ldt
            Parsed EULUMDAT object.  eulumdat-py guarantees a complete
            intensity matrix covering C 0°–360° and γ 0°–180°.
        full : bool, optional
            False (default) → resample to the UGR grid (24 C-planes × 5 γ angles).
            True            → use the full angle grid from the LDT file.

        Returns
        -------
        LuminanceResult
            Luminance table and associated metadata.

        Raises
        ------
        ValueError
            If the luminous area is zero (cannot divide intensity by zero area).
        """
        # --- 1. Extract geometry from LDT ----------------------------------
        # eulumdat-py API: all geometry is in ldt.header, in mm
        h = ldt.header

        length_mm = float(h.length_lum_area)   # mm
        width_mm = float(h.width_lum_area)     # mm
        h_c0_mm = float(h.h_lum_c0)           # mm
        h_c90_mm = float(h.h_lum_c90)         # mm
        h_c180_mm = float(h.h_lum_c180)       # mm
        h_c270_mm = float(h.h_lum_c270)       # mm

        # Convert mm → m
        length = length_mm / 1000.0
        width = width_mm / 1000.0
        h_c0 = h_c0_mm / 1000.0
        h_c90 = h_c90_mm / 1000.0
        h_c180 = h_c180_mm / 1000.0
        h_c270 = h_c270_mm / 1000.0

        # Circular luminaire: width_lum_area == 0, length_lum_area = diameter
        circular = (width_mm == 0.0)

        # Bottom luminous area (m²)
        if circular:
            a_bottom = np.pi * (length / 2.0) ** 2
        else:
            a_bottom = length * width

        if a_bottom <= 0.0:
            raise ValueError(
                "Luminous area is zero. "
                "Check 'length_lum_area' in the LDT file header."
            )

        # --- 2. Build C and γ axes and intensity matrix --------------------
        # ldt.header.c_angles / g_angles: lists of angles in degrees
        # ldt.intensities: List[List[float]], shape [mc × ng], in cd/klm
        #   Always expanded to full angular range by eulumdat-py.
        c_axis = np.array(h.c_angles, dtype=np.float64)
        g_axis = np.array(h.g_angles, dtype=np.float64)
        intensity_matrix = np.array(ldt.intensities, dtype=np.float64)

        # Luminous flux used for normalisation.
        #
        # EULUMDAT intensity values are stored in cd/klm, normalised against
        # the FIRST lamp set only — regardless of how many sets are defined.
        # Additional sets describe alternative lamp configurations (e.g. colour
        # temperatures or driver options) and must NOT be summed into the flux.
        # Relux, DIALux and other tools consistently use only the first set.
        # Reference: EULUMDAT format spec, lamp data lines 26a-26f.
        flux_klm = float(h.num_lamps[0]) * float(h.lamp_flux[0]) / 1000.0

        # Intensity in cd: intensities [cd/klm] × flux [klm]
        intensities_cd = intensity_matrix * flux_klm  # shape (n_c, n_g)

        # --- 3. Compute luminance for all (C, γ) on the native grid --------
        lum_table = cls._compute_luminance_table(
            intensities_cd, c_axis, g_axis,
            a_bottom, length, width,
            h_c0, h_c90, h_c180, h_c270,
            circular,
        )

        # --- 4. Resample to UGR grid if requested --------------------------
        if not full:
            lum_table, c_out, g_out = cls._resample_to_ugr(
                lum_table, c_axis, g_axis
            )
        else:
            c_out, g_out = c_axis, g_axis

        # --- 5. Retrieve luminaire name ------------------------------------
        try:
            luminaire_name = str(ldt.header.luminaire_name).strip()
        except AttributeError:
            luminaire_name = ""

        return LuminanceResult(
            table=lum_table,
            c_axis=c_out,
            g_axis=g_out,
            full=full,
            luminaire_name=luminaire_name,
            _a_bottom=a_bottom,
            _length=length,
            _width=width,
            _h_c0=h_c0,
            _h_c90=h_c90,
            _h_c180=h_c180,
            _h_c270=h_c270,
            _circular=circular,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _projected_area(
        c_deg: np.ndarray,
        g_deg: np.ndarray,
        a_bottom: float,
        length: float,
        width: float,
        h_c0: float,
        h_c90: float,
        h_c180: float,
        h_c270: float,
        circular: bool,
    ) -> np.ndarray:
        """
        Compute the projected luminous area A_proj(C, γ) for all (C, γ) pairs.

        Parameters
        ----------
        c_deg : np.ndarray, shape (n_c,)
            C-plane angles in degrees.
        g_deg : np.ndarray, shape (n_g,)
            γ angles in degrees.
        a_bottom : float
            Bottom face area in m².
        length, width : float
            Luminous area dimensions in m.
        h_c0, h_c90, h_c180, h_c270 : float
            Lateral heights in m.
        circular : bool
            True if the luminous area is circular (width == 0).

        Returns
        -------
        np.ndarray, shape (n_c, n_g)
            Projected area in m².  Values at γ = 90° where all heights are 0
            will be 0 (handled upstream by clipping).
        """
        c_rad = np.radians(c_deg)  # (n_c,)
        g_rad = np.radians(g_deg)  # (n_g,)

        cos_g = np.cos(g_rad)  # (n_g,)
        sin_g = np.sin(g_rad)  # (n_g,)

        # Bottom contribution: a_bottom × cos(γ), broadcast over C
        # shape: (n_c, n_g)
        a_proj = np.outer(np.ones(len(c_rad)), a_bottom * cos_g)

        if circular:
            # Lateral contribution: diameter × h_c0 × sin(γ)
            # Simplified: use h_c0 for all C (circular symmetry assumed)
            a_side = length * h_c0 * sin_g  # (n_g,)
            a_proj += np.outer(np.ones(len(c_rad)), a_side)
        else:
            # Heights by quadrant
            # Q0: 0° ≤ C < 90°   h_l = C0,   h_w = C90
            # Q1: 90° ≤ C < 180° h_l = C180, h_w = C90
            # Q2: 180° ≤ C < 270° h_l = C180, h_w = C270
            # Q3: 270° ≤ C < 360° h_l = C0,   h_w = C270
            h_l = np.where(
                c_deg < 90.0,  np.full_like(c_deg, h_c0),
                np.where(
                    c_deg < 180.0, np.full_like(c_deg, h_c180),
                    np.where(
                        c_deg < 270.0, np.full_like(c_deg, h_c180),
                        np.full_like(c_deg, h_c0),
                    )
                )
            )  # (n_c,)

            h_w = np.where(
                c_deg < 90.0,  np.full_like(c_deg, h_c90),
                np.where(
                    c_deg < 180.0, np.full_like(c_deg, h_c90),
                    np.where(
                        c_deg < 270.0, np.full_like(c_deg, h_c270),
                        np.full_like(c_deg, h_c270),
                    )
                )
            )  # (n_c,)

            # Projected side lengths
            proj_l = length * np.abs(np.cos(c_rad))  # (n_c,)
            proj_w = width * np.abs(np.sin(c_rad))   # (n_c,)

            # Lateral area contribution for each (C, γ):
            # (proj_l × h_l + proj_w × h_w) × sin(γ)
            a_side_c = proj_l * h_l + proj_w * h_w   # (n_c,)
            a_proj += np.outer(a_side_c, sin_g)       # (n_c, n_g)

        return a_proj

    @classmethod
    def _compute_luminance_table(
        cls,
        intensities_cd: np.ndarray,
        c_axis: np.ndarray,
        g_axis: np.ndarray,
        a_bottom: float,
        length: float,
        width: float,
        h_c0: float,
        h_c90: float,
        h_c180: float,
        h_c270: float,
        circular: bool,
    ) -> np.ndarray:
        """
        Compute luminance L = I / A_proj for all (C, γ) on the native grid.

        Parameters
        ----------
        intensities_cd : np.ndarray, shape (n_c, n_g)
            Luminous intensity in cd.
        c_axis, g_axis : np.ndarray
            Angle axes in degrees.
        a_bottom, length, width : float
            Luminous area geometry in m.
        h_c0, h_c90, h_c180, h_c270 : float
            Lateral heights in m.
        circular : bool
            True if the luminous area is circular.

        Returns
        -------
        np.ndarray, shape (n_c, n_g)
            Luminance in cd/m².  Entries where A_proj ≈ 0 are set to 0.
        """
        a_proj = cls._projected_area(
            c_axis, g_axis,
            a_bottom, length, width,
            h_c0, h_c90, h_c180, h_c270,
            circular,
        )

        # Safe division: where A_proj == 0, luminance is undefined → set to 0
        with np.errstate(divide="ignore", invalid="ignore"):
            luminance = np.where(a_proj > 0.0, intensities_cd / a_proj, 0.0)

        return luminance

    @classmethod
    def _resample_to_ugr(
        cls,
        lum_table: np.ndarray,
        c_axis: np.ndarray,
        g_axis: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Resample the luminance table to the UGR grid using bilinear interpolation.

        The UGR grid is:
            C: 0°, 15°, 30°, …, 345°  (24 planes)
            γ: 65°, 70°, 75°, 80°, 85°  (5 angles)

        Parameters
        ----------
        lum_table : np.ndarray, shape (n_c, n_g)
            Luminance on the native LDT grid.
        c_axis : np.ndarray
            C-plane angles of the native grid.
        g_axis : np.ndarray
            γ angles of the native grid.

        Returns
        -------
        tuple (resampled_table, ugr_c_axis, ugr_g_axis)
            resampled_table : np.ndarray, shape (24, 5)
            ugr_c_axis      : np.ndarray, shape (24,)
            ugr_g_axis      : np.ndarray, shape (5,)

        Raises
        ------
        ValueError
            If the native grid does not cover the full UGR range.
        """
        # Sanity check: native grid must cover 0°–345° in C and 65°–85° in γ
        if c_axis.max() < cls._UGR_C.max():
            raise ValueError(
                f"Native C axis ends at {c_axis.max():.1f}°, "
                f"but UGR grid requires up to {cls._UGR_C.max():.1f}°."
            )
        if g_axis.max() < cls._UGR_G.max():
            raise ValueError(
                f"Native γ axis ends at {g_axis.max():.1f}°, "
                f"but UGR grid requires up to {cls._UGR_G.max():.1f}°."
            )
        if g_axis.min() > cls._UGR_G.min():
            raise ValueError(
                f"Native γ axis starts at {g_axis.min():.1f}°, "
                f"but UGR grid requires data from {cls._UGR_G.min():.1f}°."
            )

        interpolator = RegularGridInterpolator(
            (c_axis, g_axis),
            lum_table,
            method="linear",
            bounds_error=True,
        )

        # Build meshgrid of target points
        cc, gg = np.meshgrid(cls._UGR_C, cls._UGR_G, indexing="ij")
        points = np.stack([cc.ravel(), gg.ravel()], axis=-1)
        resampled = interpolator(points).reshape(len(cls._UGR_C), len(cls._UGR_G))

        return resampled, cls._UGR_C.copy(), cls._UGR_G.copy()
