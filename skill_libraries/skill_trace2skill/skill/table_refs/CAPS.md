## CAPS Table - Capacity Limits

This table defines throughput capacities for process units.

### Equipment Codes (EXACT codes from PIMS Weight Sample model)

**Crude Processing:**
| Code | Description | Units |
|------|-------------|-------|
| Cat1 | Crude Unit #1 | B/D |
| Cat2 | Crude Unit #2 | B/D |

**Vacuum Processing:**
| Code | Description | Units |
|------|-------------|-------|
| CVU1 | Vac Unit #1 | BPD |
| CVU2 | Vac Unit #2 | BPD |

**Naphtha Processing:**
| Code | Description | Units |
|------|-------------|-------|
| CNSP | Naph Splitter | BPD |
| CNHT | Naph Hydrotrt | BPD |
| CLPR | Low-P Reformer | BPD |

**Middle Distillate Processing:**
| Code | Description | Units |
|------|-------------|-------|
| CKHT | Kero Hydrotrt | BPD |
| CDHT | Dist Hydrotrt | BPD |

**Conversion Units:**
| Code | Description | Units |
|------|-------------|-------|
| CCCU | Cat Cracker (FCC) | BPD |
| CHCD | Hydrocrack Dist | BPD |
| CDLC | Delayed Coker | BPD |

**Support Units:**
| Code | Description | Units |
|------|-------------|-------|
| CIS4 | C4 Isom | BPD |
| CSFA | Sulf Acid Alky | BPD |
| CHYD | H2 Plant | MMSCFD |
| CTGT | Tail Gas Trt | LT/D |

### Column Structure
| Column | Description |
|--------|-------------|
| TEXT | Equipment code |
| MIN | Minimum capacity (optional, forces utilization) |
| MAX | Maximum capacity limit |

### Notes
- Use the exact equipment codes listed above
- Equipment codes are case-sensitive
- Setting only MAX may have no effect if the optimizer is already below MAX; set MIN to force a different operating point