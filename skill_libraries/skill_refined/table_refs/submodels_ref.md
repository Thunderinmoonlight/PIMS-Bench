# Submodel Sheets — Yield Structure Modification

Each process unit has a submodel sheet (S + unit code). When a task mentions yield changes, product slate adjustments, or unit efficiency, modify the submodel sheet.

## Sheet Naming

| CAPS Tag | Submodel Sheet |
|----------|---------------|
| CDLC | SDLC (Delayed Coker) |
| CLPR | SLPR (Reformer) |
| CCCU | SCCU (FCC) |
| CDHT | SDHT (Dist Hydrotreater) |
| CKHT | SKHT (Kero Hydrotreater) |
| CHCD | SHCD (Hydrocracker) |

## Three Yield Modification Patterns

### Pattern A: BAS column (most common)

Used by SDLC, SDHT. Column header is `BAS` (base case adjustment). Row tags are `WBAL*` (yield balance rows).

```
TABLE | SDLC
 | TEXT | BAS |
WBALDCD | WBALDCD | -0.22 |
WBALCOK | WBALCOK | -0.2676 |
*
```

Row tag meanings for coker (SDLC):
- WBALDCD = coker distillate yield adjustment
- WBALCOK = petroleum coke yield adjustment

Row tag meanings for DHT (SDHT):
- WBALHTD = hydrotreated distillate yield adjustment
- WBALLOS = yield loss adjustment

### Pattern B: Numeric operating point column

Used by SCCU. Column header is a numeric operating point (e.g., `975` = aniline point). Row tags are `WBAL*`.

```
TABLE | SCCU
 | TEXT | 975 |
WBALLC1 | WBALLC1 | -0.42 |
WBALCCD | WBALCCD | -0.154 |
*
```

Row tag meanings for FCC (SCCU):
- WBALLC1 = light cycle oil yield
- WBALCCD = clarified oil yield

**Important**: Read the SCCU sheet first to find the actual numeric column headers.

### Pattern C: WBAL* as column headers (diagonal matrix)

Used by SLPR (reformer). **Ignore the sheet's header row** — the WBAL* row tags are used as BOTH row tags AND column headers.

**How to determine the structure:**
1. Read the submodel sheet to find WBAL* row tags (e.g., WBALR90, WBALR94, WBALR98)
2. Use those same WBAL* tags as column headers in your CASE entry
3. Place values on the diagonal (row WBALR90 -> column WBALR90)
4. Leave non-diagonal cells empty

```
TABLE | SLPR
 | TEXT | WBALR90 | WBALR94 | WBALR98 |
WBALR90 | WBALR90 | -0.9117 |  |  |
WBALR94 | WBALR94 |  | -0.8939 |  |
WBALR98 | WBALR98 |  |  | -0.8717 |
*
```

**Do NOT use the sheet's header row** (e.g., "HTD HSRN") as column names. Always use the WBAL* row tags as column headers for Pattern C.

## Key Rules

1. **Only write the columns you are changing** — do not copy all columns from the sheet
2. **WBAL* values are adjustments (deltas)**, not absolute values. Negative = reduce yield, positive = increase.
3. **Always read_sheet() first** to find the exact row tags and column headers
4. **Typical adjustment magnitude**: 0.01 to 1.0 (representing percentage point changes)

## GC vs WS Model Differences

- **GC model has more submodel rows** than WS (often 7 rows vs 5). Always read the sheet to discover all rows.
- **Row tags differ between models**: WS may have `WBALDCD`, GC may have additional rows for different products.
- **Never guess row tags from memory** — always copy EXACTLY from read_sheet() output.
- **Count the rows**: After read_sheet(), count all WBAL* rows. Your CASE should include ALL rows that need modification — missing one row will reduce the match score.

## Common Submodel Errors to Avoid

1. **Using a single column for Pattern C (SLPR)**: SLPR needs MULTIPLE WBAL* columns (WBALR90, WBALR94, WBALR98), not just one.
2. **Generic row tags**: `WBAL1`, `WBAL2` are NOT valid — use specific tags like `WBALDCD`, `WBALLC1`.
3. **Using the sheet header as column name**: The header "HTD HSRN" on SLPR is NOT a column name — use WBAL* tags instead (Pattern C).
4. **Mixing up units**: CDLC->SDLC, CCCU->SCCU, CLPR->SLPR — verify the CAPS tag maps to the correct submodel sheet.
