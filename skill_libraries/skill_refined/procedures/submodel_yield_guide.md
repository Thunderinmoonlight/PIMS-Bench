# Submodel Sheet Reasoning Guide

PIMS submodel sheets (S-prefixed tables like SLPR, SCCU, SDHT, SDLC, SHCD) define yield coefficients for processing units. They have different conventions from standard tables (SELL, BUY, CAPS).

## Step 1: Read the Sheet First
ALWAYS call read_sheet() on any submodel sheet before writing CASE entries. Never guess row tags or column names.

## Step 2: Identify the Sheet Type
After reading the sheet, classify it into one of three structural types based on what you observe:

### Type A: Severity-Mode Sheets
**How to recognize**: Column headers are operating modes or severity levels (numbers like 90/94/98, or mode codes). Each column represents a different operating condition of the same unit.

**Structure pattern**:
- Each product/feed has its OWN ROW per mode
- Each row typically has a value in only ONE column (its matching mode)
- A balance/loss row spans ALL columns with values in each

**Writing rules**:
- Write ONE ROW PER MODE — never consolidate multiple modes into one row
- Use the exact column header codes from the sheet (don't expand or rename them)
- Row tags often follow a pattern: prefix + mode identifier. Copy the pattern from existing rows.
- Include the balance/loss row if adjusting yields

### Type B: Product-Yield Sheets
**How to recognize**: Column headers are product stream names or codes (gasoline, diesel, gas, coke, etc.). Each column is a different output product.

**Structure pattern**:
- Rows represent feed components or conversion sources
- Values show how feed converts to each product (yield distribution)
- Values in a row may sum to approximately 1.0

**Writing rules**:
- Use exact column headers from the sheet as product column names
- Use exact row tags — they often encode the feed type or mechanism
- If modifying one product yield, consider whether balance rows need adjustment

### Type C: Balance-Component Sheets
**How to recognize**: Column headers are balance terms or properties (sulfur, hydrogen, specific gravity, etc.). Values are typically small coefficients.

**Structure pattern**:
- Rows are material balance terms or transfer coefficients
- Many cells are blank (sparse matrix)
- Only specific rows have values in specific columns

**Writing rules**:
- Match the sparse pattern — don't add values to columns that are normally blank
- Use exact row tags and column names from the sheet
- Row tags often have distinctive prefixes indicating the balance category

## Universal Rules for ALL Submodel Sheets
These rules apply regardless of sheet type:

### GOLDEN RULE: Copy What You See
When you call read_sheet(), the returned data IS the template for your CASE entries:
- **Each row in read_sheet output = one row in your CASE**
- **Row tags: copy character-for-character** (e.g., if sheet shows "WBALR90", use "WBALR90" — never invent "REFORMATE" or "BAL1")
- **Column headers: copy exactly** (e.g., if sheet shows "90", "94", "98", use those — never expand to "YIELD90")
- **Value placement: match the sheet** (if a row has a value in only one column, your CASE row should too)
- **Never merge rows**: if the sheet has 3 separate rows, write 3 separate CASE rows
- **Never split columns**: if the sheet has 3 columns, use 3 columns

### 1. Material Balance Rows
Most submodel sheets have balance/loss rows that maintain mass conservation. When adjusting yields:
- Look for rows with names containing "BAL", "LOSS", or "WBAL" prefix
- Balance rows typically have values across ALL columns (not sparse)
- ALWAYS include balance rows in your CASE when modifying product yields
- The balance row values may need adjustment when you change product coefficients

### 2. Recognizing Multi-Row Patterns
After read_sheet(), check: does the same product/mechanism appear in MULTIPLE rows?
- If yes: each row corresponds to a different mode/column -> your CASE must have separate rows too
- Example: if you see rows "WBALR90", "WBALR94", "WBALR98" each with a value in a different column, these are 3 separate CASE rows, NOT one row with 3 values

### 3. TEXT Column Required
Every CASE entry for submodel sheets MUST include the TEXT column as the second column.
Set TEXT equal to the row tag (e.g., TEXT = "WBALR90" for row tag WBALR90).

### 4. Discover Naming Patterns From Existing Rows
Before writing, study the row tags in read_sheet output:
- Do they share a common prefix? (e.g., WBAL + something)
- Do they encode the column header? (e.g., WBALR90 -> R90 column)
- Copy this exact pattern for your CASE entries

## Step 3: Write CASE Entries That Mirror the Sheet
Regardless of type:
- Copy row tags CHARACTER-FOR-CHARACTER from read_sheet output
- Copy column headers EXACTLY as shown
- Match the row-per-entry structure: if the sheet has separate rows, write separate CASE entries
- Include balance/loss rows when adjusting yields
- Include TEXT column (value = row tag) in every entry

## Common Mistakes
- Inventing row tags instead of copying from read_sheet (e.g., writing "BAS1" when the sheet shows "WBALHTD")
- Consolidating multiple sheet rows into a single CASE entry (e.g., putting all severity modes in one row)
- Using descriptive column names instead of the actual short codes from the sheet
- Skipping the TEXT column
- Forgetting the material balance row when adjusting yields
- Skipping read_sheet and guessing the structure

## CAPS vs BOUNDS for Capacity
When the scenario mentions capacity or throughput changes:
- Use **CAPS** table for unit physical capacity (kbbl/day throughput). Row tags are unit codes.
- Use **PROCLIM** for operating constraints (severity ranges, conversion percentages).
- **BOUNDS** is NOT for capacity changes.

## Format Examples

### Example A: 3-mode severity sheet (modes: 80, 85, 90)
```
TABLE | {SHEET_NAME}
 | TEXT | R80 | R85 | R90 |
WBALR80 | {description} | -0.850 |  |  |
WBALR85 | {description} |  | -0.875 |  |
WBALR90 | {description} |  |  | -0.900 |
WBALLOS | Loss | 0.008 | 0.011 | 0.014 |
*
```
**Key points**:
- Column headers have mode prefix (R80, not 80)
- Each mode has its own row (WBALR80, WBALR85, WBALR90)
- Each row has value only in its column (others blank)
- Balance row (WBALLOS) has values in all columns

### Example B: 2-mode sheet (modes: 100, 110)
```
TABLE | {SHEET_NAME}
 | TEXT | M100 | M110 |
WBALM100 | {description} | -0.920 |  |
WBALM110 | {description} |  | -0.945 |
WBALLOS | Loss | 0.012 | 0.015 |
*
```
**Key points**:
- Column headers use mode codes (M100, M110)
- Each mode has its own row with WBAL* tag
- Balance row has values in all columns
