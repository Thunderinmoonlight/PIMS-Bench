## BUY - Crude Purchase Table

### Crude Codes
| Code | Description |
|------|-------------|
| ARL | Arabian Light |
| ARH | Arabian Heavy |
| KWT | Kuwait Export |

### Format
| Column | Type | Description |
|--------|------|-------------|
| 1 | TEXT | Crude code |
| 2 | MAX | Maximum purchase limit |
| 3 | MIN | Minimum purchase requirement |
| 4 | FIX | Fixed purchase amount (forces exact value) |
| 5 | COST | Unit purchase cost ($/bbl) |

### MAX vs MIN vs FIX vs COST — Critical Distinction
- **"Increase limit to X" / "Raise cap to X"** -> modify **MAX** column
- **"Must purchase at least X" / "Minimum X"** -> modify **MIN** column
- **"Purchase exactly X" / "Fixed at X"** -> modify **FIX** column
- **"Cost is $X" / "Price of $X" / "Reduce price by $X"** -> modify **COST** column

**Common mistakes**:
- Writing FIX when the task says "limit" or "cap" -> should be MAX
- **Using !IPRICE instead of COST** -> !IPRICE is infeasibility price (internal solver variable), NEVER modify it. Always use COST for purchase prices.

### Example: Reduce Purchase Prices
**Task**: "Reduce all crude purchase prices by $15/bbl from their current values"

**Correct approach**:
1. Read current COST values from Buy sheet
2. Subtract $15 from each current value
3. Write new COST values

**Correct CASE**:
```
TABLE | BUY
 | TEXT | COST |
AMM | Amenam | 49.42 |     (was 64.42, now 64.42 - 15 = 49.42)
ARH | Arabian Heavy | 50.08 |  (was 65.08, now 65.08 - 15 = 50.08)
...
```

**WRONG**: Using !IPRICE column -> this is an internal solver variable, not the purchase price.

### Model-Specific Column Names
- **WS (Weight Sample)**: Standard columns — MAX, MIN, FIX, COST
- **GC (Gulf Coast)**: Same column NAMES, but more crude rows. **Always read_sheet("Buy") first** to discover exact row tags and column positions.

### GC Model Row Tags
GC has more crude types. Common tags:
| Tag | Crude |
|-----|-------|
| ARL | Arabian Light |
| ARH | Arabian Heavy |
| KWT | Kuwait Export |
| MRY | Merey |
| MRL | Marlim |
| MRN | Mariner |
| WTI | West Texas Intermediate |

**WARNING**: MRY (Merey), MRL (Marlim), and MRN (Mariner) are **different crudes**. Always match the EXACT row tag from read_sheet() output — do not guess or abbreviate.