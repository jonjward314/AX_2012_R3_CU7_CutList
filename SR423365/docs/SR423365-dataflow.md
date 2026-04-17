# SR423365 — Software & Data Flow

**Feature:** Enhance Cutsheet PDFs — Add Per-Series Quantity & Piece Count Tracking
**Jayco Change ID:** 1560
**Author:** Ward, Jonathon | Documented: 2026-04-14

---

## 1. Overview

SR423365 adds two new fields — **Per_Series** and **Pieces** — to the cutlist subsystem so
that the SSRS cutsheet report can calculate and display per-series quantities.

| Field | Source BOM Field | Type | Purpose |
|-------|-----------------|------|---------|
| `Per_Series` | `BOM.BOMQtySerie` | REAL | Quantity produced per manufacturing series |
| `Pieces` | `BOM.McaPieces` | INT | Number of pieces per BOM line |

The calculated report expression is:
```
Ceiling( Sum(Pieces × KitQty) / Per_Series )
```
…rounded up, with `Per_Series = 0` handled as 1 (safe divide).

---

## 2. Component Map

```
P:\Repository\SRs\SR423365\code\
│
├── Table_McaCutlist.xpo               — Persistent cutlist records (+Per_Series, +Pieces)
├── Table_McaCutlistTmp.xpo            — TempDB staging for report DP (+Per_Series, +Pieces)
│
├── Class_McaCutlistCreate.xpo         — Base creation class (sales-order path)
├── Class_McaCutlistCreate_Module.xpo  — Subclass for module path
├── Class_McaCutlistReportDP.xpo       — SSRS Report Data Provider
│
├── Form_McaCutlistRecords.xpo         — UI grid form (+Per_Series readonly, +Pieces columns)
│
├── SSRSReport_McaCutlistBaseReport.xpo — SSRS RDL report (+Per_Series, +Pieces, +calcs)
└── VSProject_AXModel_McaCutlistReport.xpo — VS reporting project config
```

---

## 3. Table Schema Changes

### 3.1 McaCutlist (Persistent Table)

| Field | EDT | Type | SR423365 Change |
|-------|-----|------|-----------------|
| `Per_Series` | `BOMQtySerie` | REAL | **Added** |
| `Pieces` | `McaPieces` | INT | **Added** |
| (all other fields) | — | — | Unchanged |

Selected key pre-existing fields for reference:

| Field | Type | Description |
|-------|------|-------------|
| `SalesLineRefRecId` | INT64 | Reference to sales order line |
| `CutModuleId` | STRING | Module identifier (module path) |
| `ModelItemId` | STRING | Parent model item |
| `ComponentItemId` | STRING | Raw material component item |
| `ItemId` | STRING | Active variant item ID |
| `Height / Width / Depth` | REAL | Cut dimensions |
| `Qty` | REAL | Total quantity |
| `KitQty` | REAL | Kit (model-level) quantity |
| `WrkCtrId` | STRING | Machine / work center |
| `CutGroupId` | STRING | Cut group classification |
| `IsCutlistProcessed` | NoYes | Processing status flag |
| `PWSBuildScheduleId` | STRING | Production schedule ID |
| `InventSiteId / InventLocationId` | STRING | Site and warehouse |
| `DueDateTime / DateOffLine / DateOnLine` | DATE/DATETIME | Schedule dates |

### 3.2 McaCutlistTmp (TempDB — Report Staging)

Mirrors McaCutlist plus report-specific calculated fields:

| Field | Notes |
|-------|-------|
| `Per_Series` | **Added** — copied from McaCutlist |
| `Pieces` | **Added** — copied from McaCutlist |
| `DepthString / HeightString / WidthString` | Formatted dimension strings |
| `Models / Prefixes / UnitCounts` | Aggregated display values |
| `ComponentName / RawMatName` | Item names |
| `NewPageGroupBy / NewWOPageGroupBy` | Report group-break keys |
| `CutSizeSeperator` | Dimension separator |

---

## 4. Data Flow

### 4.1 High-Level Flow

```
BOM Table (source data)
        │
        │  BOMQtySerie → Per_Series
        │  McaPieces   → Pieces
        ▼
McaCutlistCreate / McaCutlistCreate_Module
  (creation classes — populate McaCutlist record)
        │
        ▼
McaCutlist (persistent table)
        │
        ├──► Form: McaCutlistRecords (UI view/edit)
        │
        └──► McaCutlistReportDP (data provider)
                    │
                    ▼
             McaCutlistTmp (staging)
                    │
                    ▼
        McaCutlistBaseReport (SSRS)
                    │
                    ▼
           Printed / PDF Cutsheet
```

### 4.2 Sales-Order Path — McaCutlistCreate.createCutlistRecord()

```
SalesLine (RecId, InventDimId, DueDate...)
    │
    └─ doCutlistItems() — 8-table join query
            │
            ├─ ReqItemTable (item coverage → site/location)
            ├─ InventLocation (warehouse)
            ├─ InventDim [primary] (site, location, WMS)
            ├─ BOMVersion (model BOM header)
            ├─ InventDim [BOM version]
            ├─ BOM raw-material line
            │     ├─ BOMQty       → Qty
            │     ├─ BOMQtySerie  → Per_Series  ◄── SR423365
            │     ├─ McaPieces    → Pieces       ◄── SR423365
            │     ├─ Height / Width / Depth
            │     ├─ McaMachine   → WrkCtrId
            │     └─ McaPattern   → Pattern
            ├─ InventDim [raw material]
            └─ InventTable (McaUsageType, UnitId)

    Per BOM line → createCutlistRecord():
        ├─ DocuRef lookup    (notes)
        ├─ InventDim lookup  (site/location)
        ├─ CutGroupId        (static lookup McaCutlist::lookupCutGroup)
        ├─ MoveToAreaId      (static lookup McaCutlist::lookupMoveToArea)
        ├─ BluePrint         (lookup via McaEcoResProductPrints if PrintNumber set)
        └─ McaCutlist.insert()
```

**Date filtering on BOM lines:**
```
(BOM.fromDate <= DateOffLine OR !BOM.fromDate)
AND
(BOM.toDate   >= DateOffLine OR !BOM.toDate)
```

### 4.3 Module Path — McaCutlistCreate_Module.createCutlistRecord()

Simplified variant — reads `McaCutlistModuleTmp` datasource instead of building
a BOM query from scratch. Overrides:

- Sets `CutModuleId` (not `SalesLineRefRecId`)
- Reads `ModelItemId`, `PWSBuildScheduleId`, `MoveToAreaId`, `ShipToWarehouse`,
  `Prefix`, `Qty`, `LabelIdNum` from the module tmp table
- Adds `Pieces = bomRawMaterial.McaPieces` (**SR423365**)
- Does **not** set `Per_Series` (module path omission — may be gap to verify)

Transaction wrapper: `processCutlistRecords()` wraps all inserts in TTS.

### 4.4 Report Path — McaCutlistReportDP → McaCutlistBaseReport

```
McaCutlistReportDP.processReport()
    │
    ├─ Query McaCutlist (filtered by schedule/module/date/processed flag)
    ├─ For each record:
    │    Copy fields into McaCutlistTmp row
    │    Format dimension strings
    │    Calculate aggregates (Models, Prefixes, UnitCounts)
    └─ McaCutlistTmp ready for SSRS
            │
            ▼
   McaCutlistBaseReport (SSRS RDL)
            │
            ├─ Grouping: Model → Prefix → CutGroup
            ├─ Detail rows: one per McaCutlistTmp record
            │
            ├─ SR423365 Expression 1 — Calculated quantity per series:
            │    =Ceiling(
            │       Sum(Fields!Pieces.Value * Fields!KitQty.Value)
            │       /
            │       IIf(IsNothing(Max(Fields!Per_Series.Value))
            │           OrElse Max(Fields!Per_Series.Value) <= 0,
            │         1,
            │         Max(Fields!Per_Series.Value))
            │     )
            │
            └─ SR423365 Expression 2 — Per_Series display:
                 =IIf(IsNothing(Fields!Per_Series.Value)
                      OrElse Fields!Per_Series.Value <= 0,
                   "Not Set",
                   Fields!Per_Series.Value)
```

---

## 5. UI Changes — Form_McaCutlistRecords

Grid tab — new columns added (SR423365):

| Control | Type | Bound Field | Behaviour |
|---------|------|-------------|-----------|
| `McaCutlist_Pieces` | IntEdit | `McaCutlist.Pieces` | Editable |
| `McaCutlist_PerSeries` | RealEdit | `McaCutlist.Per_Series` | **Read-only** |

Default filter: `IsCutlistProcessed = No` (ProcessedCheckBox toggles).

Action buttons (unchanged):

| Button | Action |
|--------|--------|
| LoadRecords | Launches `McaCutlistCreateQuery` to create records |
| CreateFile | Invokes `McaCutlistFileAction` for machine file generation |
| FilesReports | Opens `McaCutlistReportsFilesForm` |
| DeleteRecords | Custom delete dialog |

---

## 6. Debug Instrumentation

`McaCutlistCreate.createCutlistRecord()` contains a UAT validation popup:

```
"UAT PerSeries Validation [Create]
 BomRecId=%1  BOMQty=%2  BOMQtySerie=%3
 CutlistQty=%4  CutlistKitQty=%5  Per_Series=%6"
```

> **Note:** This popup should be removed or disabled before production deployment (Step 10).

---

## 7. External Table Dependencies

| Table | Used For |
|-------|---------|
| `SalesLine` | Sales order line — top-level driver |
| `BOMVersion` | BOM header (model) |
| `BOM` | Raw material BOM lines — primary data source |
| `InventDim` | Site / location / WMS dimensions |
| `InventTable` | Item master (usage type, unit ID) |
| `InventLocation` | Warehouse master |
| `ReqItemTable` | Item coverage — derives BOM site |
| `DocuRef` | Attached notes |
| `PWSBuildSchedule` | Production schedule header |
| `PWSBuildSequenceOrder` | Sequence/order data |
| `McaBOMExplodeTmp` | Exploded BOM structure (temp) |
| `McaCutlistParameters` | System configuration |
| `McaEcoResProductPrints` | Print number references |

---

## 8. Potential Gap — Module Path Per_Series

`McaCutlistCreate_Module.createCutlistRecord()` sets `Pieces` but **does not set
`Per_Series`**. The base class `McaCutlistCreate` sets both. Verify whether:

1. The module path intentionally omits `Per_Series` (all module items are one-per-series), or
2. `Per_Series` should also be set in the module subclass (missing assignment).

Confirm with Kelly Gordon / Rhonda Rowe during Step 6 testing.

---

## 9. TFS Changeset Summary

| CS | Date | Notes |
|----|------|-------|
| 7673 | 2026-01-20 | Initial resolve |
| 7675 | 2026-01-21 | DEV-AX-12 → DEV deploy |
| 7707 | 2026-02-24 | Redeploy |
| 7713 | 2026-02-25 | Forced redeploy |
| 7723 | 2026-03-10 | **Piece Fields added to Selection** |
| 7731 | 2026-03-20 | Redeploy (ref CS 7725) |
| 7735 | 2026-03-23 | Redeploy |
| 7737 | 2026-03-24 | DEV-AX-JDEV12 → DEV (current in DEV) |
