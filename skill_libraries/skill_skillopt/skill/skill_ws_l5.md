## WS-L5 Task Execution

### Step 1: Identify Unit Type from Task Description
Parse the scenario for unit type keywords:
- 'Reformer' or 'RON' -> REF sheet
- 'CDU' or 'Crude' -> CDU sheet
- 'FCC' or 'Cat Cracker' -> FCC sheet

### Step 2: Read the Appropriate Sheet
Use read_sheet with the correct sheet name based on unit type mapping.

### Step 3: Extract Required Data
For Reformer tasks:
- Locate the row matching the RON range (e.g., 98-110)
- Extract capacity value
- Extract UPR price value