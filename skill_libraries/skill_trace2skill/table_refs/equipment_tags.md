# Equipment Row Tags (CAPS Table)

## Common Equipment Codes

| Equipment | Row Tag | Description |
|-----------|---------|-------------|
| Crude Unit #1 | Cat1 | CDU-1 capacity |
| Crude Unit #2 | Cat2 | CDU-2 capacity |
| Vacuum Unit #1 | CVU1 | Vacuum distillation |
| Vacuum Unit #2 | CVU2 | Vacuum distillation |
| FCC (Cat Cracker) | CCCU | Fluid catalytic cracker |
| Delayed Coker | CDLC | Coker capacity |
| Low-P Reformer | CLPR | Catalytic reformer |
| Dist Hydrotreater | CDHT | Distillate hydrotreating |
| Kero Hydrotreater | CKHT | Kerosene hydrotreating |
| Hydrocracker | CHCD | Hydrocracker distillate |
| Scanfiner | CGTU | Tail gas treatment unit |
| C4 Isom | CIS4 | C4 isomerization |
| Sulf Acid Alky | CSFA | Alkylation |
| H2 Plant | CHYD | Hydrogen plant |

## Submodel Sheet Naming

| Equipment | CAPS Tag | Submodel Sheet |
|-----------|----------|---------------|
| Delayed Coker | CDLC | SDLC |
| FCC | CCCU | SCCU |
| Reformer | CLPR | SLPR |
| Dist Hydrotreater | CDHT | SDHT |
| Hydrocracker | CHCD | SHCD |
| Scanfiner | CGTU | STGT |

## Common Mistakes

- CGTU ≠ CTGT — Scanfiner is **CGTU** (not CTGT)
- CCCU ≠ CCC — FCC is **CCCU**
- CDLC ≠ CDC — Coker is **CDLC**
- CLPR ≠ CRF — Reformer is **CLPR**
