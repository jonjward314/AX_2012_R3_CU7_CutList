# WorkOrderSummary (McaCutlistBaseReport design)

## Overview
- Design rendered by `McaCutlistSumReportController`. **[Confirmed from XPO]**
- Contract flag in `preRunModifyContract`: `parmPrintSummary(true)`. **[Confirmed from XPO]**

## Design-Specific Behavior
- DP applies group-by at model/module/cut group/site/warehouse/salesline/due/kitqty grain. **[Confirmed from XPO]**
- Summary row population writes core identifiers + qty/usage/pieces plus model/prefix display strings. **[Confirmed from XPO]**

## Notes Reconciliation
- Analysis notes indicate DEV changed summary rounding (`Ceiling(Sum(KitQty))`), but production snapshot here only confirms production artifact content. **[From analysis notes] [Confirmed from XPO]**
## Reconciliation Playbook
- [Prod vs Dev math reconciliation by report (SQL + SSRS)](prod-dev-math-reconciliation-by-report.md)

