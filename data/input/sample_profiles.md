# Sample profiles — LDT test files

| Sample    | ISYM | Symmetry      | Shape       | Geometry (lum. area) | Heights h_lum (mm)           | Flux (lm) | Lamp sets | mc (C-planes) | ng (γ angles) | Resolution γ | Interpolation | Luminaire name |
| --------- | ---- | ------------- | ----------- | -------------------- | ---------------------------- | --------- | --------- | ------------- | ------------- | ------------ | ------------- | -------------- |
| sample_01 | 1    | full symmetry | circular    | D=530mm              | C0=59 C90=59 C180=59 C270=59 | 4828      | 1         | 24            | 37            | 5.0°         | no            | sample_01      |
| sample_02 | 2    | C0-C180       | rectangular | 1201×38mm            | —                            | 2112      | 1         | 24            | 37            | 5.0°         | no            | sample_02      |
| sample_03 | 3    | C90-C270      | circular    | D=350mm              | C0=50 C90=50 C180=50 C270=50 | 609       | 1         | 24            | 37            | 5.0°         | no            | sample_03      |
| sample_04 | 4    | quadrant      | rectangular | 1480×63mm            | —                            | 12334     | 1         | 24            | 37            | 5.0°         | no            | sample_04      |
| sample_05 | 0    | asymmetric    | rectangular | 245×250mm            | —                            | 9639      | 1         | 24            | 37            | 5.0°         | no            | sample_05      |
| sample_06 | 4    | quadrant      | rectangular | 1208×105mm           | C0=51 C90=0 C180=51 C270=0   | 1983      | 2         | 144           | 73            | 2.5°         | **yes**       | sample_06      |
| sample_07 | 3    | C90-C270      | rectangular | 104×240mm            | —                            | 1800      | 1         | 144           | 73            | 2.5°         | **yes**       | sample_07      |
| sample_08 | 3    | C90-C270      | rectangular | 560×390mm            | —                            | 8460      | 1         | 24            | 37            | 5.0°         | no            | sample_08      |
| sample_09 | 4    | quadrant      | rectangular | 630×400mm            | C0=8 C90=8 C180=8 C270=8     | 11316     | 1         | 24            | 37            | 5.0°         | no            | sample_09      |
| sample_10 | 2    | C0-C180       | rectangular | 1500×37mm            | —                            | 3450      | 1         | 24            | 37            | 5.0°         | no            | sample_10      |

## Notes

- **ISYM** : EULUMDAT symmetry code — 0 = raw, 1 = full, 2 = C0/C180, 3 = C90/C270, 4 = quadrant
- **mc / ng** : number of C-planes / γ angles in the native LDT file (before eulumdat-py expansion)
- **Lamp sets** : number of alternative lamp configurations — only the first set is used for luminance calculation (Relux/DIALux behaviour)
- **Interpolation** : bilinear interpolation applied when native γ resolution (2.5°) does not match the UGR grid (5° step)
- sample_06 has 2 lamp sets — first set flux = 1983 lm is used
