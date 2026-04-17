# SYSTEM A — [PROD] Cutlist System Map (Debug Model)

## Scope
Source of truth analyzed:
- `SR423365/code/Production Code/Classes/*`
- `SR423365/code/Production Code/Tables/*`
- `SR423365/code/Production Code/SSRS/SSRSReport_McaCutlistBaseReport.xpo`

This file models **actual production behavior only**.

---

## 1) Entry points and execution surfaces

### [PROD] Create pipeline (records)
- `McaCutlistCreateController` -> `McaCutlistCreateService.process()` -> `processCutlist()` -> `McaCutlistCreate.run()` (or `createMultiTasks()` when batch).  
- `processCutlistRecords()` iterates `SalesLine` query rows, runs `McaBOMSearchCutlist`, loops `McaBOMExplodeTmp`, calls `doCutlistItems()`, then `createCutlistRecord()`.

### [PROD] Module create pipeline (records)
- `McaCutlistCreate_Module` extends create flow for module datasource path (`McaCutlistModuleTmp`).
- `processCutlistRecords()` loops form datasource and calls `doCutlistItems()`.

### [PROD] Report pipeline
- `McaCutlistReportDP.processReport()` dispatches:
  - `processCoverReport()`
  - `processDetailReport()`
  - `processSummaryReport()`
- DP writes TempDB `McaCutlistTmp`, SSRS consumes that dataset.

### [PROD] Output/File pipeline
- `McaCutlistFileController` -> `McaCutlistFileService.process()` -> `McaCutlistFilesReports.run()`.
- `runFiles()` invokes `McaCutlistFile.run()`.
- `runReports()` invokes `McaCutlistReports.run()`.
- `runMarkProcessed()` marks records processed when output actions run.

### [PROD] Delete pipeline
- `McaCutlistDeleteController` -> `McaCutlistDeleteService.process()` deletes selected `McaCutlist` rows in TTS.

---

## 2) Core flow map (record lifecycle)

```text
[PROD]
SalesLine query
  -> McaBOMSearchCutlist (exploded component context)
  -> doCutlistItems() (BOM lookup + fallbacks)
  -> createCutlistRecord()
  -> McaCutlist (persistent)
  -> McaCutlistReportDP
  -> McaCutlistTmp (TempDB)
  -> McaCutlistBaseReport (SSRS)
```

### [PROD] `doCutlistItems()` lookup behavior
- Primary + multiple fallback BOM resolution paths.
- BOM effective dates enforced against offline/required date.
- If no match through all paths -> info log “No cutlist record created …”.

---

## 3) Table roles

### [PROD] `McaCutlist`
Persistent transaction/output table for cutlist lines. Holds dimensions, routing, qty fields, file/report metadata, processed status.

### [PROD] `McaCutlistTmp`
TempDB staging table populated by report DP for SSRS datasets.

### [PROD] supporting tables used in flow
- `BOM`, `BOMVersion`
- `SalesLine`
- `InventDim`, `InventLocation`, `InventTable`
- `McaCutlistParameters`
- `McaCutlistMoveToAreas`, `McaCutlistCutGroup`
- `DocuRef`

---

## 4) Field lineage (critical)

## Qty
- **Set**:
  - [PROD] `McaCutlistCreate.createCutlistRecord()`: `cutlist.Qty = bomRawMaterial.BOMQty`
  - [PROD] `McaCutlistCreate_Module.createCutlistRecord()`: same mapping.
- **Transform**:
  - [PROD] DP mainly copies `Qty` into temp rows.
- **Consumed**:
  - [PROD] displayed/reported in summary/detail sections.

## KitQty
- **Set**:
  - [PROD] salesline path: `cutlist.KitQty = mcaBOMExplodeTmp.BOMQty`
  - [PROD] module path: `cutlist.KitQty = cutlistModuleTmp.Qty`
- **Transform**:
  - [PROD] copied into `McaCutlistTmp.KitQty` in DP.
- **Consumed**:
  - [PROD] SSRS expressions use `KitQty` in totals (e.g. `Sum(Pieces) * KitQty` expression present in report XML).

## Pieces
- **Set**:
  - [PROD] `cutlist.Pieces = bomRawMaterial.McaPieces` in both salesline and module create methods.
- **Transform**:
  - [PROD] `processDetailReport()`: `mcaCutlistTmp.Pieces = real2int(cutlist.Pieces * cutlist.KitQty)`.
  - [PROD] Cover/Summary paths copy raw `cutlist.Pieces`.
- **Consumed**:
  - [PROD] SSRS consumes `McaCutlistTmp.Pieces`; expressions include `Sum(Pieces) * KitQty` and `Sum(Pieces)` depending on section.
  - [PROD] machine file generation also aggregates/sums `Pieces` (outside DP).

## Per_Series
- **Set**:
  - [PROD] **NOT SET** in `McaCutlistCreate`.
  - [PROD] **NOT SET** in `McaCutlistCreate_Module`.
- **Storage**:
  - [PROD] `McaCutlist` and `McaCutlistTmp` contain no `Per_Series` field definitions in Production Code snapshots analyzed.
- **Consumed**:
  - [PROD] SSRS dataset in production snapshot does not expose `Per_Series`.

### Consequence
- [PROD] production output math is `Pieces`/`KitQty` driven only; no per-series divisor path exists in deployed code snapshot.

---

## 5) Known unknowns
- [PROD][UNKNOWN] Exact end-user menu bindings to each controller in live AX instance (not in provided artifacts).
- [PROD][UNKNOWN] Whether other non-exported customizations override report expressions at runtime.

---

For full, stage-by-stage generation and transformation trace through all three report designs,
see `analysis/end-to-end-transformation.md`.
