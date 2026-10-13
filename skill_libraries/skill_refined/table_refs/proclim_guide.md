# PROCLIM Table Guide (Processing Limits)

PROCLIM defines operating constraints for processing units, separate from CAPS which defines physical capacity.

## When to Use PROCLIM vs CAPS
- **CAPS** — Physical capacity (unit size, throughput limits). Use when scenario says "expand capacity" or mentions kbbl/day throughput.
- **PROCLIM** — Operating constraints (severity ranges, conversion limits). Use when scenario mentions RON, severity, conversion percentage, or operating mode.

## Common PROCLIM Rows
- **ZSEV** — Reformer severity (RON range)
- **ZFCV** — FCC conversion limit
- **ZCVN** — Coker conversion
- **ZDHV** — DHT severity

## How to Modify Severity
When scenario says "reformer severity 95-106 RON":
```
TABLE | PROCLIM
 | TEXT | MIN | MAX |
ZSEV | Reformer Severity | 95.0 | 106.0 |
*
```

When scenario says "FCC conversion max 76%":
```
TABLE | PROCLIM
 | TEXT | MAX |
ZFCV | FCC Conversion | 76.0 |
*
```

## Combined CAPS + PROCLIM Tasks
Many L5 tasks require BOTH tables:
1. CAPS: set throughput (MIN/MAX for unit capacity)
2. PROCLIM: set severity/conversion (MIN/MAX for operating range)

Example — "Reformer severity 95-106 RON, capacity 28 kbbl/day":
```
TABLE | PROCLIM
 | TEXT | MIN | MAX |
ZSEV | Reformer Severity | 95.0 | 106.0 |
*
TABLE | CAPS
 | TEXT | MIN | MAX |
ZRFM | Reformer | 0.0 | 28.0 |
*
```

## Critical Rules
- Always read_sheet("PROCLIM") to find the correct row tag for the unit
- Row tags start with Z (e.g., ZSEV, ZFCV, ZCVN)
- Severity values are in RON units (80-120 range typical)
- Conversion values are percentages (0-100 range)
