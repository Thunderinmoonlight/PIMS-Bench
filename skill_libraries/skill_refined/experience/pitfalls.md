# Common Pitfalls — Expert Experience

## Pitfall 1: PROCLIM Single Bound
**Wrong**: Setting only PROCLIM.MAX
```
TABLE | PROCLIM
 | TEXT | MAX
ZCON |  | 76.0
```
**Result**: Objective unchanged (δ=0). Optimizer already below MAX.
**Fix**: Set BOTH MIN and MAX:
```
TABLE | PROCLIM
 | TEXT | MIN | MAX
ZCON |  | 70.0 | 76.0
```

## Pitfall 2: SLPR Column Name
**Wrong**: Using "R90" or "RON90" as column name
```
TABLE | SLPR
 | TEXT | R90         common mistake
WBALR90 |  | -0.912
```
**Correct**: Column name is "HTD HSRN"
```
TABLE | SLPR
 | TEXT | HTD HSRN
WBALR90 |  | -0.912
```

## Pitfall 3: Column Misalignment
**Wrong**: Header column C ≠ Data column C
```
TABLE | SELL
 | TEXT | PRICE |       PRICE is column C
JET | Kero/Jet |  | 150.0 |   150.0 is column D! [x]
```
**Correct**:
```
TABLE | SELL
 | TEXT | PRICE |
JET | Kero/Jet | 150.0 |   150.0 is column C [ok]
```

## Pitfall 4: BUY.COST vs SELL.PRICE
**Common mistake**: Modifying BUY.COST for price scenarios
**Reality**: BUY.COST rarely modified (π=0.08). Most price scenarios use SELL.PRICE.
**Rule**: If task says "price" -> SELL.PRICE. If "cost" -> BUY.COST.

## Pitfall 5: REPLACE vs TABLE
**TABLE**: Modifies specific rows (unlisted rows unchanged)
**REPLACE**: Replaces entire table (unlisted rows DELETED!)
Only use REPLACE when you want to set ALL rows.

## Pitfall 6: Exploration Paralysis
**Problem**: Agent reads 8+ sheets, runs out of steps, never writes.
**Fix**: Read max 3 sheets -> identify pattern -> write immediately.
**Data**: Agents writing within 5 steps: 65% success. Reading 8+ sheets first: 25%.

## Pitfall 7: Over-Generation (MOST COMMON — 37% of errors)
**Problem**: Agent adds tables/changes not requested by the scenario.
**Examples**:
- Scenario says "increase coker capacity" -> Agent also adds SELL price changes
- Scenario says "raise limit" -> Agent sets both MIN and MAX (only MAX needed)
- Scenario mentions "premium gasoline" in passing -> Agent adds UPR price change
**Fix**: Before write_case(), check: does EVERY table in my CASE have a **direct, explicit mention** in the scenario? If not, remove it.

## Pitfall 8: MAX vs FIX Confusion
**Problem**: "Purchase limit" or "cap" means MAX, not FIX.
**Wrong**:
```
TABLE | BUY
 | TEXT | FIX |
ARH | Arab Heavy | 200.0 |     Note: FIX forces exact amount
```
**Correct**:
```
TABLE | BUY
 | TEXT | MAX |
ARH | Arab Heavy | 200.0 |     Better: MAX sets upper limit
```
**Rule**: "limit/cap/maximum/upper bound" -> MAX. "exactly/fixed/force" -> FIX.

## Pitfall 9: Row Tag Precision
**Problem**: Using approximate or abbreviated row tags.
**Wrong**: `MTB` (abbreviated) -> **Correct**: `MTBE` (full tag)
**Wrong**: `MRL` (Marlim) -> **Correct**: `MRY` (Merey) — different crude!
**Wrong**: `WBAL1` (generic) -> **Correct**: `WBALDCD` (specific to unit)
**Fix**: Always copy row tags **exactly** from read_sheet() output. Never abbreviate or guess.

## Pitfall 10: Table Name Case Sensitivity
**Problem**: Using lowercase or mixed case for table names.
**Wrong**: `Curve` -> **Correct**: `CURVE`
**Wrong**: `Utilbuy` -> **Correct**: `UTILBUY`
**Fix**: Table names are ALWAYS UPPERCASE in CASE entries.

## Pitfall 11: PROCLIM Column Headers
**Problem**: Using MIN/MAX text when the sheet has numeric column headers.
**Note**: PROCLIM may use numeric headers (e.g., `90.0`, `100.0`) that represent process severity levels, NOT MIN/MAX bounds.
**Fix**: Always read_sheet("ProcLim") first to see the actual column headers. If columns are numbers, use those numbers as column names. If columns say MIN/MAX, use MIN/MAX.
