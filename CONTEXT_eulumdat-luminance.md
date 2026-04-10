# CONTEXT — eulumdat-luminance

## Statut
- Package publié sur PyPI : https://pypi.org/project/eulumdat-luminance/
- Version actuelle : `1.3.0` (stable, publié)
- Repo GitHub : https://github.com/123VincentB/eulumdat-luminance
- Environnement virtuel : `eulumdat-luminance/.venv/`
- Tests : **211/211 passés** sur 10 fichiers LDT samples (sample_01 à sample_10)

## Description
Extension de `eulumdat-py` pour le calcul de tables de luminances (cd/m²) à partir
de fichiers EULUMDAT (.ldt). Produit des diagrammes polaires de luminance et des
exports CSV/JSON. Prérequis à `eulumdat-ugr`.

## Écosystème eulumdat-*
| Package              | Rôle                               | Statut     |
|----------------------|------------------------------------|------------|
| `eulumdat-py`        | Lecture/écriture LDT               | v1.0.0 ✓  |
| `eulumdat-symmetry`  | Symétrisation, auto-détection ISYM | v1.0.0 ✓  |
| `eulumdat-plot`      | Diagrammes polaires d'intensité    | v1.0.2 ✓  |
| `eulumdat-luminance` | Calcul luminances, diagramme pol.  | v1.3.0 ✓  |
| `eulumdat-ugr`       | Calcul UGR (CIE 117/190)           | non débuté |

## Dépendances
```
eulumdat-py >= 1.0.0   # module importable : pyldt  (pas eulumdat_py !)
numpy >= 1.24.0
scipy >= 1.10.0        # RegularGridInterpolator pour interpolation UGR + at()
vl-convert-python >= 1.0.0  # rastérisation SVG -> PNG/JPG
Pillow >= 10.0.0       # conversion PNG -> JPG
```

## Structure du projet
```
eulumdat-luminance/
├── data/
│   ├── input/              # sample_01.ldt ... sample_10.ldt (+ 10 autres)
│   ├── output/             # résultats de tests (ignoré par git)
│   └── reference/
│       └── relux_reference.json   # valeurs de référence Relux (10 samples)
├── examples/
│   ├── 01_basic_usage.md          # usage de base + for_print()
│   └── polar_sample04_word.png    # image de référence (10cm, 150dpi, font_scale=2.11)
├── src/eulumdat_luminance/
│   ├── __init__.py
│   ├── calculator.py       # LuminanceCalculator
│   ├── result.py           # LuminanceResult (+ at())
│   └── plot.py             # LuminancePlot + PolarStyle
├── tests/
│   ├── test_calculator.py
│   └── test_polar_diagram.py  # validation visuelle diagramme polaire
├── .gitignore
├── pyproject.toml
└── README.md
```

## API publique

### LuminanceCalculator
```python
from pyldt import LdtReader
from eulumdat_luminance import LuminanceCalculator

ldt = LdtReader.read("file.ldt")
result = LuminanceCalculator.compute(ldt, full=False)  # full=True = grille native
```

### LuminanceResult
```python
result.table          # np.ndarray (n_c, n_g), cd/m2
result.c_axis         # np.ndarray, degrés
result.g_axis         # np.ndarray, degrés
result.maximum        # float, cd/m2
result.full           # bool
result.luminaire_name # str

result.to_csv("output.csv")
result.to_json("output.json")

# Interpolation bilinéaire à des angles arbitraires (utile pour eulumdat-ugr)
lum = result.at(c_deg=12.0, g_deg=67.0)          # scalaire -> float
lums = result.at(c_deg=np.array([0., 12., 90.]),  # tableau -> np.ndarray
                 g_deg=np.array([65., 67., 75.]))

# Aire projetée de la surface lumineuse (m²) vue depuis (C, γ) — v1.2.0
area = result.projected_area(c_deg=0.0, g_deg=65.0)   # scalaire -> float
areas = result.projected_area(c_deg=np.array([0., 90.]),   # tableau -> np.ndarray
                               g_deg=np.array([65., 75.]))
```

### LuminancePlot + PolarStyle
```python
from eulumdat_luminance import LuminancePlot, PolarStyle

plot = LuminancePlot(result)

# Style par défaut = PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11)
# → 10 cm à 150 dpi, fontes équivalentes à Arial 9pt
plot.polar("output.svg")
plot.polar("output.png")
plot.polar("output.jpg")

# Style print/PDF — taille réelle en cm + dpi
# Référence recommandée : 10cm, 150dpi, font_scale=2.11 (Arial 9pt équiv.)
plot.polar("output.png", style=PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11))
plot.polar("output.png", style=PolarStyle.for_print(width_cm=8, dpi=300, font_scale=2.6))

# Sélection des angles gamma
plot.polar("output.png", g_angles=[65.0, 85.0])

# Formats supportés : .svg, .png, .jpg/.jpeg
```

## Décisions de conception — LuminancePlot

### Diagramme de Söllner abandonné
Le diagramme de Söllner (axe Y = gamma, axe X = luminance log, une courbe par
plan C) a été implémenté puis abandonné. Raison : il n'expose que 4 plans C
(C0/C90/C180/C270) alors que le diagramme polaire montre tous les 24 plans
simultanément, ce qui est plus intuitif et informatif pour l'évaluation de
l'éblouissement. Le fichier `plot.py` ne contient plus aucun code Söllner.

### SVG pur (pas Vega-Lite)
Le rendu est en SVG pur (pas de Vega-Lite). Vega-Lite avait été utilisé
initialement mais abandonné car :
- La légende (gradient, taille de barre) n'était pas contrôlable proprement
- `for_print()` / `font_scale` étaient impossibles à implémenter correctement
- Le layout était opaque (pas de contrôle sur les zones de réservation)

`vl-convert-python` est conservé uniquement pour la rastérisation via
`vlc.svg_to_png(svg_string, scale=scale)`.

### Architecture SVG en couches
Le SVG généré utilise des groupes `<g transform="translate(x,y)">` :

```
<svg>  (main — canvas_width × canvas_height)
  <rect fill="white"/>
  <defs>
    <linearGradient id="lgLum"/>       palette bleue pour la légende
    <clipPath id="clip-diagram">       cercle de rayon diagram_r
      <circle cx="0" cy="0" r="..."/>
    </clipPath>
  </defs>
  <g id="diagram" transform="translate(cx, cy)">
    <g id="grid"          clip-path="url(#clip-diagram)">  anneaux + rayons
    <g id="curves"        clip-path="url(#clip-diagram)">  courbes + seuil rouge
    <g id="ring-labels">                                   cd/m², non clippé
    <g id="angle-labels">                                  0°…345°, non clippé
  <g id="title"  transform="translate(tx, ty)">
  <g id="legend" transform="translate(lx, ly)">
</svg>
```

- `grid` et `curves` sont clippés au cercle → ne débordent jamais dans le padding
- `ring-labels` et `angle-labels` sont hors clip → peuvent dépasser le cercle
- Chaque couche travaille en coordonnées locales avec `(0,0)` = centre du cercle

### Convention angulaire
Convention trigonométrique standard :
- C=0° à droite, C=90° en haut, C=180° à gauche, C=270° en bas
- Sens antihoraire
- Formule : `x = r·cos(c)`, `y = -r·sin(c)` (axe Y SVG inversé)

### PolarStyle
Classe de configuration avec tous les paramètres visuels et de layout.
Paramètres clés :
- `diagram_r` : rayon du cercle polaire en unités SVG (défaut 250)
- `padding` : bord uniforme autour du canvas (défaut 10)
- `title_area_height`, `legend_area_width`, `bottom_area_height`, `left_area_width` :
  zones de réservation pour le texte autour du cercle
- `diagram_offset_x/y`, `title_offset_x/y`, `legend_offset_x/y` :
  fine-tuning de position de chaque couche par rapport à sa position par défaut
- `threshold` : cercle rouge pointillé (défaut 3000 cd/m²), None pour désactiver
- `outer_ring_color` : couleur du cercle concentrique externe (défaut `"#000000"`)
- `angle_label_gap` : offset radial des labels angulaires en px, négatif = plus proche
  du cercle (défaut `-4`)
- `curve_stroke_width` : épaisseur des courbes (défaut 2.5)
- `grid_stroke_width` : épaisseur des anneaux (défaut 1.0)
- `spoke_stroke_width` : épaisseur des rayons (défaut 0.8)
- `threshold_stroke_width` : épaisseur du cercle seuil (défaut 1.8)
- `scale` : facteur de rastérisation PNG (défaut 2.0)

### PolarStyle.for_print()
Méthode factory principale. Calcule `diagram_r` depuis `width_cm` + `dpi` :

```python
width_px = width_cm / 2.54 * dpi      # taille cible en pixels
k = width_px / 665                     # 665 = canvas de référence à r=250
diagram_r = round(250 * k)
fk = k * font_scale                    # fk scale les fontes ET les zones de texte
scale = 1.0                            # toujours — pas de doublement retina
```

`font_scale` (défaut 1.0) multiplie toutes les fontes ET les zones de réservation
de texte (`title_area_height`, `left_area_width`, `bottom_area_height`) sans changer
les dimensions du diagramme lui-même (rayon, strokes, barre de légende).

**Important** : `legend_area_width` scale avec `k` uniquement (pas `fk`) pour éviter
un espace blanc excessif à droite quand `font_scale > 1`. La position de la légende
(`legend_offset_x`) est calculée automatiquement pour dégager le label angulaire C=0°.

Valeurs de référence à 150 dpi :
| `width_cm` | pixels | `diagram_r` |
|---|---|---|
| 8  | ~472  | 177 |
| 10 | ~591  | 222 |
| 12 | ~709  | 266 |

Valeurs de référence à 300 dpi :
| `width_cm` | pixels | `diagram_r` |
|---|---|---|
| 6  | ~709  | 266 |
| 8  | ~945  | 355 |
| 12 | ~1417 | 533 |
| 16 | ~1890 | 710 |

Formule `font_scale` pour correspondre à un corps de fonte cible :
```
font_scale = (pt_size * dpi / 72) / (10 * k)
```
Exemples :
- Arial 9pt à 150dpi : `font_scale = (9 * 150 / 72) / (10 * k_10cm) ≈ 2.11`
- Arial 10pt à 300dpi : `font_scale ≈ 2.6`

Avec `font_scale > 1`, le canvas devient plus large que `width_cm` car les zones
de texte s'agrandissent.

## LuminanceResult.at() — interpolation à angle arbitraire

Permet de calculer la luminance en (C, γ) quelconques, utile pour `eulumdat-ugr`.

Implémentation :
- Interpolateur `scipy.RegularGridInterpolator` (bilinéaire), construit à la
  première utilisation et mis en cache (`_interpolator`).
- L'axe C est étendu à 360° (copie de la ligne C=0°) avant construction, ce qui
  permet l'interpolation correcte entre 345° et 360°.
- Pour la meilleure précision, utiliser `full=True` (grille native LDT).

```python
result = LuminanceCalculator.compute(ldt, full=True)

# Scalaire -> float
lum = result.at(c_deg=12.0, g_deg=67.0)

# Vectorisé -> np.ndarray
lums = result.at(
    c_deg=np.array([0.0, 12.0, 90.0]),
    g_deg=np.array([65.0, 67.0, 75.0]),
)
```

## Modèle physique (LuminanceCalculator)

### Formule générale
```
L(C, gamma) = I(C, gamma) / A_proj(C, gamma)
```

### Intensité en cd
```
I = intensities [cd/klm] x flux_klm
flux_klm = num_lamps[0] x lamp_flux[0] / 1000   <- PREMIER SET UNIQUEMENT
```
- `ldt.intensities` : matrice cd/klm, déjà étendue à la plage complète par eulumdat-py
- `ldt.header.lamp_flux` : lm par lampe (liste, un élément par set)
- `ldt.header.num_lamps` : nombre de lampes par set
- **IMPORTANT** : les LDT peuvent avoir plusieurs sets de lampes (configurations
  alternatives). Seul le premier set est utilisé pour le calcul, conformément à la
  spec EULUMDAT et au comportement de Relux/DIALux.

### Aire projetée
```
A_proj(C, gamma) = A_bottom x cos(gamma) + A_side(C) x sin(gamma)
```
- Luminaire rectangulaire : `A_bottom = length x width`
- Luminaire circulaire (`width_lum_area == 0`) : `A_bottom = pi x (length/2)²`
- `A_side(C)` = combinaison projetée des hauteurs latérales selon le quart de plan

### Mapping des hauteurs par quadrant
| Quadrant | C           | h_l   | h_w   |
|----------|-------------|-------|-------|
| Q0       | 0-90 deg    | C0    | C90   |
| Q1       | 90-180 deg  | C180  | C90   |
| Q2       | 180-270 deg | C180  | C270  |
| Q3       | 270-360 deg | C0    | C270  |

Attributs pyldt : `h.h_lum_c0`, `h.h_lum_c90`, `h.h_lum_c180`, `h.h_lum_c270` (mm)

### Cas dégénérés
- Toutes hauteurs = 0 (luminaire plat/encastré) : `A_side = 0`, pas de division
  par zéro car gamma=90 n'est pas dans la grille UGR (max 85 deg)
- `A_proj == 0` : luminance mise à 0 (`np.where` safe division)

## Grille UGR (CIE 117 / CIE 190)
```
C : 0, 15, 30, ..., 345 deg  ->  24 plans
gamma : 65, 70, 75, 80, 85 deg  ->  5 angles
```
Interpolation bilinéaire via `scipy.interpolate.RegularGridInterpolator`
si la résolution native du LDT ne correspond pas exactement (ex: sample_06/07 à 2.5 deg).

## API pyldt — points d'attention
Le module s'importe `from pyldt import LdtReader` (pas `eulumdat_py`).
```python
ldt = LdtReader.read("file.ldt")
h = ldt.header

h.luminaire_name          # str
h.mc, h.dc                # int, float — nombre et pas des plans C
h.ng, h.dg                # int, float — nombre et pas des angles gamma
h.length_lum_area         # float, mm
h.width_lum_area          # float, mm  (0 = circulaire)
h.h_lum_c0/c90/c180/c270 # float, mm
h.lamp_flux               # List[float], lm par lampe
h.num_lamps               # List[int]
h.c_angles                # List[float], degrés
h.g_angles                # List[float], degrés

ldt.intensities           # List[List[float]], cd/klm, shape [mc x ng]
                          # toujours étendu à la plage complète (ISYM géré)
```

## Profil des 10 samples de référence
| Sample | ISYM | Symétrie       | Forme      | Géométrie (surf. lum.) | Hauteurs h_lum            | Flux (lm) | Résol. gamma | Interp. |
|--------|------|----------------|------------|------------------------|---------------------------|-----------|--------------|---------|
| 01     | 1    | full symmetry  | circulaire | D=530mm                | C0=C90=C180=C270=59mm     | 4828      | 5 deg        | non     |
| 02     | 2    | C0-C180        | rect.      | 1201x38mm              | —                         | 2112      | 5 deg        | non     |
| 03     | 3    | C90-C270       | circulaire | D=350mm                | C0=C90=C180=C270=50mm     | 609       | 5 deg        | non     |
| 04     | 4    | quadrant       | rect.      | 1480x63mm              | —                         | 12334     | 5 deg        | non     |
| 05     | 0    | asymétrique    | rect.      | 245x250mm              | —                         | 9639      | 5 deg        | non     |
| 06     | 4    | quadrant       | rect.      | 1208x105mm             | C0=C180=51mm, C90=C270=0  | 1983      | 2.5 deg      | **oui** |
| 07     | 3    | C90-C270       | rect.      | 104x240mm              | —                         | 1800      | 2.5 deg      | **oui** |
| 08     | 3    | C90-C270       | rect.      | 560x390mm              | —                         | 8460      | 5 deg        | non     |
| 09     | 4    | quadrant       | rect.      | 630x400mm              | C0=C90=C180=C270=8mm      | 11316     | 5 deg        | non     |
| 10     | 2    | C0-C180        | rect.      | 1500x37mm              | —                         | 3450      | 5 deg        | non     |

## Validation Relux (data/reference/relux_reference.json)
- **10/10 samples validés** contre Relux Desktop (rapport du 2026-03-23)
- Tolérance : relative 3% pour valeurs > 10 cd/m2, absolue 10 cd/m2 sinon
- Écarts typiques : < 0.3% (majorité), < 2.5% (sample_03, arrondi Relux)
- Note sample_06 : deux sets de lampes -> seul le premier (1983 lm) est utilisé

## Validation visuelle du diagramme polaire (2026-03-26)
- **10/10 samples validés** visuellement via `tests/test_polar_diagram.py`
- Style de référence : `PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11)`
- Convention angulaire confirmée : C=0° à droite, C=90° en haut, sens antihoraire
- Cercle seuil rouge pointillé à 3000 cd/m² : fonctionnel et visible
- Cercle concentrique externe en noir (`outer_ring_color="#000000"`)
- Légende dégradé bleu (65° foncé → 85° clair) : correcte
- Labels angulaires (0°…345° par pas de 15°) : positionnement correct avec `angle_label_gap=-4`
- Labels concentriques cd/m² sur axe C=270° (bas) : au-dessus des cercles
- Image de référence Word : `examples/polar_sample04_word.png`

## Tests
```bash
pytest                                  # tous les tests (201)
pytest tests/test_calculator.py        # 181 tests numériques
pytest tests/test_polar_diagram.py     # 20 tests visuels (génération PNG/SVG)
pytest tests/test_polar_diagram.py -v -s -k "svg"
pytest tests/test_polar_diagram.py -v -s -k "png"
pytest -k Relux                        # validation Relux uniquement (30 tests)
pytest -k sample_04
pytest -k "not Smoke"
```

### Organisation des tests (test_calculator.py — 181 tests)
| Classe                              | Type                  | Nb  | Fichiers LDT |
|-------------------------------------|-----------------------|-----|--------------|
| `TestLuminanceResult`               | Unitaire              | 7   | Aucun        |
| `TestLuminanceResultAt`             | Unitaire interpolation| 8   | sample_04    |
| `TestProjectedArea`                 | Unitaire géom.        | 7   | Aucun        |
| `TestAllSamples` (parametrize)      | Invariants structurels| 120 | sample_01–10 |
| `TestSample04`                      | Spot-checks numériques| 6   | sample_04    |
| `TestLuminancePlotSmoke`            | Smoke export          | 3   | Aucun        |
| `TestReluxValidation` (parametrize) | Validation Relux      | 30  | sample_01–10 |

### Organisation des tests (test_polar_diagram.py — 20 tests)
| Fonction                | Type      | Nb  | Description |
|-------------------------|-----------|-----|-------------|
| `test_polar_svg`        | Smoke SVG | 10  | sample_01–10, `PolarStyle.for_print(10cm, 150dpi, font_scale=2.11)` |
| `test_polar_png`        | Smoke PNG | 10  | sample_01–10, idem — asserte `w == style.canvas_width` |

## Historique des versions
| Version | Date       | Changements |
|---------|------------|-------------|
| 1.3.1   | 2026-04-10 | `LuminancePlot.polar_svg()` — retourne le SVG sous forme de string sans écriture disque (pour embedding HTML inline) |
| 1.3.0   | 2026-04-09 | Style par défaut de `LuminancePlot.polar()` changé : `PolarStyle()` → `PolarStyle.for_print(width_cm=10, dpi=150, font_scale=2.11)` |
| 1.2.0   | 2026-03-30 | `LuminanceResult.projected_area()` — expose l'aire projetée pour eulumdat-ugr |
| 1.1.1   | 2026-03-26 | Fix URL image README (relative → absolue pour PyPI) |
| 1.1.0   | 2026-03-26 | `LuminanceResult.at()`, nouveaux défauts PolarStyle, `for_print()` amélioré, `test_polar_diagram.py`, image de référence |
| 1.0.1   | 2026-03-24 | Badges, image exemple dans README |
| 1.0.0   | 2026-03-23 | Première version stable, 266/266 tests |

## Roadmap v1.3 (future)
- `font_scale` automatique basé sur `pt_size` + `dpi` (pas de magic number)
- Option pour forcer le canvas à exactement `width_cm` même avec `font_scale > 1`
  (réduire `diagram_r` en compensation)
- Zenodo : mise à jour DOI si changements majeurs
