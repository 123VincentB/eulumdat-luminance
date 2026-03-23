# -*- coding: utf-8 -*-
"""
plot.py
-------
Diagram generation for a LuminanceResult object.

Two diagram types are provided:

Söllner diagram
    γ angle (45°–85°) on the Y axis, luminance (cd/m²) on a logarithmic X axis.
    One curve per C-plane.  Default C-planes: C0, C90, C180, C270.
    This is the standard diagram used for glare classification (EN 12464, UGR).

Polar luminance diagram
    C-plane angle (0°–360°) on the polar axis, luminance (cd/m²) as radial
    distance.  One curve per γ angle.  The radial scale is linear.

Both diagrams are exported as SVG (via Vega-Lite / vl-convert-python) and
optionally as PNG or JPG.

Dependencies
------------
vl-convert-python : SVG rendering and raster export
Pillow            : JPG conversion (vl-convert outputs PNG natively)
"""

import json
from pathlib import Path

import numpy as np

try:
    import vl_convert as vlc
except ImportError:  # pragma: no cover
    vlc = None

try:
    from PIL import Image
    import io as _io
except ImportError:  # pragma: no cover
    Image = None

from eulumdat_luminance.result import LuminanceResult


# Default C-planes to draw (degrees)
_DEFAULT_C_PLANES = [0.0, 90.0, 180.0, 270.0]

# Line styles per C-plane (Vega-Lite strokeDash)
_C_PLANE_STYLES = {
    0.0:   {"strokeDash": [],        "color": "#1a1a1a"},  # solid
    90.0:  {"strokeDash": [6, 3],    "color": "#1a1a1a"},  # dashed
    180.0: {"strokeDash": [8, 3, 2, 3], "color": "#1a1a1a"},  # dash-dot
    270.0: {"strokeDash": [3, 3],    "color": "#1a1a1a"},  # dotted
}

# γ angle colours for the polar diagram (same palette as eulumdat-plot)
_G_COLORS = {
    65.0: "#08306b",
    70.0: "#2171b5",
    75.0: "#6baed6",
    80.0: "#9ecae1",
    85.0: "#c6dbef",
}


class LuminancePlot:
    """
    Generate Söllner and polar luminance diagrams from a LuminanceResult.

    Parameters
    ----------
    result : LuminanceResult
        Computed luminance table.

    Examples
    --------
    ::

        plot = LuminancePlot(result)
        plot.soellner("output/soellner.svg")
        plot.soellner("output/soellner.png")
        plot.polar("output/polar.svg")
        plot.polar("output/polar.png")
    """

    def __init__(self, result: LuminanceResult):
        self.result = result

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def soellner(
        self,
        path: str | Path,
        c_planes: list[float] | None = None,
        g_min: float = 45.0,
        g_max: float = 85.0,
        width: int = 500,
        height: int = 600,
        scale: float = 2.0,
    ) -> None:
        """
        Export a Söllner diagram.

        Parameters
        ----------
        path : str or Path
            Output file.  Extension determines format: .svg, .png, or .jpg/.jpeg.
        c_planes : list of float, optional
            C-plane angles (degrees) to draw.  Defaults to [0, 90, 180, 270].
        g_min : float, optional
            Minimum γ angle on the Y axis.  Default 45°.
        g_max : float, optional
            Maximum γ angle on the Y axis.  Default 85°.
        width, height : int, optional
            Diagram dimensions in pixels (PNG/JPG) or SVG user units.
        scale : float, optional
            Scale factor for raster export (PNG/JPG).  Default 2.0 (retina).
        """
        c_planes = c_planes if c_planes is not None else _DEFAULT_C_PLANES
        spec = self._soellner_spec(c_planes, g_min, g_max, width, height)
        self._export(spec, path, scale)

    def polar(
        self,
        path: str | Path,
        g_angles: list[float] | None = None,
        width: int = 500,
        height: int = 520,
        scale: float = 2.0,
    ) -> None:
        """
        Export a polar luminance diagram.

        Parameters
        ----------
        path : str or Path
            Output file.  Extension determines format: .svg, .png, or .jpg/.jpeg.
        g_angles : list of float, optional
            γ angles (degrees) to draw.  Defaults to all angles in the result.
        width, height : int, optional
            Diagram dimensions in pixels (PNG/JPG) or SVG user units.
        scale : float, optional
            Scale factor for raster export.  Default 2.0.
        """
        g_angles = g_angles if g_angles is not None else list(self.result.g_axis)
        spec = self._polar_spec(g_angles, width, height)
        self._export(spec, path, scale)

    # ------------------------------------------------------------------
    # Vega-Lite spec builders
    # ------------------------------------------------------------------

    def _soellner_spec(
        self,
        c_planes: list[float],
        g_min: float,
        g_max: float,
        width: int,
        height: int,
    ) -> dict:
        """
        Build a Vega-Lite specification for the Söllner diagram.

        The Söllner diagram has:
        - X axis: luminance in cd/m² on a logarithmic scale
        - Y axis: γ angle in degrees (inverted: 85° at top, 45° at bottom)
        - One line per selected C-plane

        Parameters
        ----------
        c_planes : list of float
            C-plane angles to include.
        g_min, g_max : float
            Y-axis range.
        width, height : int
            Chart dimensions.

        Returns
        -------
        dict
            Vega-Lite specification.
        """
        rows = self._soellner_data(c_planes, g_min, g_max)
        if not rows:
            raise ValueError("No data available for the requested C-planes.")

        # Build per-plane style conditions for strokeDash
        stroke_dash_conditions = []
        for c in c_planes:
            style = _C_PLANE_STYLES.get(c, {"strokeDash": [4, 2], "color": "#555"})
            stroke_dash_conditions.append({
                "test": f"datum.c_plane == '{c:.0f}°'",
                "value": style["strokeDash"] if style["strokeDash"] else [1, 0],
            })
        stroke_dash_conditions.append({"value": [4, 2]})  # fallback

        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "width": width,
            "height": height,
            "title": {
                "text": self.result.luminaire_name or "Luminance diagram",
                "subtitle": "Söllner diagram — luminance vs. angle",
                "fontSize": 13,
                "subtitleFontSize": 11,
            },
            "data": {"values": rows},
            "mark": {"type": "line", "strokeWidth": 1.5, "clip": True},
            "encoding": {
                "x": {
                    "field": "luminance",
                    "type": "quantitative",
                    "scale": {"type": "log", "nice": False},
                    "axis": {
                        "title": "L [cd/m²]",
                        "titleFontSize": 11,
                        "grid": True,
                        "gridDash": [2, 2],
                        "gridOpacity": 0.5,
                    },
                },
                "y": {
                    "field": "gamma",
                    "type": "quantitative",
                    "scale": {"domain": [g_min, g_max], "nice": False},
                    "axis": {
                        "title": "γ [°]",
                        "titleFontSize": 11,
                        "values": list(np.arange(g_min, g_max + 1, 5).tolist()),
                        "grid": True,
                        "gridDash": [2, 2],
                        "gridOpacity": 0.5,
                    },
                },
                "color": {
                    "field": "c_plane",
                    "type": "nominal",
                    "scale": {"range": ["#1a1a1a", "#1a1a1a", "#1a1a1a", "#1a1a1a"]},
                    "legend": {
                        "title": None,
                        "orient": "bottom-right",
                        "symbolType": "stroke",
                        "symbolStrokeWidth": 1.5,
                    },
                },
                "strokeDash": {
                    "condition": stroke_dash_conditions[:-1],
                    "value": stroke_dash_conditions[-1]["value"],
                },
                "order": {"field": "gamma", "type": "quantitative"},
            },
            "config": {
                "view": {"stroke": "transparent"},
                "axis": {"labelFontSize": 10},
                "background": "white",
            },
        }
        return spec

    def _polar_spec(
        self,
        g_angles: list[float],
        width: int,
        height: int,
    ) -> dict:
        """
        Build a Vega-Lite specification for the polar luminance diagram.

        Uses a Vega (not Vega-Lite) wind-rose / polar approach via a layer
        with arc marks transformed by the C-plane angle.

        Note: Vega-Lite has limited native polar support.  This implementation
        uses a projection-based approach: it converts polar (C, L) to Cartesian
        (x, y) in Python and plots as a standard line chart.

        Parameters
        ----------
        g_angles : list of float
            γ angles to include.
        width, height : int
            Chart dimensions.

        Returns
        -------
        dict
            Vega-Lite specification.
        """
        rows = self._polar_data(g_angles)
        if not rows:
            raise ValueError("No data available for the requested γ angles.")

        # Determine a clean radial scale maximum
        max_lum = self.result.maximum
        r_max = self._round_scale_max(max_lum)

        # Concentric grid ring values
        n_rings = 4
        ring_values = [round(r_max * i / n_rings) for i in range(1, n_rings + 1)]

        # Gamma colour scale
        g_domain = sorted(set(row["gamma"] for row in rows))
        g_range = [
            _G_COLORS.get(g, "#333333") for g in g_domain
        ]

        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "width": width,
            "height": height,
            "title": {
                "text": self.result.luminaire_name or "Luminance diagram",
                "subtitle": "Polar luminance diagram",
                "fontSize": 13,
                "subtitleFontSize": 11,
            },
            "layer": [
                # Concentric grid rings (circles drawn as lines)
                {
                    "data": {"values": self._circle_data(ring_values, r_max)},
                    "mark": {
                        "type": "line",
                        "strokeWidth": 0.5,
                        "color": "#cccccc",
                        "clip": False,
                    },
                    "encoding": {
                        "x": {"field": "x", "type": "quantitative",
                              "axis": None, "scale": {"domain": [-1.1, 1.1]}},
                        "y": {"field": "y", "type": "quantitative",
                              "axis": None, "scale": {"domain": [-1.1, 1.1]}},
                        "detail": {"field": "ring_id", "type": "nominal"},
                        "order": {"field": "order", "type": "quantitative"},
                    },
                },
                # Ring labels
                {
                    "data": {"values": self._ring_labels(ring_values, r_max)},
                    "mark": {"type": "text", "fontSize": 9,
                             "color": "#888888", "dy": -2},
                    "encoding": {
                        "x": {"field": "x", "type": "quantitative",
                              "axis": None, "scale": {"domain": [-1.1, 1.1]}},
                        "y": {"field": "y", "type": "quantitative",
                              "axis": None, "scale": {"domain": [-1.1, 1.1]}},
                        "text": {"field": "label", "type": "nominal"},
                    },
                },
                # Spoke lines at every 15°
                {
                    "data": {"values": self._spoke_data()},
                    "mark": {"type": "line", "strokeWidth": 0.4,
                             "color": "#cccccc", "clip": False},
                    "encoding": {
                        "x": {"field": "x", "type": "quantitative",
                              "axis": None, "scale": {"domain": [-1.1, 1.1]}},
                        "y": {"field": "y", "type": "quantitative",
                              "axis": None, "scale": {"domain": [-1.1, 1.1]}},
                        "detail": {"field": "spoke_id", "type": "nominal"},
                        "order": {"field": "order", "type": "quantitative"},
                    },
                },
                # Luminance curves
                {
                    "data": {"values": rows},
                    "mark": {"type": "line", "strokeWidth": 1.5},
                    "encoding": {
                        "x": {"field": "x", "type": "quantitative",
                              "axis": None, "scale": {"domain": [-1.1, 1.1]}},
                        "y": {"field": "y", "type": "quantitative",
                              "axis": None, "scale": {"domain": [-1.1, 1.1]}},
                        "color": {
                            "field": "gamma",
                            "type": "quantitative",
                            "scale": {"domain": g_domain, "range": g_range},
                            "legend": {
                                "title": "γ [°]",
                                "orient": "right",
                                "symbolType": "stroke",
                                "symbolStrokeWidth": 1.5,
                                "format": ".0f",
                            },
                        },
                        "detail": {"field": "gamma", "type": "nominal"},
                        "order": {"field": "c_deg", "type": "quantitative"},
                    },
                },
                # Angle labels
                {
                    "data": {"values": self._angle_labels()},
                    "mark": {"type": "text", "fontSize": 10, "color": "#444444"},
                    "encoding": {
                        "x": {"field": "x", "type": "quantitative",
                              "axis": None, "scale": {"domain": [-1.1, 1.1]}},
                        "y": {"field": "y", "type": "quantitative",
                              "axis": None, "scale": {"domain": [-1.1, 1.1]}},
                        "text": {"field": "label", "type": "nominal"},
                        "align": {"field": "align", "type": "nominal"},
                        "baseline": {"field": "baseline", "type": "nominal"},
                    },
                },
                # Maximum annotation
                {
                    "data": {"values": [{"label": f"Maximum: {self.result.maximum:.0f} cd/m²"}]},
                    "mark": {"type": "text", "fontSize": 10,
                             "color": "#333333", "align": "center",
                             "x": {"expr": "width / 2"}, "y": {"expr": "height - 10"}},
                    "encoding": {
                        "text": {"field": "label", "type": "nominal"},
                    },
                },
            ],
            "resolve": {"scale": {"x": "shared", "y": "shared", "color": "independent"}},
            "config": {
                "view": {"stroke": "transparent"},
                "background": "white",
            },
        }
        return spec

    # ------------------------------------------------------------------
    # Data preparation helpers
    # ------------------------------------------------------------------

    def _soellner_data(
        self, c_planes: list[float], g_min: float, g_max: float
    ) -> list[dict]:
        """
        Build a flat list of {luminance, gamma, c_plane} records for the Söllner
        diagram, filtered to the γ range [g_min, g_max] and to rows where
        luminance > 0 (log scale requires positive values).
        """
        result = self.result
        rows = []
        for c in c_planes:
            # Find the nearest C-plane index
            idx_c = int(np.argmin(np.abs(result.c_axis - c)))
            label = f"{result.c_axis[idx_c]:.0f}°"
            for j, g in enumerate(result.g_axis):
                if g < g_min or g > g_max:
                    continue
                lum = result.table[idx_c, j]
                if lum <= 0.0:
                    continue
                rows.append({
                    "luminance": float(lum),
                    "gamma": float(g),
                    "c_plane": label,
                })
        return rows

    def _polar_data(self, g_angles: list[float]) -> list[dict]:
        """
        Build a flat list of {x, y, gamma, c_deg} records for the polar diagram.
        Polar (C, L) is converted to normalised Cartesian (x, y) using
        L / r_max as the radial coordinate.
        """
        result = self.result
        r_max = self._round_scale_max(result.maximum)
        rows = []
        for g in g_angles:
            idx_g = int(np.argmin(np.abs(result.g_axis - g)))
            actual_g = float(result.g_axis[idx_g])
            for i, c in enumerate(result.c_axis):
                lum = result.table[i, idx_g]
                r = float(lum) / r_max
                c_rad = np.radians(float(c))
                rows.append({
                    "x": float(r * np.sin(c_rad)),
                    "y": float(-r * np.cos(c_rad)),
                    "gamma": actual_g,
                    "c_deg": float(c),
                })
            # Close the curve: repeat first point
            if rows:
                first = next(
                    row for row in rows if row["gamma"] == actual_g and row["c_deg"] == float(result.c_axis[0])
                )
                rows.append({**first, "c_deg": 360.0})
        return rows

    @staticmethod
    def _circle_data(ring_values: list[float], r_max: float) -> list[dict]:
        """Generate Cartesian points for concentric grid circles."""
        angles = np.linspace(0, 2 * np.pi, 361)
        rows = []
        for k, rv in enumerate(ring_values):
            r = rv / r_max
            for i, a in enumerate(angles):
                rows.append({
                    "x": float(r * np.sin(a)),
                    "y": float(-r * np.cos(a)),
                    "ring_id": k,
                    "order": i,
                })
        return rows

    @staticmethod
    def _ring_labels(ring_values: list[float], r_max: float) -> list[dict]:
        """Generate label positions for concentric grid circles (placed at C=0°)."""
        rows = []
        for rv in ring_values:
            r = rv / r_max
            rows.append({"x": 0.0, "y": -r, "label": f"{int(rv)}"})
        return rows

    @staticmethod
    def _spoke_data() -> list[dict]:
        """Generate Cartesian points for 24 spoke lines (every 15°)."""
        rows = []
        for k, c_deg in enumerate(range(0, 360, 15)):
            c_rad = np.radians(c_deg)
            rows.extend([
                {"x": 0.0, "y": 0.0, "spoke_id": k, "order": 0},
                {"x": float(np.sin(c_rad)), "y": float(-np.cos(c_rad)),
                 "spoke_id": k, "order": 1},
            ])
        return rows

    @staticmethod
    def _angle_labels() -> list[dict]:
        """Generate angle labels at major C-planes (every 15°) on the outer ring."""
        rows = []
        for c_deg in range(0, 360, 15):
            c_rad = np.radians(c_deg)
            r = 1.07
            x = float(r * np.sin(c_rad))
            y = float(-r * np.cos(c_rad))
            # Text alignment based on position
            if c_deg in (0, 180):
                align, baseline = "center", "middle"
            elif 0 < c_deg < 180:
                align, baseline = "left", "middle"
            else:
                align, baseline = "right", "middle"
            rows.append({"x": x, "y": y,
                         "label": f"{c_deg}°",
                         "align": align, "baseline": baseline})
        return rows

    # ------------------------------------------------------------------
    # Scale helper
    # ------------------------------------------------------------------

    @staticmethod
    def _round_scale_max(value: float) -> float:
        """
        Return a round number >= value suitable as a radial scale maximum.
        Rounds up to the nearest 1000 for values > 1000, else nearest 500.
        """
        if value <= 0:
            return 1000.0
        if value > 1000:
            return float(np.ceil(value / 1000) * 1000)
        return float(np.ceil(value / 500) * 500)

    # ------------------------------------------------------------------
    # Export engine
    # ------------------------------------------------------------------

    @staticmethod
    def _export(spec: dict, path: str | Path, scale: float) -> None:
        """
        Render a Vega-Lite spec to SVG, PNG, or JPG.

        Parameters
        ----------
        spec : dict
            Vega-Lite specification.
        path : str or Path
            Output file path.  Extension must be .svg, .png, .jpg, or .jpeg.
        scale : float
            Scale factor for raster output.
        """
        if vlc is None:
            raise ImportError(
                "vl-convert-python is required for diagram export. "
                "Install it with: pip install vl-convert-python"
            )

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        suffix = path.suffix.lower()
        spec_str = json.dumps(spec)

        if suffix == ".svg":
            svg_bytes = vlc.vegalite_to_svg(spec_str)
            path.write_bytes(svg_bytes if isinstance(svg_bytes, bytes)
                             else svg_bytes.encode("utf-8"))

        elif suffix == ".png":
            png_bytes = vlc.vegalite_to_png(spec_str, scale=scale)
            path.write_bytes(png_bytes)

        elif suffix in (".jpg", ".jpeg"):
            if Image is None:
                raise ImportError(
                    "Pillow is required for JPG export. "
                    "Install it with: pip install Pillow"
                )
            png_bytes = vlc.vegalite_to_png(spec_str, scale=scale)
            img = Image.open(_io.BytesIO(png_bytes)).convert("RGB")
            img.save(path, format="JPEG", quality=92, optimize=True)

        else:
            raise ValueError(
                f"Unsupported output format '{suffix}'. "
                "Use .svg, .png, .jpg, or .jpeg."
            )
