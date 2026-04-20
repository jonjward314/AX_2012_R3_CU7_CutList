# WorkOrderDetail (McaCutlistBaseReport design)

## Overview
- Design rendered by `McaCutlistDetailReportController`. **[Confirmed from XPO]**
- Contract flag: `parmPrintDetail(true)`. **[Confirmed from XPO]**

## Design-Specific Behavior
- No DP `GROUP BY`; iterates selected cutlist rows. **[Confirmed from XPO]**
- Converts size values to fractional strings and strips machine-file path for display. **[Confirmed from XPO]**
- Calculates `Usage` with `usageCalcRounding()` and overrides UOM with invent-module unit. **[Confirmed from XPO]**
- Computes `NewWOPageGroupBy` differently for Linear vs Sheet usage types. **[Confirmed from XPO]**

## Known Risks
- Potential quantity inflation when expanded `Pieces` is multiplied again in RDL expressions. **[From analysis notes]**
