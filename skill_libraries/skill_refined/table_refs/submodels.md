# Submodel Operations — Generic Rules (Model-Agnostic)

## 1.

****: SUBMODS Table sheet 。 sheet S 。

```
Step 1: read_sheet("SUBMODS") -> ColumnTable
Step 2:
```

**CAPS -> sheet **:
- : C， S
- : read_sheet("SUBMODS") sheet

## 2. Row

 sheet RowType（ sheet ）:

| Row | Type | Description |
|--------|------|------|
| WBAL* | | Value=, Value= |
| WBALLOS | / | WBAL Row≈0 |
| CCAP* | | 1.0, CAPS Table |
| ZLIM* | | severity/conversion |
| E* | Row | 、 |

## 3. Modify

```
Step 1: read_sheet("SUBMODS") ->
Step 2: read_sheet -> Table
Step 3: WBAL* Row(/) Column
Step 4: Modify WBAL* RowValue
Step 5: WBALLOS  ！
Step 6: write_case
```

### （Key）

** WBAL* Row， WBALLOS:**

```
WBALLOS = -( WBAL* Row)
```

****: + + Loss = 0

**Example**: Modify:
```
WBALFEED: +1.0000 WBALPROD1: -0.8500
WBALPROD2: -0.1200 WBALLOS: -0.0300
 = 1.0 - 0.85 - 0.12 - 0.03 = 0 [ok]
```

 PROD1 -0.8700 :
```
 WBALLOS = -(1.0 + (-0.87) + (-0.12)) = -0.01
```

## 4. Column（ sheet ）

### A: Column(BAS)
sheet Column BAS:
```
TABLE | {}
 | TEXT | BAS |
WBALxxx | WBALxxx | {Value} |
WBALLOS | WBALLOS | {Value} |
*
```

### B: ValueColumn
ColumnValue( 975, 920)，Table:
```
TABLE | {}
 | TEXT | {ValueColumn} |
WBALxxx | WBALxxx | {Value} |
*
```

### C:
 WBAL* RowColumn，Value:
```
TABLE | {}
 | TEXT | WBALaaa | WBALbbb | WBALccc |
WBALaaa | WBALaaa | {Value} | | |
WBALbbb | WBALbbb | | {Value} | |
WBALccc | WBALccc | | | {Value} |
WBALLOS | WBALLOS | {loss_a} | {loss_b} | {loss_c} |
*
```

****: sheet WBAL* RowRowTable -> C

### Example

**Example A: 3-mode severity sheet (modes: 80, 85, 90)**
```
TABLE | {SHEET_NAME}
 | TEXT | R80 | R85 | R90 |
WBALR80 | {description} | -0.850 | | |
WBALR85 | {description} | | -0.875 | |
WBALR90 | {description} | | | -0.900 |
WBALLOS | Loss | 0.008 | 0.011 | 0.014 |
*
```
**Key**:
- Column mode (R80, 80)
- mode Row (WBALR80, WBALR85, WBALR90)
- RowColumnValue（Column）
- Balance Row (WBALLOS) ColumnValue

**Example B: 2-mode sheet (modes: 100, 110)**
```
TABLE | {SHEET_NAME}
 | TEXT | M100 | M110 |
WBALM100 | {description} | -0.920 | |
WBALM110 | {description} | | -0.945 |
WBALLOS | Loss | 0.012 | 0.015 |
*
```
**Key**:
- Column mode (M100, M110)
- mode WBAL* Row
- Balance RowColumnValue

**Example C: Column sheet (BAS Column)**
```
TABLE | SDHT
 | TEXT | BAS |
WBALHTD | Htd Distillate | -0.975 |
WBALHYL | Hydrogen | -0.0065 |
*
```
**Key**:
- Column (BAS)
- WBAL* RowValue
- balance Row（Column）

**Example D: mode severity sheet**
 "Reduce yield coefficients to {val1}, {val2}, {val3} for modes {mode1}, {mode2}, {mode3} respectively":
```
TABLE | {SHEET_NAME}
 | TEXT | {COL1} | {COL2} | {COL3} |
WBAL{MODE1} | {description} | {val1} | | |
WBAL{MODE2} | {description} | | {val2} | |
WBAL{MODE3} | {description} | | | {val3} |
WBALLOS | Loss | {loss1} | {loss2} | {loss3} |
*
```
**CRITICAL Key**:
- ** mode WBAL* Row** (WBAL{MODE1}, WBAL{MODE2}, WBAL{MODE3})
- **RowColumnValue，Column**（ValueRow）
- Balance Row (WBALLOS) ColumnValue
- Column mode （ read_sheet ）

**Example E: Yield chain issue**
 "After yield adjustment, product yields decreased. Diagnose and fix yield chain" ：
```
TABLE | {SUBMODEL_SHEET}
 | TEXT | {COL_CODE} |
WBAL{CODE1} | {product1} | {value1} |
WBAL{CODE2} | {product2} | {value2} |
*
TABLE | BLNMIX
 | TEXT | {PRODUCT1} | {PRODUCT2} |
{COMPONENT} | {COMPONENT} | 1.0 | 1.0 |
*
TABLE | SELL
 | TEXT | PRICE |
{PRODUCT1} | {PRODUCT1} | {price1} |
{PRODUCT2} | {PRODUCT2} | {price2} |
*
```
**CRITICAL Key**:
- **Yield chain issue Table**: submodel sheet (yield coefficients) + BLNMIX (blending eligibility) + SELL (prices)
- **Table** — BLNMIX SELL
- Submodel sheet WBAL* Row
- BLNMIX Set blending eligibility (1.0 = enabled)
- SELL

## 5.

1. ** read_sheet** — RowColumn，
2. ** WBAL WBALLOS** —
3. **Column** — sheet Column
4. **ValueRange** — WBAL -1.0 ~ +1.0
5. **** — Value=, Value=，
6. **Row** — read_sheet ，
