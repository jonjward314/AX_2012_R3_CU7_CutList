# Class: McaCutlistReportDP

## Type
`SrsReportDataProviderPreProcessTempDB` with attributes:
- `SRSReportQueryAttribute(querystr(McaCutlistQuery))`
- `SRSReportParameterAttribute(classstr(McaCutlistReportContract))`

## Key Methods
- `getMcaCutlistTmp()` dataset provider.
- `processReport()` dispatcher.
- `processCoverReport()` grouped cover data path.
- `processDetailReport()` detailed per-row path.
- `processSummaryReport()` grouped summary path.
- `getQueryRun()`, `getModelPrefixes()`, `filename()` helpers.

## Key Dependencies
`McaCutlist`, `McaCutlistTmp`, `SalesLine`, `InventTable`, `InventTableModule`, `McaCutlistMoveToAreas`, `SysQuery`.

## Functional Notes
- Central report behavior class; any quantity/grouping changes here alter SSRS output directly.
- Production code includes 2024 note adjusting detail UOM source from cutlist unit to `InventTableModule` unit.
