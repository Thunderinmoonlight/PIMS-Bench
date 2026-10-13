# BLNTARG — Blending Target Limits

## Methodology

BLNTARG sets upper/lower limits for blend component ratios. Column naming follows a convention:

| Prefix | Meaning | Example |
|--------|---------|---------|
| UALL | Upper limit applying to ALL blend products | UALL |
| DALL | Lower limit applying to ALL blend products | DALL |
| U{product} | Upper limit for specific product | URG, UDSL |
| D{product} | Lower limit for specific product | DURG, DDSL |

## How to Determine the Right Column

1. **Read BLNTARG sheet first** to see available columns
2. If the limit applies to all products -> use UALL or DALL
3. If the limit applies to a specific product -> use U{product_code} or D{product_code}
4. Only include the column you are changing

## Example: Set IC4 max to 5% for all products

```
TABLE | BLNTARG
 | TEXT | UALL |
IC4 | IC4 | 0.05 |
*
```

**Do not confuse BLNTARG (target limits) with BLNCAP (capacity) or BLNMIX (eligibility).**
