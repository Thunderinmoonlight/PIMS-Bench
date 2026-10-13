## BLNSPEC Table Structure

BLNSPEC defines blending specifications for blend pools. The table structure is:

| TEXT | [Blend Pool 1] | [Blend Pool 2] | ... |
|------|----------------|----------------|-----|
| XSUL | Sulfur, WT% | [spec value] | [spec value] | ... |

Valid blend pool codes:
- URGPOOL: Unleaded Regular pool
- UPRPOOL: Unleaded Premium pool  
- JETPOOL: Kero/Jet pool
- DSLPOOL: Diesel pool
- LSFPOOL: Low Sulfur Fuel Oil pool
- HSFPOOL: High Sulfur Fuel Oil pool

Example for sulfur spec on all pools:
TABLE | BLNSPEC
 | TEXT | URGPOOL | UPRPOOL | JETPOOL | DSLPOOL | LSFPOOL | HSFPOOL |
XSUL | Sulfur, WT% | 0.015 | 0.015 | 0.3 | 0.25 | 0.45 | 0.8 |
*