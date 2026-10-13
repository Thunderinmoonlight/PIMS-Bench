# UTILBUY — Utility Purchase Table

## Methodology

When modifying utility costs:
1. **Read UTILBUY sheet first** to discover the exact row tags (e.g., GAS, PWR, STEAM, etc.)
2. Identify the row tag for the utility you need to modify
3. Use COST column to change unit cost
4. Only include columns you are changing

## Example Structure

```
TABLE | UTILBUY
 | TEXT | COST |
{ROW_TAG} | {description} | {new_cost} |
*
```

**Always read_sheet("UTILBUY") first** — row tags vary by model and utility type.
