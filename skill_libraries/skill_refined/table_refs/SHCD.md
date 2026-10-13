# SHCD — Hydrocracker Submodel Sheet

## Purpose
The SHCD sheet defines hydrocracker yield coefficients.

## Key Structure Facts
- Column headers represent product streams or severity modes
- Row tags identify yield coefficient rows — verify via read_sheet
- Hydrocracker yields show conversion of heavy feed into middle distillates and lighter products
- Balance rows maintain mass conservation

## How to Modify
1. Call read_sheet("SHCD") first to see exact layout
2. Use the exact row tags and column headers from the sheet
3. Write one CASE row per modification, matching sheet structure
