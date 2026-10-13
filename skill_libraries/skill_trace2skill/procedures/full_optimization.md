# Procedure: Full Optimization

## When to use
Task mentions: full optimization, severity + capacity + prices, multi-table (4-5 tables)

## Steps (ordered by expert practice)
1. **PROCLIM** — severity first (sets yield structure)
2. **CAPS** — capacity (constrains throughput)
3. **SELL** — prices (captures value)
4. **BUY** — feedstock (enables throughput)
5. **BLNSPEC/BLNMIX** — quality (fine-tunes products)

## Template
```
CASE N | Full plant optimization
TABLE | PROCLIM
 | TEXT | MIN | MAX
ZSEV |  | SEV_MIN | SEV_MAX
ZCON |  |  | CONV_MAX
*
TABLE | CAPS
 | TEXT | MAX
Cat2 |  | CDU2_MAX
CCCU |  | FCC_MAX
CDLC |  | COKER_MAX
CLPR |  | REFORMER_MAX
*
TABLE | SELL
 | TEXT | PRICE
DSL |  | DSL_PRICE
JET |  | JET_PRICE
URG |  | URG_PRICE
UPR |  | UPR_PRICE
*
TABLE | BUY
 | TEXT | MAX
ARL |  | ARL_MAX
AHV |  | AHV_MAX
KUW |  | KUW_MAX
*
```

## Oracle Example
**Example**: Reformer RON 98-110, capacity 30, UPR $160 -> expected result
```
CASE (example)
TABLE | PROCLIM
 | TEXT | MIN | MAX
ZSEV |  | <MIN_VAL> | <MAX_VAL>
*
TABLE | CAPS
 | TEXT | MAX
CLPR |  | 30.0
*
TABLE | SELL
 | TEXT | PRICE
UPR |  | <PRICE_VAL>
*
```

## Critical Rules
- PROCLIM: ALWAYS set BOTH MIN+MAX (single bound = no effect)
- Order matters: PROCLIM -> CAPS -> SELL -> BUY -> BLNSPEC
- 4-5 TABLE blocks typical for L5 tasks
