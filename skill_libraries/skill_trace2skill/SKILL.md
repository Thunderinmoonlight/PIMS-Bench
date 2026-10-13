---
name: pims-skillbase
description: "SKILLBASE: structural knowledge + coordination rules + autonomous discovery."
---

# PIMS SKILLBASE — Phase 1-3 Output

## Overview
This SKILLBASE contains knowledge extracted through Phase 1-3:
- Phase 1: Structural and interface knowledge from documentation
- Phase 2a: Coordination patterns from expert CASE records (κ-filtered)
- Phase 2b: Autonomous discovery from documentation

---

## MANDATORY: Task Classification (DO THIS FIRST)

Before reading any sheets, classify the task and read the corresponding skill files:

**IF task mentions**: yield, severity, RON, conversion, coefficient, submodel, S-prefix sheet (SLPR, SCCU, SDHT, SDLC, SHCD, SHYD, etc.)
-> **MUST READ**: `table_refs/submodels.md` AND the specific sheet file (e.g., `table_refs/SLPR.md`, `table_refs/SDHT.md`) BEFORE read_sheet

**IF task mentions**: capacity, expand, unit throughput, MAX, MIN
-> **MUST READ**: `table_refs/CAPS.md`

**IF task mentions**: price, cost, $X per bbl
-> **MUST READ**: `table_refs/SELL.md`, `table_refs/BUY.md`

**IF task mentions**: blend, mix, recipe, component, eligibility
-> **MUST READ**: `table_refs/BLNMIX.md`, `table_refs/BLNSPEC.md`

---

## Part 1: Table Catalog

PIMS contains 85+ tables, organized into the following categories. Detailed definitions are in the `table_refs/` directory。

### Core Tables (Core Tables)

#### CAPS Table (Capacity Bounds)

**Purpose:** Defines unit capacity boundaries

**Columns:**
- `MIN`: min throughput (kbbl/day)
- `MAX`: max capacity (kbbl/day)

**Common Units:**
- `CDHT`: Distillate Hydrotreater (Distillate Hydrotreater)
- `CDLC`: Delayed Coker (Delayed Coker)
- `CCCU`: Catalytic Cracker (Catalytic Cracker)
- `CLPR`: Reformer (Reformer)
- `CHCD`: Hydrocracker (Hydrocracker)
- `CNHT`: Naphtha Hydrotreater (Naphtha Hydrotreater)
- `CKHT`: Kerosene Hydrotreater (Kerosene Hydrotreater)
- `CHYD`: Hydrogen Plant (Hydrogen Plant)
- `CIS4`: C4 Isomerization (C4 Isomerization)
- `CSFA`: Sulfuric Acid Alkylation (Sulfuric Acid Alkylation)

**Usage:**
```
CASE: Expand CDHT capacity
TABLE: CAPS
CDHT.MAX: 15 -> 20
```

**See:** `table_refs/CAPS.md`, `table_refs/equipment_tags.md`

#### SELL Table (Product Sales)

**Purpose:** Defines product sales boundaries and prices

**Columns:**
- `MIN`: min sales volume (kbbl/day)
- `MAX`: max sales volume (kbbl/day)
- `PRICE`: selling price ($/bbl)
- `IPRICE`: Infeasibility price (infeasibility price)

**Common Products:**
- `DSL`: Diesel (Diesel)
- `LSF`: Low Sulfur Fuel (Low Sulfur Fuel Oil)
- `HSF`: High Sulfur Fuel (High Sulfur Fuel Oil)
- `URG`: Unleaded Regular Gasoline (Unleaded Regular Gasoline)
- `UPR`: Unleaded Premium Gasoline (Unleaded Premium Gasoline)
- `JET`: Jet Fuel (Jet Fuel)
- `LPG`: Liquefied Petroleum Gas (Liquefied Petroleum Gas)
- `CKE`: Coke (Coke)
- `SUL`: Sulfur (Sulfur)

**Usage:**
```
CASE: Increase diesel price
TABLE: SELL
PRODUCT.PRICE: old_price -> new_price
```

**See:** `table_refs/SELL.md`, `table_refs/PRICES.md`

#### BLNMIX Table (Blending Rules)

**Purpose:** Defines which components can be blended into which products

**Format:** binary matrix (1 = allowed, 0 = not allowed)

**Common Components:**
- `HCD`: Hydrotreated Cracked Distillate (Hydrotreated Cracked Distillate)
- `CCD`: Catalytic Cracked Distillate (Catalytic Cracked Distillate)
- `DCD`: Delayed Coker Distillate (Delayed Coker Distillate)
- `HTD`: Hydrotreated Distillate (Hydrotreated Distillate)
- `HTK`: Hydrotreated Kerosene (Hydrotreated Kerosene)
- `RFT`: Reformate (Reformate)
- `ALK`: Alkylate (Alkylate)
- `IC4`: Isobutane (Isobutane)
- `NC4`: Normal Butane (Normal Butane)

**Usage:**
```
CASE: Enable DCD blending into DSL
TABLE: BLNMIX
DCD.DSL: 0 -> 1
```

**See:** `table_refs/BLNMIX.md`, `table_refs/BLEND.md`

#### BUY Table (Feedstock Purchase)

**Purpose:** Defines feedstock purchase boundaries

**Columns:**
- `MIN`: min purchase volume (kbbl/day)
- `MAX`: max purchase volume (kbbl/day)
- `COST`: purchase cost ($/bbl)
- `IPRICE`: Infeasibility price (infeasibility price)

**Common Feeds:**
- `CRUDE`: (various crude types)
- `NC4`: Normal Butane (Normal Butane)
- `IC4`: Isobutane (Isobutane)
- `C4m`: Mixed C4s (Mixed C4)
- `H2`: Hydrogen (Hydrogen)

**Usage:**
```
CASE: Increase crude purchase
TABLE: BUY
CRUDE.MAX: old_value -> new_value
```

**See:** `table_refs/BUY.md`, `table_refs/econ_params.md`

### Blending Specification Tables (Blending Specification Tables)

#### BLNSPEC Table (Blending Specifications)

**Purpose:** Defines quality specifications for blend pools

**Columns:** blend pools (URGPOOL, UPRPOOL, JETPOOL, DSLPOOL, LSFPOOL, HSFPOOL)

**Common Specifications:**
- `XSUL`: Sulfur content (Sulfur content, wt%)
- `XRON`: Research Octane Number (Research Octane Number)
- `XMON`: Motor Octane Number (Motor Octane Number)
- `XRVP`: Reid Vapor Pressure (Reid Vapor Pressure, psi)
- `XAPI`: API Gravity (API Gravity)
- `XSPG`: Specific Gravity (Specific Gravity)

**Usage:**
```
CASE: Tighten diesel sulfur spec
TABLE: BLNSPEC
POOL.SPEC: old_value -> new_value
```

**See:** `table_refs/BLNSPEC.md`

#### BLNTARG Table (Blending Targets)

**Purpose:** Defines blend target values (non-binding，for reporting only)

**Columns:** blend pools

**Common Targets:**
- `XRON`: Target RON
- `XMON`: Target MON
- `XSUL`: Target sulfur

**See:** `table_refs/BLNTARG.md`

#### BLNREST Table (Blending Restrictions)

**Purpose:** Defines blending restrictions (inter-component restrictions)

**See:** `table_refs/BLNREST.md`

### Process Control Tables (Process Control Tables)

#### PROCLIM Table (Process Limits)

**Purpose:** Defines MIN/MAX limits for process parameters

**Columns:**
- `MIN`: minimum value
- `MAX`: maximum value

**Common Parameters:**
- `SEV`: Severity (Severity)
- `CONV`: Conversion (Conversion)
- `TEMP`: Temperature (Temperature)
- `PRES`: Pressure (Pressure)

**Usage:**
```
CASE: Increase reformer severity
TABLE: PROCLIM
CLPR.SEV.MAX: 95 -> 100
```

**See:** `table_refs/PROCLIM.md`, `table_refs/process_limits.md`

#### BOUNDS Table (LP Variable Bounds)

**Purpose:** Defines LP variable bounds

**See:** `table_refs/BOUNDS.md`

#### CASE Table (Case Definitions)

**Purpose:** Defines CASE modifications

**See:** `table_refs/CASE.md`

### Crude and Feedstock Tables (Crude and Feedstock Tables)

#### CRDCUTS Table (Crude Cuts)

**Purpose:** Defines crude distillation cut schedule

**See:** `table_refs/CRDCUTS.md`

#### CRDQUAL Table (Crude Quality)

**Purpose:** Defines crude quality parameters

**See:** `table_refs/CRDQUAL.md`

### Equipment and Economics Tables (Equipment and Economics Tables)

#### EQUIP Table (Equipment Parameters)

**Purpose:** Defines equipment parameters

**See:** `table_refs/EQUIP.md`, `table_refs/equipment_params.md`

#### ECON Table (Economic Parameters)

**Purpose:** Defines economic parameters

**See:** `table_refs/ECON.md`, `table_refs/econ_params.md`

#### GROUPS Table (Product Groups)

**Purpose:** Defines product groupings

**See:** `table_refs/GROUPS.md`

### Submodel Tables (Submodel Tables)

PIMS contains multiplesubmodels, each withits own table：

- **SLPR**: Reformer (Reformer)
- **SCCU**: Catalytic Cracker (Catalytic Cracker)
- **SDLC**: Delayed Coker (Delayed Coker)
- **SDHT**: Distillate Hydrotreater (Distillate Hydrotreater)
- **SHCD**: Hydrocracker (Hydrocracker)
- **CHYD**: Hydrogen Plant (Hydrogen Plant)
- **SIS4**: C4 Isomerization (C4 Isomerization)
- **SSFA**: Sulfuric Acid Alkylation (Sulfuric Acid Alkylation)

**See:** `table_refs/submodels.md`, `submodel_refs/`

---

## Part 2: Coordination Rules (Phase 2a)

### Rule 1: CAPS -> SELL Coordination (κ=0.48)

**When modifying CAPS.MAX (Capacity expansion):**
- **Action:** also modify SELL Table
- **Reasoning:** increased capacity requires increased sales bounds
- **Pattern:** When expanding capacity，proportionally increase product sales bounds

**Example:**
```
CASE: Expand CDHT capacity
TABLE: CAPS
CDHT.MAX: 15 -> 20
TABLE: SELL
DSL.MAX: increase proportionally
```

---

### Rule 2: BUY -> CAPS Coordination (κ=0.24)

**When modifying BUY.MAX (purchase boundaries):**
- **Action:** check downstream units have sufficient capacity
- **Reasoning:** increased purchases require sufficient processing capacity
- **Pattern:** When increasing purchases，check downstream capacity

**Example:**
```
CASE: Increase crude oil purchase
TABLE: BUY
CRUDE.MAX: old_value -> new_value
CHECK: CAPS.CDHT.MAX >= required_capacity
```

---

### Rule 3: BLNSPEC -> SELL Coordination (κ=0.13)

**When modifying BLNSPEC:**
- **Action:** Adjust SELL.PRICE to reflect quality changes
- **Reasoning:** tighter specs reduce yield，requiring higher prices
- **Pattern:** tighter specs -> higher prices

**Example:**
```
CASE: Tighten diesel sulfur spec
TABLE: BLNSPEC
POOL.SPEC: old_value -> new_value
TABLE: SELL
DSL.PRICE: increase by 5%
```

---

## Part 3: Autonomous Discovery Skills (Phase 2b)

### Skill 1: Multi-Table Coordination for Capacity Expansion

**Scenario:** Expand unit capacity
**Required Tables:** CAPS, SELL, BUY (sometimes)

**Procedure:**
1. Identify the unit to expand (e.g., CDHT)
2. Modify CAPS.{unit}.MAX to new capacity
3. Check if downstream product sales bounds need increasing
4. If so，proportionally modify SELL.{product}.MAX
5. Check if upstream feedstock purchase bounds need increasing
6. If so，proportionally modify BUY.{feed}.MAX

---

### Skill 2: Blending Route Optimization

**Scenario:** Enable new blending route
**Required Tables:** BLNMIX, BLNSPEC (sometimes)

**Procedure:**
1. Identify component and target product
2. Set BLNMIX.{component}.{product} = 1
3. Check if blend specs need adjustment
4. If so，modify accordingly BLNSPEC

---

### Skill 3: Submodel Yield Adjustment

**Scenario:** Adjust submodel yields (e.g., reformer, FCC, coker)
**Required Tables:** Submodel Tables (e.g., SLPR, SCCU, SDLC)

**Procedure:**
1. Identify submodel table
2. modify yield coefficients
3. Ensure mass balance is maintained

---

### Skill 4: Cross-Unit Coordination

**Scenario:** Coordinate multiple units (e.g., coker + FCC)
**Required Tables:** multiple submodel tables

**Procedure:**
1. Identify units to coordinate
2. Modify yields for each unit
3. Ensure overall material balance

---

## Part 4: CASE Format

### Basic Format
```
CASE {case_number} | {description}
TABLE | {table_name}
{row_name} | {column_name} | {value}
*
```

### Common Patterns

#### Pattern 1: Capacity Expansion
```
CASE: Expand {unit} capacity
TABLE: CAPS
{unit}.MAX: {old_value} -> {new_value}
TABLE: SELL
{product}.MAX: {old_value} -> {new_value}
```

#### Pattern 2: Blending Route Enablement
```
CASE: Enable {component} blending into {product}
TABLE: BLNMIX
{component}.{product}: 0 -> 1
```

#### Pattern 3: Price Adjustment
```
CASE: Adjust {product} price
TABLE: SELL
{product}.PRICE: {old_price} -> {new_price}
```

---

## Reference Files

- `table_refs/`: Detailed table schema and column definitions
- `procedures/`: Step-by-step procedures for common operations
- `equipment_refs/`: Equipment-specific reference data
- `dep_map.md`: cross-table dependency map (κ-filtered)

---


---

## Agent Behavioral Patterns (from trajectory mining, 100 tasks × 4 models)

These are observations about HOW agents work, not domain rules.

### B1: Tool-call ordering matters
- High-match agents: read_skill() -> read_sheet() -> read_cell() -> write_case() -> run_pims()
- Low-match agents: read_sheet() -> write_case() (skip skill reading entirely)
- Observation: 85% of match≥0.8 tasks read at least one skill before writing
- Observation: 0% of match<0.3 tasks read any skill before writing

### B2: Exploration depth correlates with task level
- L1 tasks: 3-5 tool calls sufficient (one table, one column)
- L2 tasks: 5-8 tool calls (two tables, coordination)
- L3 tasks: 8-12 tool calls (multi-table, downstream effects)
- L4-L5 tasks: 12-20 tool calls (cross-unit, full-system)
- Observation: Agents that under-explore on L3+ tasks get match<0.5

### B3: Read-write ratio predicts success
- Successful agents: ~60% read, ~20% write, ~20% verify
- Failed agents: ~30% read, ~50% write, ~20% retry
- Observation: Agents that write too early (before understanding structure) get lower match
- Observation: Agents that re-read the same sheet 3+ times are confused about structure

### B4: Multi-table discovery before writing
- L3+ tasks require modifying 2-4 tables
- Successful agents: discover ALL required tables BEFORE first write_case()
- Failed agents: write first table, then discover they need more tables
- Observation: In a multi-table task, agent wrote SHCU first, then realized CAPS was needed -> too late, match=0.167

### B5: Error recovery patterns
- When run_pims returns infeasible:
  - Good agents: check REPLACE->TABLE, FIX->MAX, percentage->fraction
  - Bad agents: retry with same parameters, or give up
- Observation: 65% of recovered tasks fixed one of these three issues

### B6: Forced write indicates confusion
- When agent reaches step 12+ without writing, it is confused
- Common confusion causes: too many columns to choose from, unclear which table to modify
- Observation: 40% of forced-write tasks get match<0.3

---

## What These Lessons Do NOT Cover

These are behavioral observations about agent patterns. They do NOT provide:

### NOT covered: Specific domain rules
- Which column to use for price changes (PRICE vs VPRICE)
- Which column to use for crude costs (COST vs IPRICE)
- Which column to use for capacity limits (MAX vs FIX)
- Which table to modify for specific scenarios
- What values to write for specific parameters

### NOT covered: CASE format requirements
- TABLE keyword must be uppercase
- Terminator `*` rules
- Column header format (` | TEXT | COL |`)
- Row tag format (PIMS codes, not descriptions)
- SLPR submodel special format (R90/R94/R98, WBAL*)

### NOT covered: Exact table schemas
- What columns exist in each table
- What row tags are valid for each table
- What value ranges are acceptable
- Cross-table dependencies and coordination rules

### NOT covered: PIMS-specific knowledge
- How PIMS interprets CASE entries
- What causes PIMS convergence failures
- How PIMS handles multi-table modifications
- What PIMS does with unknown row tags or columns
