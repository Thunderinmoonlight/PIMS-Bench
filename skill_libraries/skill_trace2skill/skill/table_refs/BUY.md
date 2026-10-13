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

### MAX vs MIN vs FIX — Critical Distinction
- **"Increase limit to X" / "Raise cap to X"** -> modify **MAX** column
- **"Must purchase at least X" / "Minimum X"** -> modify **MIN** column
- **"Purchase exactly X" / "Fixed at X"** -> modify **FIX** column
- **"Cost is $X" / "Price of $X"** -> modify **COST** column

**Common mistake**: Writing FIX when the task says "limit" or "cap" -> should be MAX.

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