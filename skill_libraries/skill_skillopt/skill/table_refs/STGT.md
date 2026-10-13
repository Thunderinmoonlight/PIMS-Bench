
## Scanfiner Configuration
- Table: STGT
- Column: SCANFINER_MAX
- Description: Maximum Scanfiner throughput
- To enable Scanfiner with MAX=5: Set SCANFINER_MAX = 5

## Coker Configuration
- Table: STGT
- Column: COKER_MAX
- Description: Maximum coker capacity for DCD supply
- To expand coker MAX=25: Set COKER_MAX = 25


## Sheet Name
STGT

## Aliases
- SGTU (common typo in task descriptions)
- STGT (correct sheet name)

## Important
When tasks reference 'SGTU', use sheet name 'STGT'.


## SGTU Transplant Unit Mapping
When performing SGTU transplant operations, the STGT sheet contains the mapping between scenario-specific unit names and their corresponding row tags in other tables.

| Scenario Unit | Mapped Row Tag | Target Table |
|---------------|----------------|--------------|
| Scanfiner | SCF | CAPS |
| Coker | CKR | CAPS |
| DCD | CDLC | CAPS |
