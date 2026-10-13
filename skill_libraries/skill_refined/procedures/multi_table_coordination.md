# Multi-Table Coordination Rules

When a task involves multiple tables, you MUST modify ALL relevant tables in a single write_case() call.

## Common Coordination Patterns

### Price + Capacity Tasks
If scenario mentions both prices AND capacities:
- SELL table: change PRICE column
- CAPS table: change MIN/MAX columns
- Always include BOTH tables in one write_case()

### Purchase + Price Tasks
If scenario mentions crude purchase limits AND costs:
- BUY table: change MAX (limit) and COST (price) columns in the SAME entry
- SELL table: change product PRICE if mentioned
- Include both BUY and SELL if both are mentioned

### Blending + Purchase + Price Tasks
If scenario mentions blending components:
- BLNMIX table: set eligibility (1=enabled, 0=disabled) and upper limits
- BUY table: set purchase limit (MAX) and cost (COST) for the component
- SELL table: change product PRICE if mentioned
- BLNTARG table: set target properties if mentioned

### Submodel + Capacity + Price Tasks
If scenario mentions yield adjustments:
- Submodel sheet (SLPR/SCCU/SDHT/etc.): adjust yield coefficients
- CAPS table: set capacity (MIN/MAX) for the processing unit
- SELL table: change product PRICE if mentioned

## Shutdown/Turnaround Pattern
When scenario says "shut down" or "turnaround" for a unit:
- CAPS table: set BOTH MIN=0 AND MAX=0 for that unit
- This completely disables the unit in the LP model

## How to Identify ALL Required Tables
1. Read the scenario carefully
2. For each action mentioned, identify the target table:
   - Price changes -> SELL
   - Purchase limits/costs -> BUY
   - Capacity changes -> CAPS
   - Blending limits/eligibility -> BLNMIX
   - Blend targets -> BLNTARG
   - Blend capacity -> BLNCAP
   - Processing limits -> PROCLIM
   - Yield adjustments -> SLPR/SCCU/SDHT/SDLC/SHCD
   - Additives -> ADDITIVE
3. **Trace downstream effects**: When a scenario mentions "yield chain", "downstream", or "diagnose", ask:
   - Does changing this yield affect what gets blended? -> check BLNMIX
   - Does it affect product output prices? -> check SELL
   - Does it affect purchase needs? -> check BUY
4. Call read_sheet() for EACH identified table
5. Write ALL modifications in ONE write_case() call

## Yield Chain Diagnosis Pattern
When scenario says "fix yield chain" or "diagnose yield issue":
- Submodel sheet: fix the yield coefficients
- BLNMIX: update blending eligibility for affected intermediate products
- SELL: update prices for affected final products
- Always trace: submodel change -> intermediate product -> blending -> final product price
