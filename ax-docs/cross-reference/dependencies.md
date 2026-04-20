# Dependency Cross-Reference

## Report-level dependency graph
- `McaCutlistBaseReport` <- controllers (`Cover/Detail/Sum`) <- orchestration (`McaCutlistReports`, `McaCutlistFilesReports`)
- Report DP `McaCutlistReportDP` depends on:
  - Contract `McaCutlistReportContract`
  - Query `McaCutlistQuery`
  - Tables `McaCutlist`, `McaCutlistTmp`
  - Lookup tables/classes (`SalesLine`, `InventTable`, `InventTableModule`, `McaCutlistMoveToAreas`)

## External dependency hotspots
- Query definitions not exported in standalone form.
- Menu-item/security metadata not fully exported in analyzed package.
