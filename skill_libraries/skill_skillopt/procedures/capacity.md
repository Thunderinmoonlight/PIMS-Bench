# Procedure: Capacity Change

## When to use
Task mentions: capacity, expand, MAX, MIN, utilization, restart, force

## Steps
1. Identify unit from CAPS table (see table_refs/CAPS.md)
2. Determine: expansion (MAX (increase)) or forced utilization (MIN (increase))?
3. Check dep_map.md: CAPS->SELL (48%), CAPS->BUY (24%)
4. Write CASE with CAPS + dependent tables

## Templates

**Expansion (MAX only)**:
```
CASE N | Expand unit capacity
TABLE | CAPS
 | TEXT | MAX
UNIT_TAG |  | NEW_MAX
*
TABLE | SELL
 | TEXT | PRICE
PRODUCT |  | NEW_PRICE
*
```

**Forced utilization (MIN + MAX)**:
```
CASE N | Force unit utilization
TABLE | CAPS
 | TEXT | MIN | MAX
UNIT_TAG |  | NEW_MIN | NEW_MAX
*
```

## Oracle Examples
**Example**: FCC MIN=X, URG $X -> objective changes accordingly
```
CASE (example)
TABLE | CAPS
 | TEXT | MIN
CCCU |  | 23.0
*
TABLE | SELL
 | TEXT | PRICE
URG |  | <PRICE_VAL>
*
```

**Example**: Coker MIN=X/MAX=Y, AHV MAX=X, DSL $X -> expected result
```
CASE (example)
TABLE | CAPS
 | TEXT | MIN | MAX
CDLC |  | 13.0 | 20.0
*
TABLE | BUY
 | TEXT | MAX
AHV |  | new_limit
*
TABLE | SELL
 | TEXT | PRICE
DSL |  | <PRICE_VAL>
*
```

## Critical Rules
- Setting only MAX when optimizer is already below -> NO EFFECT (δ=0)
- Forced utilization requires BOTH MIN and MAX
- CAPS.MAX  (increase) -> check SELL.PRICE for affected products
- CAPS.MAX  (increase) -> check BUY.MAX for feedstock
