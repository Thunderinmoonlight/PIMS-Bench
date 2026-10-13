## PROCLIM Table - Process Limits

This table defines operating parameters for process units.

### IMPORTANT: PROCLIM column headers are NUMERIC VALUES, not MIN/MAX

The PIMS PROCLIM sheet uses numeric column headers representing operating points:
```
ZSEV | Reformer Severity | 90.0 | 100.0
ZCON | FCC Conversion    | 70.0 |  73.0
```
- `90.0` and `100.0` are severity levels (column headers in the actual sheet)
- `70.0` and `73.0` are conversion values at those severity levels

### How to write PROCLIM CASE entries

Use the numeric column headers from the sheet:
```
TABLE | PROCLIM
 | TEXT | 90.0 | 100.0 |
ZSEV | Reformer Severity | 95.0 | 108.0 |
*
```

### Common Row Identifiers
| Row Code | Description | Typical Range |
|----------|-------------|---------------|
| ZSEV | Reformer Severity (RON) | 88-110 |
| ZCON | FCC Conversion (LV%) | 68-80 |

### Always read_sheet("PROCLIM") first to see the actual column headers!
The numeric headers vary by model. Check before writing.