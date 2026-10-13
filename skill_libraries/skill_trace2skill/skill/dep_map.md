# Cross-Table Dependency Map (π-filtered)
# Dependencies with practice coverage > 5%

## High-Frequency Dependencies (π > 0.1)

| From | To | π | Rule |
|------|----|----|------|
| CAPS | SELL | 0.48 | Capacity change -> update product prices/limits |
| BUY | SELL | 0.25 | Purchase change -> product availability change |
| BUY | CAPS | 0.24 | Feedstock must match capacity |
| PROCLIM | SELL | 0.17 | Process severity -> product output change |
| CAPS | PROCLIM | 0.16 | Capacity ↔ process limits coupled |
| BLNSPEC | SELL | 0.13 | Quality spec -> product price |
| BLNSPEC | CAPS | 0.11 | Quality spec -> may need capacity |

## Medium-Frequency Dependencies (π 0.05-0.1)

| From | To | π | Rule |
|------|----|----|------|
| BLNMIX | BUY | 0.06 | New blend component -> need purchase |
| CRDCUTS | CAPS | 0.05 | Cut change -> capacity adjustment |
| CRDCUTS | SELL | 0.05 | Cut change -> product yield change |

## Dependency Chains (common patterns)

**Capacity expansion chain** (48% of CAPS tasks):
```
CAPS.MAX  (increase) -> SELL.PRICE  (increase) -> BUY.MAX  (increase)
```

**Severity tuning chain** (17% of PROCLIM tasks):
```
PROCLIM.MIN+MAX -> CAPS.MAX -> SELL.PRICE
```

**Blending introduction chain** (6% of BLNMIX tasks):
```
BLNMIX (allow component) -> BUY (purchase) -> SELL (price products)
```

## Quick Lookup: "I'm changing X, what else do I need?"

| Changing... | Must also check... |
|------------|-------------------|
| CAPS.MAX | SELL.PRICE/MAX, BUY.MAX |
| CAPS.MIN | SELL.PRICE (forced utilization) |
| PROCLIM | BOTH MIN+MAX, CAPS, SELL |
| BUY.MAX | CAPS.MAX (enough capacity?) |
| BUY.COST | rarely needed (π=0.08) |
| SELL.PRICE | usually standalone (π=0.79) |
| BLNMIX | BUY (source), SELL (value) |
| BLNSPEC | CAPS (capacity), SELL (price) |
| CRDCUTS | CAPS (capacity), SELL (products) |
| SLPR | CAPS (reformer capacity) |
