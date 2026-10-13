# CRDQUAL — Crude Quality Override

Overrides crude oil quality parameters.

## Common Row Tags

| Row Tag | Crude Stream |
|---------|-------------|
| KE1 | Kerosene stream |
| KE2 | Diesel stream |
| ARH | Arab Heavy crude |
| ARL | Arab Light crude |

## Common Column Tags

| Column | Property |
|--------|---------|
| SPG | Specific gravity |
| SUL | Sulfur content (wt%) |
| API | API gravity |

## Example: Override kerosene specific gravity

```
TABLE | CRDQUAL
 | TEXT | SPG |
KE1 | KE1 | 0.8 |
*
```

**Only include the columns you are changing.**
