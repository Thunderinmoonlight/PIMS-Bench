# Operation Patterns — Expert Experience

## Pattern 1: Capacity Expansion Chain
When expanding unit capacity (CAPS.MAX), chain:
```
CAPS.MAX  (increase) -> SELL.PRICE  (increase) (capture value, π=0.48)
CAPS.MAX  (increase) -> BUY.MAX  (increase) (ensure feedstock, π=0.24)
```

## Pattern 2: Severity Tuning
Reformer/FCC severity:
```
TABLE | PROCLIM
 | TEXT | MIN | MAX
ZSEV |  | 95.0 | 105.0      reformer RON range
ZCON |  |  | 76.0            FCC conversion (MAX only OK)
```
- ZSEV = reformer severity -> MUST set BOTH MIN+MAX
- ZCON = FCC conversion -> MAX alone OK here
- CLPR = reformer capacity (in CAPS table)

## Pattern 3: Blending Component Introduction
New component always needs 3 tables:
```
BLNMIX  -> allow component in products
BUY     -> purchase the component (MAX + COST)
SELL    -> price the products it goes into
```

## Pattern 4: Full Optimization Order
When optimizing the full plant (L5):
1. **PROCLIM** — severity first
2. **CAPS** — capacity
3. **SELL** — prices
4. **BUY** — feedstock
5. **BLNSPEC/BLNMIX** — quality

This order matches expert practice in 80% of L5 cases.
