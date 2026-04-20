# Table: McaCutlistTmp

## Purpose
TempDB staging table consumed by SSRS datasets.

## Characteristics
- `TableType = TempDB`
- Dataset exposure through `McaCutlistReportDP.getMcaCutlistTmp()`

## Key report fields
`ComponentItemId`, `ComponentName`, `CutGroupId`, `Depth/Width/Height`, `DepthString/WidthString/HeightString`, `Pieces`, `KitQty`, `Usage`, `UnitId`, `MoveToLocation`, `NewPageGroupBy`, `NewWOPageGroupBy`, `Models`, `Prefixes`.
