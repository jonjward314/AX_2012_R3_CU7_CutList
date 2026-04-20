# SR423365 – Cutlist filters, start/report trigger flow, and end-to-end data flow

## Important repository note
- `SR423365/code/Production Code/` currently contains `Classes`, `Tables`, and `SSRS`, but no `Forms` folder.
- For UI/filter mechanics, this analysis uses `SR423365/code/Current Dev Code/Form_McaCutlistRecords.xpo` as the available form source.

## 1) How users filter cutlists from the form

## Base datasource behavior
- Form datasource is `McaCutlist`.
- On datasource init, a default range is added: `McaCutlist.IsCutlistProcessed = No`.
- If opened from a `PWSBuildSchedule` record, the datasource also ranges by `PWSBuildScheduleId = BuildSchedule`.
- If opened with `cutModuleId` arg, datasource ranges by `CutModuleId = cutModuleId`.

## Processed toggle behavior
- `ProcessedCheckBox` controls whether processed records are shown.
- Checked = clear range on `IsCutlistProcessed` (show all).
- Unchecked = enforce `IsCutlistProcessed = checked` (false/no at startup).

## Field-level filtering in the grid
The grid is bound directly to `McaCutlist` fields including:
- `ModelItemId`
- `Prefix`
- `PWSBuildScheduleId`
- `CutGroupId`
- `IsCutlistProcessed`
- `SalesLineRefRecId` via `ReferenceGroup`/`SalesLineReferenceGroup`

Because `McaCutlist` has a table relation from `SalesLineRefRecId -> SalesLine.RecId`, user filters can be applied through related SalesLine identification fields in the reference control (commonly displayed as SalesId in AX reference groups).

## 2) How “start/select cut lists” works

## Load records (create/recreate cutlists)
`LoadRecords.clicked()` does the following:
1. Builds query from `McaCutlistCreateQuery`.
2. Reads current form query filters (`queryFilter`) from `McaCutlist` datasource.
3. Maps filters into create query:
   - `McaCutlist.PWSBuildScheduleId` -> `PWSBuildSchedule.BuildSchedule`
   - `McaCutlist.Prefix` -> `PWSBuildSequenceOrder.McaPrefix`
   - `McaCutlist.ModelItemId` -> `PWSBuildSequenceOrder.ItemId`
4. Calls menu action `McaCutlistCreateAction` with the mapped query.
5. Requeries the `McaCutlist` datasource.

This means users "select scope" in the records form first, then `Load records` translates that scope into the creation pipeline query.

## Files/Reports action (trigger reports/files)
`FilesReports.clicked()`:
1. Takes the current `McaCutlist` query from datasource.
2. Passes that query in `Args.parmObject(...)` to action `McaCutlistReportsFilesForm`.
3. Optionally passes module args (labels/skip validation path).

Then `McaCutlistReportsFilesForm.run()`:
- Builds `McaCutlistFileContract` from dialog selections and query-derived values.
- Pulls first available values from query for:
  - Build schedule
  - Prefix
  - Cut group
- Validates key selectors (prefix/cut group and build schedule unless skipValidation path).
- Executes `McaCutlistFilesReports.run()`.

`McaCutlistFilesReports.run()` sequence:
1. Save original query.
2. Generate files (if selected).
3. Generate reports.
4. Print labels (if selected).
5. Mark processed records.

`McaCutlistReports.markProcessed(query)` updates all query-selected rows to `IsCutlistProcessed = true` via `doUpdate()`.

## 3) Report trigger and query propagation
- Report launcher keeps the same cutlist query scope from form -> reports form -> contract -> report execution.
- `McaCutlistReports.runReport(...)` passes `contract.getQuery()` into report args.
- For detail report, it also adds `UsageType` range and clears `IsCutlistProcessed` range so detail prints can include previously processed rows when needed for that report path.
- `McaCutlistReportDP.processReport()` uses contract query (`parmQuery`) and routes to cover/detail/summary processors.

## 4) Overall field data flow: BOMs -> McaCutlist -> Report dataset

## BOM/source to McaCutlist insert
In `McaCutlistCreate.createCutlistRecord()`, cutlist records are inserted from BOM explosion/BOM raw material context. Key mappings include:
- `SalesLineRefRecId <- salesLine.RecId`
- `ModelItemId <- salesLine.ItemId`
- `ItemId <- activeRawMaterial(...)`
- `Height/Width/Depth <- bomRawMaterial`
- `Qty <- bomRawMaterial.BOMQty`
- `Pieces <- bomRawMaterial.McaPieces`
- `WrkCtrId <- bomRawMaterial.McaMachine`
- `CutGroupId <- getCutGroupId(...)`
- `Prefix <- buildScheduleOrder.McaPrefix`
- `PWSBuildScheduleId <- buildSchedule.BuildSchedule`
- `DateOffLine/DateOnLine <- buildScheduleOrder`
- `MoveToAreaId <- findMoveToArea(...)`
- `BluePrint <- print mapping when enabled`

BOM line selection uses date-effective filtering with `fromDate/toDate` against `offLineDate` (which is overridden by `ReqDate` when present).

## McaCutlist to report temp table
`McaCutlistReportDP` reads `McaCutlist` rows from query and writes `McaCutlistTmp` fields.
Representative mappings:
- `KanbanId <- SalesLine::findRecId(cutlist.SalesLineRefRecId).SalesId`
- `ModelItemId <- cutlist.ModelItemId`
- `Prefix <- cutlist.Prefix`
- `CutGroupId <- cutlist.CutGroupId` (or aggregated cut group string in cover path)
- `Qty/Pieces/Usage/UnitId/Pattern/Notes/PrintNumber` from cutlist
- `Models/Prefixes` computed via helper groupings

Finally SSRS dataset fields bind to `McaCutlistTmp` (including `ModelItemId`, `Prefix`, `CutGroupId`, and many operational columns).

## 5) Requested filter mapping summary
- Cutlist Processed filter: `McaCutlist.IsCutlistProcessed`
- Model filter: `McaCutlist.ModelItemId`
- Prefix filter: `McaCutlist.Prefix`
- Build Schedule filter: `McaCutlist.PWSBuildScheduleId`
- Cut Group filter: `McaCutlist.CutGroupId`
- SalesLine filter path: relation `McaCutlist.SalesLineRefRecId -> SalesLine.RecId`, exposed through reference controls; often surfaced as SalesId in reference group identification.

## 6) Uncertainty / limitation
- The exact production form XPO for `McaCutlistRecords` is not present under `SR423365/code/Production Code/Forms` in this repository snapshot, so UI behavior is derived from the available form export in `Current Dev Code` plus production classes/tables.
