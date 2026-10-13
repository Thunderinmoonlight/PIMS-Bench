---
name: pims-hybrid-skill
description: "Hybrid PIMS operation skill: generic table catalog + dependency map + operation patterns. Use for any PIMS CASE table operation."
---

# PIMS Operation Skill — Hybrid Structure

## MANDATORY: Read Skills Before Sheets (DO THIS FIRST)

**STEP 1 (MANDATORY)**: Call `read_skill("SKILL")` to read this file.

**STEP 2 (MANDATORY)**: Based on task content, read the corresponding table skill files BEFORE calling read_sheet:

| IF task mentions... | MUST READ these skill files |
|---------------------|----------------------------|
| crude, purchase, feed, BUY | `table_refs/BUY.md` |
| price, sell, product, SELL | `table_refs/SELL.md` |
| capacity, unit, MAX, MIN, CAPS | `table_refs/CAPS.md` |
| blend, mix, recipe, component | `table_refs/BLNMIX.md` AND `table_refs/BLNSPEC.md` |
| yield, severity, RON, conversion, submodel | `table_refs/submodels.md` AND `procedures/submodel_yield_guide.md` |
| PROCLIM, process limit, bound | `table_refs/PROCLIM.md` AND `table_refs/proclim_guide.md` |

**CRITICAL**: You MUST read the table skill files BEFORE calling read_sheet. The skill files contain column names and usage rules that are essential for correct CASE entries.

**Example**: If task says "reduce crude purchase prices", you MUST:
1. Call `read_skill("SKILL")`
2. Call `read_skill("BUY")` to learn that BUY table uses COST column (not !IPRICE)
3. Then call `read_sheet("Buy")` to see the data
4. Write CASE using COST column

## Quick Router: What type of operation?

| Task mentions... | Operation Type | Read |
|-----------------|---------------|------|
| capacity, expand, unit, MAX, MIN | Capacity Change | procedures/capacity.md |
| price, cost, $X | Price Change | procedures/price_change.md |
| blend, mix, recipe, component | Blending | procedures/blending.md |
| additive, TEL, ethanol | Additive | procedures/blending.md (ADDITIVE table) |
| cut, swing, distillation, yield | Structural | procedures/structural.md |
| severity, RON, conversion, process | Process Parameter | procedures/process_operations.md |
| bound, variable limit, LP bound | LP Bounds | table_refs/BOUNDS.md |
| utility cost, fuel gas, steam | Utility | table_refs/UTILBUY.md |
| interaction, cross-unit effect | Interaction | (read_sheet on INTERACT) |

## CASE Format (MUST follow exactly)
```
CASE N | Description
TABLE | TABLE_NAME
 | TEXT | COL1 | COL2 |
ROW_TAG | description | val1 | val2 |
*
```
**CRITICAL**: Column C in header = Column C in data. Same position!

## Write Discipline

**Golden rule**: Only include columns and rows that the task explicitly requires.

When you call `read_sheet()`, you see many columns. Your CASE output should include ONLY the column(s) the task asks you to modify — never copy the full header row from `read_sheet()`.

Correct workflow:
1. `read_sheet("SELL")` -> see columns: TEXT, MIN, MAX, FIX, PRICE, VPRICE, ...
2. Task says "raise diesel price" -> only PRICE column matters
3. Write: `| TEXT | PRICE |` and `DSL | Diesel | 148.0 |`
4. Do NOT include MIN, MAX, FIX, VPRICE, GROUP, etc.

Why: Extra columns shift data positions and corrupt the CASE entry. PIMS maps values by column position — if you write 5 columns but only intend to change the 4th, PIMS may assign values to the wrong fields.

## Core Tables — Column Reference (READ THIS)

### BUY Table (Crude Purchase)
**Columns**:
- Column 1: TEXT (crude code)
- Column 2: MAX (maximum purchase limit)
- Column 3: MIN (minimum purchase requirement)
- Column 4: FIX (fixed purchase amount — forces exact value)
- Column 5: **COST** (unit purchase cost, $/bbl)

**CRITICAL**: For purchase price changes, use **COST** column. **NEVER use !IPRICE** — it's an internal solver variable for infeasibility pricing, not the purchase price.

**Purchase limit rules**:
- "Increase limit to X" / "Raise cap to X" / "Sign contract for X kbbl/day" / "Purchase up to X" -> modify **MAX** column
- "Must purchase at least X" / "Minimum X" -> modify **MIN** column
- "Purchase exactly X" / "Fixed at X" / "Must be exactly X" -> modify **FIX** column

**Example**: "Sign a contract for 15 kbbl/day at $120/bbl" -> modify MAX=15 and COST=120 (contract = upper limit, not fixed amount).

### SELL Table (Product Sales)
**Columns**:
- Column 1: TEXT (product code)
- Column 2: MIN (minimum sales)
- Column 3: MAX (maximum sales)
- Column 4: FIX (fixed sales amount)
- Column 5: **PRICE** (selling price, $/bbl)

**CRITICAL**: For product price changes, use **PRICE** column. **NEVER use VPRICE** — it's volume-weighted average price (computed value), not the selling price.

### CAPS Table (Capacity Bounds)
**Columns**:
- Column 1: TEXT (unit code)
- Column 2: MIN (minimum throughput, kbbl/day)
- Column 3: MAX (maximum capacity, kbbl/day)

**CRITICAL**: "Increase capacity to X" -> modify MAX. "Set minimum to X" -> modify MIN. Do NOT use FIX unless task says "exactly" or "fixed".

### PROCLIM Table (Process Limits)
**Columns**: Numeric severity levels (e.g., 90.0, 95.0, 100.0, 105.0)
- These represent process severity modes, NOT MIN/MAX bounds
- For severity ranges: write TWO values in the appropriate severity columns
- Example: "Reformer severity 92-102 RON" -> write 92.0 in column "90.0" and 102.0 in column "100.0"

### Submodel Sheets (SLPR, SDHT, SDLC, SCCU, SHCD)
Submodel sheets use a special CASE format that differs from standard tables.

Column headers use R-prefixed severity codes (e.g., R90, R94, R98 for reformer).
Row tags use WBALR-prefixed codes (e.g., WBALR90, WBALR94, WBALR98).
Always include a WBALLOS (loss) row for mass balance.

The yield matrix is diagonal: WBALR90 row has its value in R90 column, WBALR94 row in R94 column, etc.

Example for reformer yield adjustment:
```
TABLE | SLPR
 | TEXT | R90 | R94 | R98 |
WBALR90 | 90 RONC Reformate | -0.930 |  |  |
WBALR94 | 94 RONC Reformate |  | -0.915 |  |
WBALR98 | 98 RONC Reformate |  |  | -0.895 |
WBALLOS | Loss | 0.0091 | 0.0121 | 0.0145 |
*
```

Always call `read_sheet()` on the specific submodel sheet first to discover its exact row tags and column headers — they may differ between models.
Call `read_skill("submodels")` for the full submodel guide including Pattern A (BAS) and Pattern B (numeric) formats.

## When facing a task:
1. **MANDATORY**: Call `read_skill("TABLE_CATALOG")` to get generic table descriptions
2. Call the matching procedure file based on task type (see router above)
3. Use `read_sheet()` to explore specific tables (max 5 calls before writing)
4. Call `write_case()` with the CASE entries — **ONLY tables explicitly requested**
5. Call `run_pims()` to verify

## Write Strategy
Write tables the scenario **explicitly** asks for, PLUS necessary coordination tables (see `experience/patterns.md` for coordination patterns).

**DO NOT** add tables that are only tangentially related (see `experience/pitfalls.md` Pitfall 7: Over-Generation).

**Coordination examples** (from `experience/patterns.md`):
- Capacity expansion -> CAPS + SELL (price capture) + BUY (feedstock)
- New blending component -> BLNMIX + BUY + SELL
- Full optimization -> PROCLIM -> CAPS -> SELL -> BUY -> BLNSPEC/BLNMIX

## Column Quick Reference

| Scenario keyword | Table | Column to modify |
|---|---|---|
| product price, selling price, $X/bbl | SELL | PRICE (not VPRICE) |
| crude cost, purchase price | BUY | COST (not IPRICE) |
| capacity, expand, throughput limit | CAPS | MAX (not FIX) |
| minimum purchase/sales volume | BUY/SELL | MIN |
| exact amount, fixed quantity | BUY/SELL/CAPS | FIX (use sparingly) |
| severity, RON, conversion | PROCLIM | numeric severity column |
| sulfur, octane, RVP spec | BLNSPEC | pool column |
| blend eligibility, allow component | BLNMIX | 0 -> 1 |
| utility cost, fuel gas price | UTILBUY | COST |
| cross-unit interaction factor | INTERACT | target column |

## Reference Files
- [Table Catalog](table_refs/TABLE_CATALOG.md) — **MANDATORY** — all tables, columns, dependencies
- [Submodel Sheets](table_refs/submodels.md) — **MANDATORY for yield tasks** — S-prefix sheets, unit->sheet mapping
- [CAPS Equipment Codes](table_refs/CAPS.md) — exact equipment tags for capacity table
- [PROCLIM Format](table_refs/PROCLIM.md) — numeric column headers (NOT MIN/MAX!)
- [Capacity Operations](procedures/capacity.md) — capacity expansion/utilization
- [Price Operations](procedures/price_change.md) — price/cost changes
- [Blending Operations](procedures/blending.md) — blend modifications
- [Structural Operations](procedures/structural.md) — cuts, swings, yields
- [Process Operations](procedures/process_operations.md) — severity, conversion parameters
- [Pitfalls](experience/pitfalls.md) — common mistakes to avoid
