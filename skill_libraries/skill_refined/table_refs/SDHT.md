# SDHT — Distillate Hydrotreater Submodel Sheet

## Purpose
The SDHT sheet defines DHT yield coefficients and material balance rows.

## Key Structure Facts
- Columns represent balance components or product yields (e.g., BAS, NSPG, XSUL)
- Row tags follow naming conventions specific to the DHT unit — read_sheet to discover exact tags
- Material balance rows often have a recognizable prefix pattern — look for rows that span multiple columns
- Some rows control individual product yields, others control balance/loss terms

## CRITICAL: Copy Row Tags Exactly
When modifying SDHT, you MUST copy row tags EXACTLY as shown in read_sheet output:
- If the sheet shows "WBALHTD" -> use "WBALHTD", not "BAS" or "HTD"
- If the sheet shows "WBALLOS" -> use "WBALLOS", not "LOSS" or "BAL"
- Each distinct row in the sheet needs its own CASE entry row

Example — if read_sheet shows two balance rows:
```
TABLE | SDHT
 | TEXT | BAS |
WBALHTD | WBALHTD | -0.99 |
WBALLOS | WBALLOS | 0.008473 |
*
```
NOT this (wrong row tags, merged rows):
```
TABLE | SDHT
 | BAS | BAS2 |
BAS | -0.99 | 0.008473 |
*
```

## How to Modify
1. Call read_sheet("SDHT") to see actual row tags and column names
2. Match your CASE entry row tags EXACTLY to what appears in the sheet
3. Include the TEXT column (second column) with value = row tag
4. If adjusting balance terms, include all relevant balance rows as separate entries
5. Keep the row-per-modification pattern: one CASE row per sheet row you're changing

## Common Scenario Patterns
- "Reduce yield loss" -> find the loss/balance row, adjust the coefficient
- "Set balance to X" -> find the specific balance row tag from read_sheet output
- "Force throughput" -> this goes in CAPS table, not SDHT
