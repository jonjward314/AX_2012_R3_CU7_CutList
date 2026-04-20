# Class: McaCutlistSumReportController

## Purpose
Controller for `ssrsReportStr(McaCutlistBaseReport, WorkOrderSummary)`.

## Behavior
- `preRunModifyContract()` sets query + `parmPrintSummary(true)`.
- `prePromptModifyContract()` sets query only.
- Standard no-dialog report start behavior in `main()`.
