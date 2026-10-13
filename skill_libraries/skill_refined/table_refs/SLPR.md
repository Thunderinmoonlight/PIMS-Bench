# SLPR — Reformer Submodel Sheet

## Purpose
The SLPR sheet defines reformer yield coefficients for each RON severity mode.

## Key Structure Facts
- Column headers are RON severity codes (e.g., R90, R94, R98). Use these EXACT codes as column names in CASE entries.
- Each severity mode has its own ROW. The row tag typically combines a prefix (e.g., WBAL) with the severity code.
- There is usually a separate loss/balance row that has values across ALL columns.
- Yield coefficients for products are typically NEGATIVE (representing consumption from feed pool).

## How Yield Modification Works
When modifying reformer yields, you are replacing the coefficient that describes how much of a product is generated (or consumed) per unit of feed at each severity level.

**Reading the sheet**: Call read_sheet("SLPR") first. Observe:
- Which columns represent which severity modes (the column headers)
- Which rows represent which products or balance terms (the row tags)
- Whether each product row has a value in ONE column (sparse) or across ALL columns

**Writing the modification**:
- For each product whose yield you're changing, find its row in the sheet
- Set the new coefficient value in the column matching the target severity mode
- Leave other columns blank for that row (if the sheet is sparse)
- If the scenario mentions multiple severity modes, each gets its own row — do NOT merge them into one row
- Always include the balance/loss row if adjusting product yields, with values across all affected columns

**Row tag convention**: Copy the exact row tags from read_sheet. If the sheet uses a prefix pattern (e.g., all rows start with the same letters), your CASE entries must follow the same pattern.

## Common Scenario Patterns
- "Reduce yield to X for mode Y" -> find the row for mode Y's product, set the coefficient in that mode's column only
- "Adjust multiple severity modes" -> write separate rows for each mode, each with value only in its own column
- "Maintain material balance" -> include the balance/loss row with adjusted values
