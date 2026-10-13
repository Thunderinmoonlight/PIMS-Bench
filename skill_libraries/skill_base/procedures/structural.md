# Procedure: Structural Changes

## When to use
Task mentions: cut, swing, distillation, transplant, migration, submodel, yield

## Steps
1. Identify: CRDCUTS (cut points) or SLPR (yields) or unit transplant?
2. For CRDCUTS: column = CD1
3. For SLPR: column = "HTD HSRN" (NOT "R90"!)
4. Check dep_map for CAPS and SELL dependencies

## Templates

**Distillation cut**:
```
TABLE | CRDCUTS
 | TEXT | CD1
CUT_TAG |  | CUT_VALUE
*
TABLE | CAPS
 | TEXT | MAX
UNIT |  | CAP_VALUE
*
TABLE | SELL
 | TEXT | PRICE
PRODUCT |  | PRICE_VAL
*
```

**Submodel yield (SLPR)**:
```
TABLE | SLPR
 | TEXT | HTD HSRN
WBALR90 |  | -0.912
WBALR94 |  | -0.894
WBALR98 |  | -0.872
*
TABLE | CAPS
 | TEXT | MAX
CSFA |  | CAP_VAL
*
```

## Oracle Examples
**a capacity task**: K/D swing + coker + DSL price -> expected result
```
CASE (example)
TABLE | CRDCUTS
 | TEXT | CD1
KD1 |  | 7.0
*
TABLE | CAPS
 | TEXT | MAX
CDLC |  | 20.0
*
TABLE | SELL
 | TEXT | PRICE
DSL |  | <PRICE_VAL>
*
```

## Critical Rules
- SLPR column is "HTD HSRN" — NOT "R90" or "RON90"
- SLPR values are NEGATIVE (material balance)
- Unit transplant = just CAPS + SELL (no SUBMODS needed)
