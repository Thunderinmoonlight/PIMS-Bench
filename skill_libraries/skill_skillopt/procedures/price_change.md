# Procedure: Price Change

## When to use
Task mentions: price, cost, $X, surge, drop, premium

## Steps
1. Identify which table: SELL (product prices) or BUY (crude costs)
2. Find the row tag (product/crude name)
3. Write CASE with PRICE (SELL) or COST (BUY) column

## Template
```
CASE N | Description
TABLE | SELL
 | TEXT | PRICE
PRODUCT_TAG |  | NEW_PRICE
*
```

## Oracle Examples
**a capacity task**: product price -> $X -> objective changes accordingly
```
CASE (example)
TABLE | SELL
 | TEXT | PRICE
JET |  | new_price
*
```

**a GC task**: All crude prices change by $X -> objective changes accordingly
```
CASE (example)
TABLE | BUY
 | TEXT | COST
ARL |  | -15.0
AHV |  | -15.0
... (all crudes)
*
```

## Dependencies
- SELL.PRICE usually standalone (π=0.79, rarely needs other tables)
- BUY.COST rarely modified (π=0.08) — most price tasks use SELL.PRICE
- If task also mentions capacity -> check dep_map.md for CAPS->SELL

## Common Mistakes
- Using BUY.COST when task says "price" (should be SELL.PRICE)
- Modifying both SELL and BUY when only one is needed
