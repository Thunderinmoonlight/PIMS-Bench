# Lesson: Only Write Changed Columns

Observed: Agents that copy all columns from read_sheet() get lower match scores.
- Bad pattern: read_sheet("SELL") -> see PRICE, VPRICE, MIN, MAX, GROUP -> write all 5 columns
- Good pattern: read_sheet("SELL") -> identify PRICE as target -> write only PRICE column

Rule: After read_sheet(), identify which column(s) the scenario asks you to modify. Write ONLY those columns.
