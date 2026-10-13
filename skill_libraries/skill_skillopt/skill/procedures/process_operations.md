# Procedure: Process Parameter Changes

## When to use
Task mentions: severity, RON, conversion, process parameter, PROCLIM

## Steps
1. **MANDATORY**: `read_sheet("PROCLIM")` first to see actual column headers
2. Identify: Which process parameter? (ZSEV, ZCON, etc.)
3. Common parameters:
   - ZSEV: Reformer severity (RON 90-110 range)
   - ZCON: FCC conversion (70-98 range)
4. Write CASE using the NUMERIC column headers from the sheet
5. Check dep_map for CAPS and SELL dependencies

## CRITICAL: PROCLIM column headers are NUMBERS, not MIN/MAX

The PROCLIM sheet has numeric column headers (e.g., `90.0`, `100.0`):
```
ZSEV | Reformer Severity | 90.0 | 100.0
ZCON | FCC Conversion    | 70.0 |  73.0
```

## Templates

**Process parameter change** (using numeric headers from sheet):
```
TABLE | PROCLIM
 | TEXT | 90.0 | 100.0 |
ZSEV | Reformer Severity | 95.0 | 108.0 |
*
```

**With capacity adjustment**:
```
TABLE | PROCLIM
 | TEXT | 90.0 | 100.0 |
ZSEV | Reformer Severity | 95.0 | 108.0 |
*
TABLE | CAPS
 | TEXT | MAX |
CLPR | Low-P Reformer BPD | 30.0 |
*
TABLE | SELL
 | TEXT | PRICE |
UPR | Unleaded Premium | <PRICE_VAL> |
*
```

## Critical Rules
- **ALWAYS read_sheet("PROCLIM") first** — column headers vary by model
- **Use numeric column headers** from the sheet (e.g., 90.0, 100.0), NOT "MIN"/"MAX"
- Typical ranges: ZSEV (90-110), ZCON (70-98)
- Process changes affect product yields -> check SELL
- Process changes may need capacity adjustment -> check CAPS
- Use EXACT equipment codes from CAPS.md (CLPR, not CRF; CCCU, not CCC)
