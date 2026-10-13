
# Scenario Transplant Procedure

## SGTU Transplant
1. Read the **SGTU** sheet to load all scenario parameters.
2. Identify the target tables in the current case that correspond to the SGTU parameters:
   - Scanfiner MAX -> typically in a unit capacity or process limit table
   - Coker MAX -> typically in a unit capacity or process limit table (for DCD supply, set coker max to 25)
   - JET product -> set to desired price)
3. Apply the values by modifying the appropriate cells in the active case tables.

## Common Pitfalls
- Do not confuse 'STGT' with 'SGTU' - the correct sheet name is **SGTU**.
- The SGTU sheet contains the scenario definition; the actual application requires modifying the corresponding tables in the current case (e.g., Caps, ProcLim, SELL).
