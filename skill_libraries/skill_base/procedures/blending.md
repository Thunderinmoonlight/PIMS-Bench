# Procedure: Blending Operations

## When to use
Task mentions: blend, mix, recipe, component, sulfur spec, RVP, blending limit, blending target

## Five Blending-Related Tables — Do Not Confuse

| Table | Purpose | When to use | Example scenario text |
|-------|---------|-------------|-----------------------|
| BLNMIX | Component eligibility (on/off) | "Enable/add component X to product Y" | "allow IC4 in regular gas" |
| BLNTARG | Ratio limits/targets (upper/lower bounds) | "Set max/min blending ratio" | "max 5% butane" |
| BLNSPEC | Quality specifications (sulfur, RVP, etc.) | "Tighten/change spec for product" | "sulfur spec to 0.05" |
| BLNCAP | Blending capacity/volume limits | "Set blending capacity" | "blending capacity 50 kbbl" |
| ADDITIVE | Additive components (TEL, ethanol, etc.) | "Add additive to product" | "TEL additive 0.5 units" |

**Common confusion**: ADDITIVE vs BLNMIX
- BLNMIX = regular blend components (crudes, intermediates)
- ADDITIVE = special additives (TEL, ethanol, MTBE as additive)
- If the task mentions "additive" specifically -> use ADDITIVE table
- If the task mentions "component" or "blend in" -> use BLNMIX table

**BOUNDS table**: Used for LP variable bounds, NOT blending. If a task mentions "bounds" or "variable limits" in the LP context, use BOUNDS — not any blending table.

**Read the relevant table_ref for column naming conventions before writing.**

## Steps
1. Identify which table: BLNMIX (eligibility), BLNTARG (ratio limits), or BLNCAP (capacity)?
2. Read the table_ref for that table to understand column naming
3. Read the actual sheet to discover available columns
4. Only include columns you are changing

## Templates

**New blend component (BLNMIX)**:
```
TABLE | BLNMIX
 | TEXT | {PRODUCT1} | {PRODUCT2}
{COMPONENT} | {COMPONENT} | 1.0 | 1.0
*
TABLE | BUY
 | TEXT | MAX | COST
{COMPONENT} | {COMPONENT} | {MAX_VAL} | {COST_VAL}
*
```

**Blending ratio limit (BLNTARG)**:
```
TABLE | BLNTARG
 | TEXT | {COLUMN}
{COMPONENT} | {COMPONENT} | {LIMIT_VAL}
*
```
Read BLNTARG table_ref for column naming (UALL/DALL/U{product}/D{product}).

**Quality spec change (BLNSPEC)**:
```
TABLE | BLNSPEC
 | TEXT | {PRODUCT}
{QUALITY_TAG} | {QUALITY_TAG} | {SPEC_VAL}
*
```
