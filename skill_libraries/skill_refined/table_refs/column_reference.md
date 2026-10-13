# Column Name Reference and Common Pitfalls

## SELL Table Columns
| Column | Meaning | When to Use |
|--------|---------|-------------|
| PRICE | Unit selling price ($/bbl) | Changing product prices |
| VPRICE | Volume-weighted avg price | **NEVER use for price changes** |
| VOL | Sales volume limit | Limiting product sales |
| MIN | Minimum sales | Setting minimum output |
| MAX | Maximum sales | Capping product output |
| FIX | Fixed sales value | **Avoid — removes LP flexibility** |
| GROUP | Product group code | Restructuring product groups |
| LIQ | Liquid flag (0/1) | Phase designation |

## BUY Table Columns
| Column | Meaning | When to Use |
|--------|---------|-------------|
| COST | Purchase cost ($/bbl) | Changing crude costs |
| MAX | Purchase limit (kbbl/day) | Setting supply limits |
| MIN | Minimum purchase | Forced purchases |
| !IPRICE | Internal calculated price | **Read only — do NOT modify** |
| FIX | Fixed purchase amount | **Avoid — use MAX instead** |

## CAPS Table Columns
| Column | Meaning | When to Use |
|--------|---------|-------------|
| MIN | Minimum throughput | Setting floor (0 for shutdown) |
| MAX | Maximum throughput (capacity) | Setting capacity ceiling |
| REPORT | Reporting flag | Usually leave unchanged |

## CRITICAL: TEXT Column Required
Every CASE entry MUST include a TEXT column as the second column:
```
TABLE | SELL
 | TEXT | PRICE |           TEXT is mandatory
DSL | DSL | 145.0 |        TEXT value = row tag (not description)
*
```
The TEXT value should be the row tag itself (e.g., DSL, not "Diesel"). Never skip the TEXT column.

## Key Column Mistakes to Avoid
1. **PRICE vs VPRICE**: ALWAYS use PRICE for setting product prices. VPRICE is a computed field — using it will cause errors.
2. **MAX vs FIX**: Use MAX to set upper bounds. FIX forces an exact value and removes optimization flexibility.
3. **COST vs !IPRICE**: Use COST for purchase price changes. !IPRICE is internal.
4. **MIN+MAX for shutdown**: Set BOTH to 0 to completely disable a unit.
5. **Uppercase table names**: Always use SELL, BUY, CAPS — never Sell, Buy, Caps.
6. **Missing TEXT column**: Every table entry must have TEXT as second column. This is the #1 formatting mistake.

## Row Tag Conventions
- Product rows (SELL): URG, UPR, JET, DSL, HSF, LSF, RFG, NPH
- Crude rows (BUY): ARH, ARL, BCF, TJL, TJH, KUW, WCS, MES
- Unit rows (CAPS): ZRFM, ZFCC, ZCOK, ZHCU, ZDHT, CDHT, CCCU, CAT2
