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
**WS-L2-02**: FCC MIN=23, URG $140 -> objective 1002.33
```
CASE 411
TABLE | CAPS
 | TEXT | MIN
CCCU |  | 23.0
*
TABLE | SELL
 | TEXT | PRICE
URG |  | <PRICE_VAL>
*
```

**WS-L3-02**: Coker MIN=13/MAX=20, AHV MAX=55, DSL $145 -> 1293.73
```
CASE 421
TABLE | CAPS
 | TEXT | MIN | MAX
CDLC |  | 13.0 | 20.0
*
TABLE | BUY
 | TEXT | MAX
AHV |  | 55.0
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
