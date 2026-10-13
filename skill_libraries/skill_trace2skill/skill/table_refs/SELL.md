## SELL Table

### Schema
| Column | Type | Description |
|--------|------|-------------|
| TEXT | string | Equipment/Product identifier (e.g., DSL) |
| GROUP | string | Group NAME (e.g., 'DIST'), NOT numeric group ID. Reference the Groups table to find the group name. |
| PRICE | number | Product price in dollars |

### Important Notes
- The GROUP column takes the group NAME (text), not the numeric group ID.
- To move a product to a different group, use the group's name as listed in the Groups table's group name column.
- Example: To move DSL to the DIST group, use GROUP='DIST', not GROUP=9.