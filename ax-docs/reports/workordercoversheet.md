# WorkOrderCoverSheet (McaCutlistBaseReport design)

## Overview
- Design rendered by `McaCutlistCoverReportController`. **[Confirmed from XPO]**
- Uses same RDP dataset `McaCutlistTmp`. **[Confirmed from XPO]**

## Design-Specific Behavior
- Contract flag: `parmCoverSheet(true)` in controller prePrompt/preRun. **[Confirmed from XPO]**
- Data grouped in DP by model/module/prefix/site/move-to/warehouse/salesline/due/kitqty. **[Confirmed from XPO]**
- Cover-specific page key: `NewPageGroupBy`. **[Confirmed from XPO]**

## Known Gaps
- Menu item name/path for this design is **Not determinable from provided XPO/MD**.
- Security role mapping is **Not determinable from provided XPO/MD**.
## Reconciliation Playbook
- [Prod vs Dev math reconciliation by report (SQL + SSRS)](prod-dev-math-reconciliation-by-report.md)

