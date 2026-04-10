# -*- coding: utf-8 -*-
"""
plot.py
-------
Polar luminance diagram generation from a LuminanceResult object.

SVG layer architecture
----------------------
main
  padding (uniform border around the full canvas)
  diagram   <g translate(cx, cy)> — all diagram layers share this origin
    grid        <g clip-path>  concentric rings + spokes
    curves      <g clip-path>  luminance polylines + threshold circle
    ring-labels <g>            cd/m² labels on C=270° axis (not clipped)
    angle-labels<g>            C-plane labels around outer ring (not clipped)
  title     <g translate(tx, ty)>
  legend    <g translate(lx, ly)>

clip-path is a circle of radius diagram_r, defined in <defs>.
grid and curves cannot overflow into the padding area.
ring-labels and angle-labels are intentionally outside the clip zone.

Rasterisation to PNG/JPG via vl-convert-python (svg_to_png).

Dependencies
------------
vl-convert-python : SVG -> PNG/JPG
Pillow            : JPG conversion
"""

import io
import math
from pathlib import Path

import numpy as np

try:
    import vl_convert as vlc
except ImportError:  # pragma: no cover
    vlc = None

try:
    from PIL import Image as _PILImage
except ImportError:  # pragma: no cover
    _PILImage = None

from eulumdat_luminance.result import LuminanceResult


# ---------------------------------------------------------------------------
# Default gamma colour palette (65° dark -> 85° light blue)
# ---------------------------------------------------------------------------
_G_COLORS: dict[float, str] = {
    65.0: "#08306b",
    70.0: "#2171b5",
    75.0: "#6baed6",
    80.0: "#9ecae1",
    85.0: "#c6dbef",
}


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

class PolarStyle:
    """
    Visual style and layout parameters for the polar luminance diagram.

    Canvas layout
    -------------
    ::

        ┌──────────────────────────────────────────────────┐
        │  padding                                         │
        │  ┌─────────────────────────────────────────────┐ │
        │  │  title_area  (title + subtitle + maximum)   │ │
        │  ├──────────────────────────┬──────────────────┤ │
        │  │ left_area │   diagram    │   legend_area    │ │
        │  │           │  (circle)    │                  │ │
        │  │           │              │                  │ │
        │  ├──────────────────────────┤                  │ │
        │  │  bottom_area             │                  │ │
        │  └─────────────────────────────────────────────┘ │
        │  padding                                         │
        └──────────────────────────────────────────────────┘

    ``diagram_r`` is the polar circle radius.  All other dimensions scale
    proportionally via ``PolarStyle.for_size()``.

    Positioning
    -----------
    Each layer is positioned in canvas space via a computed default.
    ``*_offset_x/y`` parameters allow fine-tuning without changing the layout.

    - ``diagram`` : centre of circle = (padding + left_area + r,
                                        padding + title_area + r)
    - ``title``   : centred horizontally on the circle centre, top = padding
    - ``legend``  : left edge = circle right + gap, top = circle top

    Parameters
    ----------
    diagram_r : int
        Radius of the polar circle in SVG user units.  Default 250.
    padding : int
        Uniform border around the full canvas.  Default 10.
    title_area_height : int
        Height reserved above the circle for the title block.  Default 70.
    legend_area_width : int
        Width reserved to the right of the circle for the legend.  Default 110.
    bottom_area_height : int
        Height reserved below the circle (angle labels overhang).  Default 35.
    left_area_width : int
        Width reserved to the left of the circle (angle labels overhang).  Default 35.
    diagram_offset_x : int
        Horizontal offset of the diagram layer from its default position.
    diagram_offset_y : int
        Vertical offset of the diagram layer from its default position.
    title_offset_x : int
        Horizontal offset of the title layer from its default position.
    title_offset_y : int
        Vertical offset of the title layer from its default position.
    legend_offset_x : int
        Horizontal offset of the legend layer from its default position.
    legend_offset_y : int
        Vertical offset of the legend layer from its default position.
    title_font_size : int
        Font size for the luminaire name.  Default 14.
    subtitle_font_size : int
        Font size for subtitle and Maximum lines.  Default 12.
    angle_label_font_size : int
        Font size for C-plane angle labels.  Default 11.
    ring_label_font_size : int
        Font size for concentric ring value labels (cd/m²).  Default 10.
    legend_title_font_size : int
        Font size for the legend title (γ [°]).  Default 11.
    legend_label_font_size : int
        Font size for legend tick labels.  Default 10.
    legend_bar_width : int
        Width of the gradient bar.  Default 16.
    legend_bar_height : int
        Height of the gradient bar.  Default 200.
    curve_stroke_width : float
        Stroke width of luminance curves.  Default 2.5.
    grid_stroke_width : float
        Stroke width of concentric rings.  Default 1.0.
    spoke_stroke_width : float
        Stroke width of spokes.  Default 0.8.
    grid_color : str
        Color for rings and spokes.  Default "#cccccc".
    outer_ring_color : str or None
        Color for the outermost concentric ring.  None falls back to
        ``grid_color``.  Default "#000000".
    threshold : float or None
        Threshold circle in cd/m².  Default 3000.0.  Pass None to disable.
    threshold_color : str
        Color for the threshold circle.  Default "#cc0000".
    threshold_stroke_width : float
        Stroke width of the threshold circle.  Default 1.8.
    threshold_dash : str
        SVG stroke-dasharray for the threshold circle.  Default "6,4".
    g_colors : dict or None
        Mapping gamma (float) -> hex color string.
    angle_label_gap : int
        Extra radial offset (px, can be negative) added to the angle labels
        distance formula.  Use negative values to bring labels closer to the
        circle.  Default -4.
    scale : float
        Rasterisation scale for PNG/JPG export.  Default 2.0.
    """

    _REF_R: int = 250

    def __init__(
        self,
        *,
        diagram_r: int = 250,
        padding: int = 10,
        title_area_height: int = 70,
        legend_area_width: int = 110,
        bottom_area_height: int = 35,
        left_area_width: int = 35,
        diagram_offset_x: int = 0,
        diagram_offset_y: int = 0,
        title_offset_x: int = 0,
        title_offset_y: int = 0,
        legend_offset_x: int = 0,
        legend_offset_y: int = 0,
        title_font_size: int = 14,
        subtitle_font_size: int = 12,
        angle_label_font_size: int = 11,
        ring_label_font_size: int = 10,
        legend_title_font_size: int = 11,
        legend_label_font_size: int = 10,
        legend_bar_width: int = 16,
        legend_bar_height: int = 200,
        curve_stroke_width: float = 2.5,
        grid_stroke_width: float = 1.0,
        spoke_stroke_width: float = 0.8,
        grid_color: str = "#cccccc",
        outer_ring_color: str | None = "#000000",
        threshold: float | None = 3000.0,
        threshold_color: str = "#cc0000",
        threshold_stroke_width: float = 1.8,
        threshold_dash: str = "6,4",
        g_colors: dict | None = None,
        angle_label_gap: int = -4,
        scale: float = 2.0,
    ):
        self.diagram_r = diagram_r
        self.padding = padding
        self.title_area_height = title_area_height
        self.legend_area_width = legend_area_width
        self.bottom_area_height = bottom_area_height
        self.left_area_width = left_area_width
        self.diagram_offset_x = diagram_offset_x
        self.diagram_offset_y = diagram_offset_y
        self.title_offset_x = title_offset_x
        self.title_offset_y = title_offset_y
        self.legend_offset_x = legend_offset_x
        self.legend_offset_y = legend_offset_y
        self.title_font_size = title_font_size
        self.subtitle_font_size = subtitle_font_size
        self.angle_label_font_size = angle_label_font_size
        self.ring_label_font_size = ring_label_font_size
        self.legend_title_font_size = legend_title_font_size
        self.legend_label_font_size = legend_label_font_size
        self.legend_bar_width = legend_bar_width
        self.legend_bar_height = legend_bar_height
        self.curve_stroke_width = curve_stroke_width
        self.grid_stroke_width = grid_stroke_width
        self.spoke_stroke_width = spoke_stroke_width
        self.grid_color = grid_color
        self.outer_ring_color = outer_ring_color
        self.threshold = threshold
        self.threshold_color = threshold_color
        self.threshold_stroke_width = threshold_stroke_width
        self.threshold_dash = threshold_dash
        self.g_colors = g_colors if g_colors is not None else dict(_G_COLORS)
        self.angle_label_gap = angle_label_gap
        self.scale = scale

    # ------------------------------------------------------------------
    # Computed canvas geometry
    # ------------------------------------------------------------------

    @property
    def canvas_width(self) -> int:
        return (
            self.padding
            + self.left_area_width
            + self.diagram_r * 2
            + self.legend_area_width
            + self.padding
        )

    @property
    def canvas_height(self) -> int:
        return (
            self.padding
            + self.title_area_height
            + self.diagram_r * 2
            + self.bottom_area_height
            + self.padding
        )

    @property
    def _default_cx(self) -> float:
        """Default X of circle centre in canvas space (before offset)."""
        return self.padding + self.left_area_width + self.diagram_r

    @property
    def _default_cy(self) -> float:
        """Default Y of circle centre in canvas space (before offset)."""
        return self.padding + self.title_area_height + self.diagram_r

    @property
    def circle_cx(self) -> float:
        """Effective X of circle centre in canvas space."""
        return self._default_cx + self.diagram_offset_x

    @property
    def circle_cy(self) -> float:
        """Effective Y of circle centre in canvas space."""
        return self._default_cy + self.diagram_offset_y

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------


    @classmethod
    def for_print(
        cls,
        width_cm: float,
        dpi: int = 300,
        font_scale: float = 1.0,
        **kwargs,
    ) -> "PolarStyle":
        """
        Create a PolarStyle sized for print/PDF output.

        Geometry parameters scale with ``k = width_px / 665``.  Font sizes
        scale with ``fk = k * font_scale``.  Legend area scales with ``k``
        only (not ``fk``) to avoid excessive white space when ``font_scale``
        is large.  The legend bar is automatically shifted right to clear the
        C=0° angle label.  ``scale`` is always 1.0: 1 SVG unit = 1 px.

        When ``font_scale > 1`` the canvas becomes wider than ``width_cm``
        because text areas (title, left, bottom) grow with ``fk``.

        Parameters
        ----------
        width_cm : float
            Target image width in centimetres.
        dpi : int, optional
            Output resolution in dots per inch.  Default 300 (print quality).
            Use 150 for screen/web, 300 for standard print, 600 for high-res.
        font_scale : float, optional
            Additional multiplier applied to all font sizes and text areas.
            Use this to match a specific point size in a target document.
            Example: ``font_scale=2.11`` gives Arial 9pt at 150 dpi.
        **kwargs
            Override any parameter after scaling (e.g. ``threshold=None``).
            Note: stroke-width parameters cannot be overridden via kwargs
            (they are set explicitly); adjust them on the returned object.

        Examples
        --------
        ::

            # 10 cm at 150 dpi, fonts equivalent to Arial 9pt
            style = PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11)

            # 8 cm at 300 dpi (~945 px) — standard datasheet
            style = PolarStyle.for_print(width_cm=8)

            # Disable threshold circle
            style = PolarStyle.for_print(width_cm=8, threshold=None)
        """
        # Target canvas width in pixels (scale=1.0 -> 1 SVG unit = 1 px)
        width_px = width_cm / 2.54 * dpi

        # Reference canvas width at k=1:
        #   padding + left_area + r*2 + legend_area + padding
        #   = 10 + 35 + 500 + 110 + 10 = 665
        REF_CANVAS_W = 10 + 35 + cls._REF_R * 2 + 110 + 10  # 665
        k = width_px / REF_CANVAS_W
        diagram_r = max(1, round(cls._REF_R * k))

        # fk combines geometry scale and font readability scale
        fk = k * font_scale

        # Legend area scales with k only — avoids giant white space when
        # font_scale > 1 (fonts grow but bar content width does not).
        legend_area = round(110 * k)

        # Auto-position legend to the right of the C=0° angle label.
        # C=0° label (text-anchor=start) is the rightmost: starts at label_r,
        # extends ~1x font_size to the right.  The 0.18 factor converts
        # legend_area into a gap from the circle edge to the legend bar.
        angle_font = round(11 * fk)
        label_right = diagram_r * 0.98 + angle_font - 4 + angle_font + 10
        legend_offset_x = max(0, round(label_right - (diagram_r + legend_area * 0.18)))

        return cls(
            diagram_r=diagram_r,
            padding=round(10 * k),
            # Text areas scale with fk (font size drives their height/width)
            title_area_height=round(70 * fk),
            legend_area_width=legend_area,
            bottom_area_height=round(35 * fk),
            left_area_width=round(35 * fk),
            title_font_size=round(14 * fk),
            subtitle_font_size=round(12 * fk),
            angle_label_font_size=angle_font,
            ring_label_font_size=round(10 * fk),
            legend_title_font_size=round(11 * fk),
            legend_label_font_size=round(10 * fk),
            legend_bar_width=round(16 * k),
            legend_bar_height=round(200 * k),
            # Stroke widths scale with k so physical pt size is constant
            # across dpi values.  Base values match ~1.2/0.5/0.4/0.9 pt.
            curve_stroke_width=round(2.5 * k, 2),
            grid_stroke_width=round(1.0 * k, 2),
            spoke_stroke_width=round(0.8 * k, 2),
            threshold_stroke_width=round(1.8 * k, 2),
            legend_offset_x=legend_offset_x,
            scale=1.0,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

class LuminancePlot:
    """
    Generate a polar luminance diagram from a LuminanceResult.

    Examples
    --------
    ::

        plot = LuminancePlot(result)
        plot.polar("output/polar.svg")
        plot.polar("output/polar.png")
        plot.polar("output/polar_small.png", style=PolarStyle.for_print(width_cm=6))
    """

    def __init__(self, result: LuminanceResult):
        self.result = result

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def polar(
        self,
        path: str | Path,
        g_angles: list[float] | None = None,
        style: PolarStyle | None = None,
        scale: float | None = None,
    ) -> None:
        """
        Export a polar luminance diagram.

        Parameters
        ----------
        path : str or Path
            Output file (.svg, .png, .jpg, .jpeg).
        g_angles : list of float, optional
            Gamma angles to draw.  Defaults to all angles in the result.
        style : PolarStyle, optional
            Visual style and layout.  Defaults to
            ``PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11)``
            (10 cm at 150 dpi, fonts equivalent to Arial 9pt).
        scale : float, optional
            Rasterisation scale override.  Defaults to style.scale.
        """
        if style is None:
            style = PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11)
        if g_angles is None:
            g_angles = list(self.result.g_axis)
        effective_scale = scale if scale is not None else style.scale
        svg = self._build_svg(g_angles, style)
        self._export(svg, Path(path), effective_scale)

    def polar_svg(
        self,
        g_angles: list[float] | None = None,
        style: PolarStyle | None = None,
    ) -> str:
        """
        Return a polar luminance diagram as an SVG string without writing to disk.

        Intended for inline HTML embedding.  Same rendering as :meth:`polar`
        with a ``.svg`` path, but no file I/O.

        Parameters
        ----------
        g_angles : list of float, optional
            Gamma angles to draw.  Defaults to all angles in the result.
        style : PolarStyle, optional
            Visual style and layout.  Defaults to
            ``PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11)``.

        Returns
        -------
        str
            SVG document as a string (starts with ``<svg``).
        """
        if style is None:
            style = PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11)
        if g_angles is None:
            g_angles = list(self.result.g_axis)
        return self._build_svg(g_angles, style)

    # ------------------------------------------------------------------
    # SVG builder
    # ------------------------------------------------------------------

    def _build_svg(self, g_angles: list[float], s: PolarStyle) -> str:
        r_max = self._round_scale_max(self.result.maximum)
        n_rings = 4
        ring_values = [round(r_max * i / n_rings) for i in range(1, n_rings + 1)]

        r  = s.diagram_r
        cx = s.circle_cx
        cy = s.circle_cy
        W  = s.canvas_width
        H  = s.canvas_height

        # Layer positions in canvas space
        # diagram : origin = circle centre
        diag_x = cx
        diag_y = cy
        # title : centred on circle centre, top = padding
        title_x = cx + s.title_offset_x
        title_y = s.padding + s.title_offset_y
        # legend : left edge just right of circle, top = circle top
        legend_x = cx + r + s.legend_area_width * 0.18 + s.legend_offset_x
        legend_y = cy - r + s.legend_offset_y

        parts: list[str] = []

        # SVG root
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'font-family="sans-serif">'
        )
        # White background
        parts.append(f'<rect width="{W}" height="{H}" fill="white"/>')

        # <defs> : gradient + clip-path (circle, origin = 0,0)
        parts.append(self._defs(g_angles, r, s))

        # --- diagram layer (origin = circle centre) ---
        parts.append(
            f'<g id="diagram" transform="translate({diag_x:.2f},{diag_y:.2f})">'
        )
        # grid (clipped)
        parts.append('<g id="grid" clip-path="url(#clip-diagram)">')
        parts.append(self._layer_grid(ring_values, r_max, r, s))
        parts.append('</g>')
        # curves (clipped)
        parts.append('<g id="curves" clip-path="url(#clip-diagram)">')
        parts.append(self._layer_curves(g_angles, r_max, r, s))
        parts.append('</g>')
        # ring labels (not clipped — sit just outside the circle)
        parts.append('<g id="ring-labels">')
        parts.append(self._layer_ring_labels(ring_values, r_max, r, s))
        parts.append('</g>')
        # angle labels (not clipped — sit well outside the circle)
        parts.append('<g id="angle-labels">')
        parts.append(self._layer_angle_labels(r, s))
        parts.append('</g>')
        parts.append('</g>  <!-- /diagram -->')

        # --- title layer ---
        parts.append(
            f'<g id="title" transform="translate({title_x:.2f},{title_y:.2f})">'
        )
        parts.append(self._layer_title(s))
        parts.append('</g>')

        # --- legend layer ---
        parts.append(
            f'<g id="legend" transform="translate({legend_x:.2f},{legend_y:.2f})">'
        )
        parts.append(self._layer_legend(g_angles, s))
        parts.append('</g>')

        parts.append('</svg>')
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # <defs>
    # ------------------------------------------------------------------

    def _defs(self, g_angles: list[float], r: int, s: PolarStyle) -> str:
        """<defs> block: gradient for legend + circular clip-path for diagram."""
        g_sorted = sorted(g_angles)
        n = len(g_sorted)

        # Gradient stops (bottom = smallest gamma = darkest)
        stops = []
        for i, g in enumerate(g_sorted):
            pct = round(100 * i / max(n - 1, 1))
            color = s.g_colors.get(g, "#333333")
            stops.append(f'    <stop offset="{pct}%" stop-color="{color}"/>')

        # Clip-path: circle of radius r centred at origin (diagram layer origin)
        return (
            "<defs>\n"
            '  <linearGradient id="lgLum" x1="0" y1="1" x2="0" y2="0"\n'
            '      gradientUnits="objectBoundingBox">\n'
            + "\n".join(stops) + "\n"
            "  </linearGradient>\n"
            f'  <clipPath id="clip-diagram">\n'
            f'    <circle cx="0" cy="0" r="{r}"/>\n'
            f'  </clipPath>\n'
            "</defs>"
        )

    # ------------------------------------------------------------------
    # Layer renderers  (all use origin = 0,0 = circle centre)
    # ------------------------------------------------------------------

    def _layer_grid(self, ring_values, r_max, r, s: PolarStyle) -> str:
        """Concentric rings and spokes."""
        parts: list[str] = []
        outer_color = s.outer_ring_color if s.outer_ring_color is not None else s.grid_color
        for rv in ring_values:
            ri = r * rv / r_max
            color = outer_color if rv == ring_values[-1] else s.grid_color
            parts.append(
                f'<circle cx="0" cy="0" r="{ri:.2f}" '
                f'fill="none" stroke="{color}" '
                f'stroke-width="{s.grid_stroke_width}"/>'
            )
        for c_deg in range(0, 360, 15):
            c_rad = math.radians(c_deg)
            x2 =  r * math.cos(c_rad)
            y2 = -r * math.sin(c_rad)
            parts.append(
                f'<line x1="0" y1="0" x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="{s.grid_color}" stroke-width="{s.spoke_stroke_width}"/>'
            )
        return "\n".join(parts)

    def _layer_curves(self, g_angles, r_max, r, s: PolarStyle) -> str:
        """Luminance polylines + threshold circle. Darkest gamma drawn last."""
        result = self.result
        parts: list[str] = []

        # Threshold circle
        if s.threshold is not None and 0 < s.threshold <= r_max:
            rt = r * s.threshold / r_max
            parts.append(
                f'<circle cx="0" cy="0" r="{rt:.2f}" '
                f'fill="none" stroke="{s.threshold_color}" '
                f'stroke-width="{s.threshold_stroke_width}" '
                f'stroke-dasharray="{s.threshold_dash}"/>'
            )

        # Luminance curves
        for g in sorted(g_angles, reverse=True):
            idx_g = int(np.argmin(np.abs(result.g_axis - g)))
            color = s.g_colors.get(float(result.g_axis[idx_g]), "#333333")
            points: list[str] = []
            for i, c in enumerate(result.c_axis):
                lum = result.table[i, idx_g]
                ri = r * float(lum) / r_max
                c_rad = math.radians(float(c))
                px =  ri * math.cos(c_rad)
                py = -ri * math.sin(c_rad)
                points.append(f"{px:.2f},{py:.2f}")
            points.append(points[0])  # close curve
            parts.append(
                f'<polyline points="{" ".join(points)}" '
                f'fill="none" stroke="{color}" '
                f'stroke-width="{s.curve_stroke_width}" '
                f'stroke-linejoin="round"/>'
            )
        return "\n".join(parts)

    def _layer_ring_labels(self, ring_values, r_max, r, s: PolarStyle) -> str:
        """cd/m² value labels on C=270° axis (bottom of circle, y = +ri)."""
        parts: list[str] = []
        for rv in ring_values:
            ri = r * rv / r_max
            parts.append(
                f'<text x="0" y="{ri:.2f}" '
                f'font-size="{s.ring_label_font_size}" fill="#888888" '
                f'text-anchor="middle" dominant-baseline="auto" '
                f'dy="-3">{int(rv)}</text>'
            )
        return "\n".join(parts)

    def _layer_angle_labels(self, r: int, s: PolarStyle) -> str:
        """C-plane angle labels around the outer ring."""
        label_r = r * 0.98 + s.angle_label_font_size + s.angle_label_gap
        parts: list[str] = []
        for c_deg in range(0, 360, 15):
            c_rad = math.radians(c_deg)
            cos_v = math.cos(c_rad)
            sin_v = math.sin(c_rad)
            lx =  label_r * cos_v
            ly = -label_r * sin_v
            if abs(cos_v) < 0.01:
                anchor = "middle"
            elif cos_v > 0:
                anchor = "start"
            else:
                anchor = "end"
            if abs(sin_v) < 0.01:
                baseline = "middle"
            elif sin_v > 0:
                baseline = "auto"
            else:
                baseline = "hanging"
            parts.append(
                f'<text x="{lx:.2f}" y="{ly:.2f}" '
                f'font-size="{s.angle_label_font_size}" fill="#444444" '
                f'text-anchor="{anchor}" dominant-baseline="{baseline}">'
                f'{c_deg}\u00b0</text>'
            )
        return "\n".join(parts)

    def _layer_title(self, s: PolarStyle) -> str:
        """Title block. x=0 is circle centre (inherited from translate)."""
        name = self.result.luminaire_name or "Luminance diagram"
        maximum = f"Maximum:\u00a0{self.result.maximum:.0f}\u00a0cd/m\u00b2"
        y1 = s.title_font_size
        y2 = y1 + s.title_font_size * 1.3
        y3 = y2 + s.subtitle_font_size * 1.3
        return (
            f'<text x="0" y="{y1:.1f}" font-size="{s.title_font_size}" '
            f'font-weight="bold" fill="#1a1a1a" '
            f'text-anchor="middle">{name}</text>\n'
            f'<text x="0" y="{y2:.1f}" font-size="{s.subtitle_font_size}" '
            f'fill="#555555" text-anchor="middle">'
            f'Polar luminance diagram</text>\n'
            f'<text x="0" y="{y3:.1f}" font-size="{s.subtitle_font_size}" '
            f'fill="#555555" text-anchor="middle" '
            f'font-style="italic">{maximum}</text>'
        )

    def _layer_legend(self, g_angles: list[float], s: PolarStyle) -> str:
        """Gradient legend bar. Origin = top-left of the bar."""
        g_sorted = sorted(g_angles)
        n = len(g_sorted)
        bw = s.legend_bar_width
        bh = s.legend_bar_height
        parts: list[str] = []

        # Title above bar
        parts.append(
            f'<text x="{bw / 2:.1f}" y="0" '
            f'font-size="{s.legend_title_font_size}" fill="#333333" '
            f'text-anchor="middle" dominant-baseline="auto" '
            f'dy="-{s.legend_title_font_size * 0.5:.1f}" '
            f'font-style="italic">\u03b3\u00a0[\u00b0]</text>'
        )
        # Gradient bar
        parts.append(
            f'<rect x="0" y="0" width="{bw}" height="{bh}" '
            f'fill="url(#lgLum)" stroke="{s.grid_color}" stroke-width="0.5"/>'
        )
        # Tick labels (top = largest gamma = lightest)
        for i, g in enumerate(reversed(g_sorted)):
            frac = i / max(n - 1, 1)
            ty = frac * bh
            parts.append(
                f'<text x="{bw + 4}" y="{ty:.2f}" '
                f'font-size="{s.legend_label_font_size}" fill="#333333" '
                f'dominant-baseline="middle">{int(g)}\u00b0</text>'
            )
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _round_scale_max(value: float) -> float:
        if value <= 0:
            return 1000.0
        if value > 1000:
            return float(math.ceil(value / 1000) * 1000)
        return float(math.ceil(value / 500) * 500)

    @staticmethod
    def _export(svg: str, path: Path, scale: float) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        suffix = path.suffix.lower()
        if suffix == ".svg":
            path.write_text(svg, encoding="utf-8")
            return
        if vlc is None:
            raise ImportError(
                "vl-convert-python is required for PNG/JPG export. "
                "Install it with: pip install vl-convert-python"
            )
        png_bytes = vlc.svg_to_png(svg, scale=scale)
        if suffix == ".png":
            path.write_bytes(png_bytes)
        elif suffix in (".jpg", ".jpeg"):
            if _PILImage is None:
                raise ImportError("Pillow is required for JPG export.")
            img = _PILImage.open(io.BytesIO(png_bytes)).convert("RGB")
            img.save(path, format="JPEG", quality=92, optimize=True)
        else:
            raise ValueError(
                f"Unsupported format '{suffix}'. Use .svg, .png, .jpg or .jpeg."
            )
