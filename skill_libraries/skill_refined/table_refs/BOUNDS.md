# BOUNDS — LP Variable Bounds Override

Overrides LP solver variable bounds to unlock or constrain optimization variables.

## Row Tag Format

Row tags follow the pattern: `{variable_name}` or `{variable_name}>` (with > suffix for swing cuts).

| Row Tag | Description |
|---------|-------------|
| SCD2NK> | Swing cut D to NK (unlock swing cut range) |
| SCRK> | Swing cut to RK |

## Columns

| Column | Purpose |
|--------|---------|
| TEXT | Description |
| MIN | Lower bound override |
| MAX | Upper bound override |

## Example: Unlock swing cut range

```
TABLE | BOUNDS
 | TEXT | MIN | MAX |
SCD2NK> | SCD2NK> | 0.0 | 10.0 |
*
```

Setting MIN=0/MAX=10 unlocks the swing cut variable to allow values between 0 and 10.

**Only include the columns you are changing.**
