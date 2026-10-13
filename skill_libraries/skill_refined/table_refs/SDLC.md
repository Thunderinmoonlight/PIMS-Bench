# SDLC — Delayed Coker Submodel Sheet

## Purpose
The SDLC sheet defines coker yield coefficients.

## Key Structure Facts
- Column headers represent product streams or operating modes
- Row tags identify individual yield coefficients — verify via read_sheet
- Coker yields show conversion of heavy feed into lighter products and coke
- Material balance rows maintain mass conservation

## How to Modify
1. Call read_sheet("SDLC") first to see exact layout
2. Use the exact row tags and column headers from the sheet
3. Write one CASE row per modification, matching sheet structure
