# SCCU — FCC Submodel Sheet

## Purpose
The SCCU sheet defines FCC cracking yield coefficients.

## Key Structure Facts
- Column headers are conversion percentages or product codes (e.g., 760, 975, GASO, DIES)
- Row tags identify feed/product streams — always verify exact tags via read_sheet
- FCC yields typically show how feed converts to gasoline, diesel, and other products
- Balance rows ensure total yields sum correctly

## How to Modify
1. Call read_sheet("SCCU") to discover the actual column and row layout
2. Use exact column headers from the sheet as column names in your CASE
3. Use exact row tags from the sheet as row identifiers in your CASE
4. Write one CASE row per sheet row you're modifying

## Common Scenario Patterns
- "Adjust FCC yield chain" -> identify which rows control gasoline/diesel yields from read_sheet
- "Diagnose yield issue" -> read multiple related rows to understand the yield structure
- "FCC conversion" -> may also need PROCLIM table for conversion limits
