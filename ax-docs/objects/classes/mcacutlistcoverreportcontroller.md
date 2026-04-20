# Class: McaCutlistCoverReportController

## Purpose
Controller for `ssrsReportStr(McaCutlistBaseReport, WorkOrderCoverSheet)`.

## Behavior
- `main()` sets report name, no dialog, no SysLastValue, passes args.
- `prePromptModifyContract()` and `preRunModifyContract()` set query from args and `parmCoverSheet(true)`.
- `dialogShow()/dialogClose()` customized for multi-viewer behavior.
