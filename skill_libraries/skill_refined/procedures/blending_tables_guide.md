# Blending Table Modification Guide

PIMS uses several blending-related tables. Understanding their structure is critical for blending tasks.

## BLNMIX (Blend Recipe Table)
Controls which components can be blended into which products.

### Structure
- Column A: Row tag (component code, e.g., IC4, NC4, LSR)
- Column B: TEXT (component name)
- Remaining columns: Product codes (e.g., RGL, DSL, LSF, HSF)

### Values
- **0** = component NOT eligible for this product (disabled)
- **1** = component IS eligible (enabled)
- **Decimal (e.g., 0.05)** = upper blending limit (volume fraction)

### How to Enable a Component for Blending
To allow isobutane (IC4) in diesel (DSL):
```
TABLE | BLNMIX
 | TEXT | DSL |
IC4 | Isobutane | 1 |
*
```

To set an upper blending limit of 5%:
```
TABLE | BLNMIX
 | TEXT | DSL |
IC4 | Isobutane | 0.05 |
*
```

### Critical: Read First!
Always call `read_sheet("BLNMIX")` first to see:
- Which components exist (row tags)
- Which products are columns
- Current eligibility values

## BLNTARG (Blend Target Table)
Controls target properties for blended products.

### Common Columns
- **BEN** — Blend endpoint number
- **BLNSPC** — Blend specification reference
- Product-specific property targets

## BLNCAP (Blend Capacity Table)
Controls total blending capacity.

### How to Set Blend Capacity
```
TABLE | BLNCAP
 | TEXT | MAX |
BLEN | Gasoline Blend Capacity | 50.0 |
*
```

## Common Mistakes to Avoid
- Don't confuse BLNMIX eligibility (0/1) with blending limits (decimals)
- Don't forget to also update BUY table for new component purchases
- Product codes: RGL=Regular Gasoline, PGL=Premium, DSL=Diesel, JET=Jet, HSF=High Sulfur Fuel, LSF=Low Sulfur Fuel
