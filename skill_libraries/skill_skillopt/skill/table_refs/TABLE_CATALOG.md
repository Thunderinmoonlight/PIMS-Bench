# PIMS Table Catalog

## Overview
PIMS contains 85+ interconnected tables organized into 5 domains. Use `list_sheets()` to see all available tables, then `read_sheet()` to explore specific tables.

## Table Domains

### Supply/Demand Tables
- **BUY**: Crude/feedstock purchase limits and costs
  - Key columns: COST, MAX, MIN, FIX, IPRICE
  - Row tags: Crude names (ARL, AHV, KUW, BAC, etc.)
- **SELL**: Product sales limits and prices
  - Key columns: PRICE, MAX, MIN, FIX
  - Row tags: Product names (URG, UPR, DSL, JET, LSF, HSF, etc.)
- **UTILBUY**: Utility purchase limits
- **UTILSEL**: Utility sales limits

### Capacity Tables
- **CAPS**: Unit capacity limits
  - Key columns: MAX, MIN
  - Row tags: Unit names (Cat1, Cat2, CCCU, CDLC, CLPR, CDHT, etc.)
  - Common units: CDU (Cat1/Cat2), FCC (CCCU), Coker (CDLC), Reformer (CLPR), HCU (CDHT)
- **PROCLIM**: Process limits (severity, conversion)
  - Key columns: MIN, MAX
  - Row tags: Process parameters (ZSEV=reformer severity, ZCON=FCC conversion, etc.)
  - **CRITICAL**: Always set BOTH MIN and MAX for process parameters

### Submodel Tables
- **SLPR**: Reformer yield tables
  - Key column: "HTD HSRN" (NOT "R90" or "RON90")
  - Row tags: WBALR90, WBALR94, WBALR98, WBALR02
  - Values are NEGATIVE (material balance)
- **SCCU**: FCC submodel
- **SDHT**: Diesel hydrotreater submodel
- **SDLC**: Coker submodel

### Blending Tables
- **BLENDS**: Blend definitions
- **BLNMIX**: Blend component mixture ratios
  - Columns: Product pool names (DSL, LSF, URG, UPR, JET, etc.)
  - Row tags: Component names (IC4, NGL, etc.)
  - Values: Volume fractions (0.0-1.0)
- **BLNSPEC**: Blend quality specifications
  - Columns: Product names
  - Row tags: Quality properties (RVP, RON, SULFUR, etc.)
  - Values: Specification limits

### Other Tables
- **CRDCUTS**: Crude distillation cut points
- **UNITS**: Unit definitions
- **PROPRNG**: Property ranges
- **CASE**: CASE table (scenario modifications)

## Common Unit Names
- **CDU**: Crude Distillation Unit (Cat1, Cat2)
- **FCC**: Fluid Catalytic Cracker (CCCU)
- **Coker**: Delayed Coker (CDLC)
- **Reformer**: Low-P Reformer (CLPR)
- **HCU**: Hydrocracker (CDHT)
- **DHT**: Diesel Hydrotreater (CDHT)
- **SGTU**: Scanfiner (SGTU or CGTU)

## Cross-Table Dependencies (Generic)
- **CAPS -> SELL**: Capacity changes affect product availability
- **CAPS -> BUY**: Capacity expansion needs feedstock
- **PROCLIM -> CAPS**: Process limits affect unit operation
- **BLNMIX -> SELL**: Blend ratios affect product pools
- **BLNSPEC -> BLNMIX**: Quality specs constrain blend ratios

## Common Operation Patterns

### Capacity Expansion
1. Read CAPS sheet to find unit row tag
2. Modify MAX (and optionally MIN)
3. Check if BUY needs adjustment (feedstock)
4. Check if SELL needs adjustment (product availability)

### Price Change
1. Read SELL sheet to find product row tag
2. Modify PRICE column
3. Check if related products need adjustment

### Process Parameter Change
1. Read PROCLIM sheet to find parameter row tag
2. **ALWAYS set BOTH MIN and MAX**
3. Check if CAPS needs adjustment
4. Check if SELL needs adjustment (product yields)

### Blend Modification
1. Read BLNMIX sheet to find component/product intersection
2. Modify volume fractions
3. Check BLNSPEC for quality constraints
4. Check SELL for product pool limits

## Critical Rules
1. **PROCLIM**: ALWAYS set BOTH MIN and MAX (single bound = no effect)
2. **SLPR column**: Use "HTD HSRN" (NOT "R90" or "RON90")
3. **SLPR values**: NEGATIVE values (material balance)
4. **Unit names**: Use exact tags from CAPS sheet (Cat1, CCCU, CDLC, etc.)
5. **CASE format**: Column alignment is CRITICAL (header col = data col)
