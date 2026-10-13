# Write Operations — CASE Entry Rules

## CRITICAL RULE: Only Write Columns You Are Changing

When writing CASE entries, **only include the columns you need to modify**. Do NOT copy all columns from the sheet.

### CORRECT — only PRICE column:
```
TABLE | SELL
 | TEXT | PRICE |
DSL | Diesel | 148.0 |
*
```

### WRONG — copied all columns:
```
TABLE | SELL
 | TEXT | MIN | MAX | FIX | PRICE | VPRICE | VOL | GROUP | LIQ | DISABLE |
DSL | Diesel | | 0.0 | 22.0 | 148.0 | 131.37 | | 1.0 | 6.0 | 1.0 |
*
```

The second version creates 9 unnecessary components and reduces match precision.

## CASE Entry Structure

```
TABLE | TABLE_NAME
 | TEXT | COL1 | COL2 |        header: only columns you're changing
ROW_TAG | description | val1 | val2 |    data: matching positions
*                               terminator (required)
```

## Common Mistakes to Avoid

1. **Copying all columns** from read_sheet output -> only write columns you're changing
2. **Missing terminator** `*` after each TABLE block
3. **Wrong row tags** -> check table_refs for correct tags (e.g., CGTU not CTGT for Scanfiner)
4. **Wrong column names** -> check table_refs for correct column names (e.g., COST not IPRICE for BUY)
5. **Extra empty columns** -> don't include trailing empty `|` separators

## Multiple Tables in One CASE

```
TABLE | CAPS
 | TEXT | MAX |
CDLC | Delayed Coker | 20.0 |
*
TABLE | SELL
 | TEXT | PRICE |
DSL | Diesel | 148.0 |
*
```

Each TABLE block needs its own header row and `*` terminator.

## CRITICAL: Minimal Write Principle

**Only write tables that the task EXPLICITLY requires.** Do NOT add tables because they seem "related" or "might be useful."

### Common Over-Generation Mistakes:
1. **Adding SELL when only a capacity change is requested** — "increase coker capacity" -> only CAPS, NOT SELL
2. **Adding BUY when only a blending change is requested** — "enable component X" -> only BLNMIX, NOT BUY+SELL
3. **Adding PROCLIM when a BOUNDS change is needed** — "tighten LP variable bound" -> BOUNDS, NOT PROCLIM
4. **Setting both MIN and MAX when only one is asked** — "raise the limit to 200" -> only MAX, NOT MIN+MAX
5. **Adding price changes not explicitly mentioned** — if the scenario doesn't say "change price to $X", don't add SELL/BUY price rows

### Self-Check Before write_case():
- [ ] Does EVERY table in my CASE have a **direct mention** in the scenario?
- [ ] Am I adding any column that wasn't **explicitly requested**?
- [ ] Am I setting MIN/MAX/FIX values that weren't **stated in the task**?
- If any answer is YES -> **remove those extra components**
