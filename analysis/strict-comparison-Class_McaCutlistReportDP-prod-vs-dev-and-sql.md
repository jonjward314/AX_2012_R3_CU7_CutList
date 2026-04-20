# Strict comparison: Class_McaCutlistReportDP (PROD vs DEV) + SQL equivalents

## Scope used
- PROD class: `SR423365/code/Production Code/Classes/Class_McaCutlistReportDP.xpo`
- DEV class source used: `SR423365/code/Current Dev Code/SharedProject_J_SR423365_1560_Enhance_Cutsheet_Changes.xpo` (contains the `McaCutlistReportDP` class block)

## Important repository caveat
- `SR423365/code/Current Dev Code/Class_McaCutlistReportDP.xpo` is not a ReportDP class in this snapshot (it contains `McaCutlistCreate_Module`).
- Therefore DEV ReportDP analysis is based on the SharedProject export where `CLASS #McaCutlistReportDP` is present.

## What is "compacted"?
In this context, "compacted" means rows are reduced (grouped/aggregated) before writing to `McaCutlistTmp`.

- Compacting happens where query `GROUP BY` is applied and/or aggregated selection fields are added.
- No compacting means one source `McaCutlist` row produces one `McaCutlistTmp` row.

## Method analysis

### 1) `processCoverReport()`

### PROD behavior
- Applies GROUP BY on:
  - `ModelItemId`, `ModuleItemId`, `Prefix`, `InventSiteId`, `MoveToAreaId`, `ShipToWarehouse`, `SalesLineRefRecId`, `DueDateTime`, `KitQty`
- No explicit aggregate selection fields are added.
- Writes one temp row per grouped result and fills standard fields (`Pieces`, `Qty`, etc.).

### DEV behavior
- Keeps same GROUP BY keys as PROD.
- Adds explicit aggregates/selections:
  - `SUM(Pieces)`
  - `SUM(Qty)`
  - `MAX(PWSBuildScheduleId)`
- Adds sort by `Prefix`, `ModelItemId` (in addition to due date sort).
- Adds new output fields to temp:
  - `Per_Series`
  - `PWSBuildScheduleId`
  - `UnitCounts` (per `(ModelItemId, Prefix)` distinct SalesLine count via helper map)

### What is compacted and why (Cover)
- **Compacted dimensions**: rowset collapses at the GROUP BY grain listed above.
- **Compacted measures in DEV**: `Pieces` and `Qty` are summed at that grain.
- **Reason**: produce one cover-line per grouped work-order bucket while retaining total quantities and adding display metadata (`UnitCounts`, per-series support).

---

### 2) `processDetailReport()`

### PROD behavior
- No GROUP BY in this method.
- Iterates `QueryRun` row-by-row and inserts one `McaCutlistTmp` row per source row.
- Derives detail-specific fields (fraction strings, `NewWOPageGroupBy`, etc.).
- `Pieces` written as `real2int(cutlist.Pieces * cutlist.KitQty)`.

### DEV behavior
- Still no GROUP BY (same per-row pattern).
- Adds new temp fields:
  - `Per_Series = cutlist.Per_Series`
  - `PWSBuildScheduleId = buildSchedules` (prebuilt, global concatenation)
  - `UnitCounts = unitCountsDisplay` (prebuilt display string)
- Keeps piece expansion formula: `real2int(cutlist.Pieces * cutlist.KitQty)`.

### What is compacted and why (Detail)
- **Not compacted at row level**: still one row per selected `McaCutlist` record.
- **Compacted as metadata strings in DEV**:
  - Build schedules are compacted into one string (`getBuildSchedules()` distinct/grouped schedule list).
  - Unit counts are compacted into display strings from deduplicated SalesLine sets by model/prefix.
- **Reason**: detail output remains granular for cutting instructions, while headers/side panels receive condensed contextual summaries.

---

### 3) `processSummaryReport()`

### PROD behavior
- GROUP BY on:
  - `ModelItemId`, `ModuleItemId`, `CutGroupId`, `InventSiteId`, `ShipToWarehouse`, `SalesLineRefRecId`, `DueDateTime`, `KitQty`
- No explicit aggregate selection fields.
- Writes grouped rows to temp with baseline fields.

### DEV behavior
- Keeps same GROUP BY keys as PROD.
- Adds selection/aggregate fields:
  - `SUM(Pieces)`
  - `MAX(PWSBuildScheduleId)`
- Adds extra sort fields (`Prefix`, `ModelItemId`).
- Adds debug `info(...)` calls and keeps `mcaCutlistTmp.Pieces = cutlist.Pieces` assignment.
- Adds output fields:
  - `Per_Series`
  - `PWSBuildScheduleId` (global concatenated schedules)
  - `UnitCounts` (global all-model/prefix display string)

### What is compacted and why (Summary)
- **Compacted dimensions**: grouped to summary bucket grain.
- **Compacted measures in DEV**: `Pieces` is explicitly summed at that grouped grain.
- **Compacted metadata in DEV**: schedules/unit counts are condensed to display strings reused across rows.
- **Reason**: produce summary-level report rows with condensed quantity/context data.

---

## SQL equivalents (from `McaCutlist`)

> Notes:
> - Replace `/* your filter */` with your actual scope (build schedule/prefix/model/etc).
> - These SQL examples replicate **data-shaping intent**, not every AX helper method side effect.
> - SQL Server syntax is used (`STRING_AGG`, window/CTE style).

### A) Cover equivalent

```sql
-- Cover grain + DEV-style aggregation behavior
WITH base AS (
    SELECT *
    FROM McaCutlist
    WHERE /* your filter */ 1=1
)
SELECT
    sl.SalesId                                   AS KanbanId,
    b.WMSLocationId,
    b.InventLocationId,
    b.InventSiteId,
    b.ModelItemId,
    b.ModuleItemId                               AS ComponentItemId,
    itModule.ProductName                         AS ComponentName,
    b.Pattern,
    b.UsageType,
    b.MachineFilename,
    b.Depth,
    b.Width,
    b.Height,
    SUM(b.Qty)                                   AS Qty,             -- DEV explicit sum
    b.Prefix,
    b.WrkCtrId,
    b.DueDateTime,
    b.ShipToWarehouse,
    b.Usage,
    b.UnitId,
    b.KitQty,
    SUM(b.Pieces)                                AS Pieces,          -- DEV explicit sum
    MAX(b.PWSBuildScheduleId)                    AS PWSBuildScheduleId,
    MAX(b.Per_Series)                            AS Per_Series,
    b.Notes,
    b.BluePrint                                  AS PrintNumberId,
    mta.Description                              AS MoveToLocation,
    CONCAT(b.ModelItemId, b.Prefix, b.InventSiteId, COALESCE(mta.Description,''), CONVERT(date, b.DueDateTime)) AS NewPageGroupBy
FROM base b
LEFT JOIN SalesLine sl
       ON sl.RecId = b.SalesLineRefRecId
LEFT JOIN McaCutlistMoveToAreas mta
       ON mta.MoveToAreaId = b.MoveToAreaId
LEFT JOIN InventTable itModule
       ON itModule.ItemId = b.ModuleItemId
GROUP BY
    sl.SalesId,
    b.WMSLocationId,
    b.InventLocationId,
    b.InventSiteId,
    b.ModelItemId,
    b.ModuleItemId,
    itModule.ProductName,
    b.Pattern,
    b.UsageType,
    b.MachineFilename,
    b.Depth,
    b.Width,
    b.Height,
    b.Prefix,
    b.WrkCtrId,
    b.DueDateTime,
    b.ShipToWarehouse,
    b.Usage,
    b.UnitId,
    b.KitQty,
    b.Notes,
    b.BluePrint,
    mta.Description
ORDER BY b.DueDateTime, b.Prefix, b.ModelItemId;
```

### B) Detail equivalent

```sql
-- Detail is row-granular (no group by). Includes DEV metadata compaction helpers.
WITH base AS (
    SELECT *
    FROM McaCutlist
    WHERE /* your filter */ 1=1
),
allSchedules AS (
    SELECT STRING_AGG(DISTINCT b.PWSBuildScheduleId, ' ') AS BuildSchedules
    FROM base b
    WHERE b.PWSBuildScheduleId IS NOT NULL AND b.PWSBuildScheduleId <> ''
),
unitCounts AS (
    -- distinct SalesLine count at (ModelItemId, Prefix)
    SELECT
        b.ModelItemId,
        b.Prefix,
        COUNT(DISTINCT b.SalesLineRefRecId) AS UnitCount
    FROM base b
    WHERE b.SalesLineRefRecId IS NOT NULL
    GROUP BY b.ModelItemId, b.Prefix
)
SELECT
    sl.SalesId                                   AS KanbanId,
    b.WMSLocationId,
    b.InventLocationId,
    b.InventSiteId,
    b.ModelItemId,
    b.ItemId                                     AS RawMatItemId,
    itRaw.ProductName                            AS RawMatName,
    b.ModuleItemId                               AS ComponentItemId,
    itModule.ProductName                         AS ComponentName,
    b.Pattern,
    b.UsageType,
    b.MachineFilename,
    b.Depth,
    b.Width,
    b.Height,
    b.Qty,
    b.Prefix,
    b.WrkCtrId,
    b.DueDateTime,
    b.ShipToWarehouse,
    b.Usage,
    b.UnitId,
    b.KitQty,
    b.CutGroupId,
    CAST(ROUND(b.Pieces * b.KitQty, 0) AS int)   AS Pieces,          -- matches DP detail expansion
    b.Notes,
    b.BluePrint                                  AS PrintNumberId,
    b.Per_Series,
    s.BuildSchedules                              AS PWSBuildScheduleId,
    uc.UnitCount,
    CASE
        WHEN b.UsageType = 1 /* Linear enum value */
            THEN CONCAT(b.ShipToWarehouse, COALESCE(mta.Description,''), b.MachineFilename, b.ItemId)
        ELSE CONCAT(b.ItemId, b.ShipToWarehouse, COALESCE(mta.Description,''))
    END                                           AS NewWOPageGroupBy
FROM base b
LEFT JOIN SalesLine sl
       ON sl.RecId = b.SalesLineRefRecId
LEFT JOIN McaCutlistMoveToAreas mta
       ON mta.MoveToAreaId = b.MoveToAreaId
LEFT JOIN InventTable itRaw
       ON itRaw.ItemId = b.ItemId
LEFT JOIN InventTable itModule
       ON itModule.ItemId = b.ModuleItemId
LEFT JOIN unitCounts uc
       ON uc.ModelItemId = b.ModelItemId
      AND uc.Prefix = b.Prefix
CROSS JOIN allSchedules s
ORDER BY b.DueDateTime, b.Prefix, b.ModelItemId;
```

### C) Summary equivalent

```sql
-- Summary grain + DEV explicit pieces aggregation and schedule condensation.
WITH base AS (
    SELECT *
    FROM McaCutlist
    WHERE /* your filter */ 1=1
),
allSchedules AS (
    SELECT STRING_AGG(DISTINCT b.PWSBuildScheduleId, ' ') AS BuildSchedules
    FROM base b
    WHERE b.PWSBuildScheduleId IS NOT NULL AND b.PWSBuildScheduleId <> ''
),
unitCounts AS (
    SELECT
        b.ModelItemId,
        b.Prefix,
        COUNT(DISTINCT b.SalesLineRefRecId) AS UnitCount
    FROM base b
    WHERE b.SalesLineRefRecId IS NOT NULL
    GROUP BY b.ModelItemId, b.Prefix
)
SELECT
    sl.SalesId                                   AS KanbanId,
    b.WMSLocationId,
    b.InventLocationId,
    b.InventSiteId,
    b.ModelItemId,
    b.ModuleItemId                               AS ComponentItemId,
    itModule.ProductName                         AS ComponentName,
    SUM(b.Qty)                                   AS Qty,
    b.Prefix,
    b.WrkCtrId,
    b.DueDateTime,
    b.ShipToWarehouse,
    b.Usage,
    b.UnitId,
    b.KitQty,
    b.CutGroupId,
    SUM(b.Pieces)                                AS Pieces,          -- DEV sum
    MAX(b.Per_Series)                            AS Per_Series,
    MAX(b.PWSBuildScheduleId)                    AS PWSBuildScheduleId_Max,
    s.BuildSchedules                             AS PWSBuildScheduleId,
    uc.UnitCount
FROM base b
LEFT JOIN SalesLine sl
       ON sl.RecId = b.SalesLineRefRecId
LEFT JOIN InventTable itModule
       ON itModule.ItemId = b.ModuleItemId
LEFT JOIN unitCounts uc
       ON uc.ModelItemId = b.ModelItemId
      AND uc.Prefix = b.Prefix
CROSS JOIN allSchedules s
GROUP BY
    sl.SalesId,
    b.WMSLocationId,
    b.InventLocationId,
    b.InventSiteId,
    b.ModelItemId,
    b.ModuleItemId,
    itModule.ProductName,
    b.Prefix,
    b.WrkCtrId,
    b.DueDateTime,
    b.ShipToWarehouse,
    b.Usage,
    b.UnitId,
    b.KitQty,
    b.CutGroupId,
    s.BuildSchedules,
    uc.UnitCount
ORDER BY b.DueDateTime, b.Prefix, b.ModelItemId;
```

## Concise outcome
- `processCoverReport` and `processSummaryReport` are compacted by GROUP BY in both versions; DEV adds explicit aggregates and extra compacted display metadata.
- `processDetailReport` remains non-grouped row-level output in both versions, but DEV injects compacted/global metadata strings and per-series fields.
