# End-to-End Cutlist Data Transformation Model (PROD vs DEV)

This is a **working-session debugging model** (not end-user documentation).  
Goal: trace data generation and transformation from creation through `McaCutlist` persistence and out through all 3 report paths.

---

## 0) Report surfaces in scope (the 3)

The system produces three SSRS designs from `McaCutlistBaseReport`:
1. **WorkOrderSummary**
2. **WorkOrderCoverSheet**
3. **WorkOrderDetail**

These are run by `McaCutlistReports.createReports()` via:
- `McaCutlistSumReportController`
- `McaCutlistCoverReportController`
- `McaCutlistDetailReportController`

Detail is executed twice (Linear then Sheet usage type) with an extra query range on `McaCutlist.UsageType`.

---

## 1) [PROD] start-to-finish pipeline

## Stage P1 — selection + BOM explode input

1. Create service (`McaCutlistCreateService`) calls `McaCutlistCreate.run()`.
2. `processCutlistRecords()` walks query rows (build schedule/salesline context).
3. For each row:
   - `McaBOMSearchCutlist::newSalesLine(salesLine)`
   - `bomSearch.run()`
   - iterate `McaBOMExplodeTmp`
   - call `doCutlistItems()`.

Result: generation candidates for raw-material cutlist rows.

## Stage P2 — BOM resolution in `doCutlistItems()`

[PROD] attempts up to four retrieval strategies:
1. item-coverage + transfer-warehouse path
2. parent BOM site transfer-warehouse fallback
3. parent BOM site direct fallback
4. any BOM fallback

All branches apply effective-date filter against `offLineDate`.

Result: each matched BOM raw-material line triggers `createCutlistRecord()`.

## Stage P3 — row construction into `McaCutlist`

In [PROD] `createCutlistRecord()` (salesline path):
- identity/context:
  - `SalesLineRefRecId`, `ComponentBOMId`, `ComponentItemId`, `ModelBOMId`, `ModelItemId`
- inventory/routing:
  - site/location/wms, machine, cut group, move-to area, warehouse
- dimensions:
  - `Height`, `Width`, `Depth`
- quantities:
  - `Qty = BOMQty`
  - `Pieces = McaPieces`
  - `KitQty = McaBOMExplodeTmp.BOMQty`
- report/output extras:
  - notes, blueprint, prefix, schedule IDs, module IDs

Critical [PROD] fact:
- no `Per_Series` assignment path exists in production create code snapshot.

Module path (`McaCutlistCreate_Module`) similarly sets Qty/Pieces/KitQty but no per-series behavior.

## Stage P4 — persistence

`cutlist.validateWrite()` -> `cutlist.insert()`.  
Records are now in persistent `McaCutlist` and available for report/file generation.

## Stage P5 — report orchestration

`McaCutlistReports.createReports()` dispatches by flags:
- Summary -> WorkOrderSummary
- Cover -> WorkOrderCoverSheet
- Detail -> WorkOrderDetail (Linear + Sheet passes)

For detail pass, query is augmented with usage-type range.

## Stage P6 — DP preprocessing (`McaCutlistReportDP`) into `McaCutlistTmp`

### [PROD] Cover DP (`processCoverReport`)
- Query grouped by model/module/prefix/site/move-to/warehouse/salesline/due/kitqty.
- Copies cutlist row values to temp.
- `Pieces` copied raw (`cutlist.Pieces`).
- Generates `NewPageGroupBy` key.

### [PROD] Summary DP (`processSummaryReport`)
- Query grouped by model/module/cutgroup/site/warehouse/salesline/due/kitqty.
- `Pieces` copied raw.
- Populates summary-oriented row set.

### [PROD] Detail DP (`processDetailReport`)
- Row-by-row mapping with formatting.
- Key transform:
  - `mcaCutlistTmp.Pieces = real2int(cutlist.Pieces * cutlist.KitQty)`
- Additional transforms:
  - dimension strings (`real2FractionStr`)
  - usage via `usageCalcRounding()`
  - unit via `InventTableModule` lookup
  - `NewWOPageGroupBy` varies by usage type (Linear vs Sheet).

## Stage P7 — SSRS expression evaluation

In [PROD] SSRS `.xpo`:
- dataset includes `Pieces`, `KitQty` (no `Per_Series`).
- quantity expressions observed include:
  - `Sum(Pieces) * KitQty`
  - `Sum(Pieces)`

Implication:
- report section behavior differs based on which expression the specific tablix uses.
- when combined with detail DP expansion, some sections may multiply once, others effectively twice depending on region context.

---

## 2) [DEV] start-to-finish pipeline

## Stage D1 — selection + BOM explode

Same high-level flow as PROD for salesline creation.

Difference begins in selected fields and assignment.

## Stage D2 — BOM resolution

[DEV] `doCutlistItems()` includes `BOMQtySerie` in BOM selects (salesline flow), enabling per-series mapping.

## Stage D3 — row construction into `McaCutlist`

### [DEV] Salesline path (`McaCutlistCreate`)
- same core mappings as PROD plus:
  - `cutlist.Per_Series = bomRawMaterial.BOMQtySerie`
- includes UAT info popup logging per-series values.

### [DEV] Module path (`McaCutlistCreate_Module`)
- still sets Qty/Pieces/KitQty
- still **does not set `Per_Series`**

This is the highest-impact data-quality gap in DEV.

## Stage D4 — persistence

Same insert flow (`validateWrite` -> `insert`).

## Stage D5 — report orchestration

Same three report designs.

## Stage D6 — DP preprocessing (DEV variant)

In SR shared-project `McaCutlistReportDP`:
- Adds helper structures for:
  - model/prefix unit counts
  - build schedule display strings
- Cover/detail/summary all copy:
  - `mcaCutlistTmp.Per_Series = cutlist.Per_Series`
- Detail still expands pieces:
  - `mcaCutlistTmp.Pieces = real2int(cutlist.Pieces * cutlist.KitQty)`
- Summary path includes debug info messages around pieces assignment.

Meaning:
- DEV temp rows may mix origins where some have valid `Per_Series` (salesline) and some default (module).

## Stage D7 — SSRS expression evaluation (DEV)

Dataset differences:
- includes `Per_Series`, `Pieces`, `KitQty`, plus added fields like `UnitCounts`, `PWSBuildScheduleId`.

Expressions present:
- new intended formula:
  - `Ceiling(Sum(Pieces * KitQty) / safe(Max(Per_Series)))`
- per-series display fallback:
  - show `Not Set` when null/<=0
- legacy quantity regions still exist:
  - `Ceiling(Sum(KitQty))` in other sections.

Implication:
- DEV report is mixed-mode until all regions align on one quantity definition.

---

## 3) Field-by-field transformation timeline

## Qty
- Create:
  - [PROD]/[DEV] from `BOM.BOMQty`
- DP:
  - copied through all report paths
- SSRS:
  - mostly display/context; not the new DEV denominator

## Pieces
- Create:
  - [PROD]/[DEV] from `BOM.McaPieces`
- DP Cover/Summary:
  - raw copy
- DP Detail:
  - expanded: `Pieces * KitQty`
- SSRS:
  - [PROD] legacy totals (`Sum(Pieces)` or `Sum(Pieces)*KitQty`)
  - [DEV] new numerator `Sum(Pieces*KitQty)` in targeted regions

## KitQty
- Create:
  - salesline from explode temp BOM qty
  - module from module temp qty
- DP:
  - copied through
- SSRS:
  - multiplier in several expressions

## Per_Series
- [PROD]: not in production report data path
- [DEV] salesline create: set from `BOMQtySerie`
- [DEV] module create: missing assignment
- [DEV] DP: copied to temp
- [DEV] SSRS: denominator with safe fallback to 1

---

## 4) Three report paths individually (what each does)

## Report A — WorkOrderSummary

### [PROD]
- DP groups by module/cutgroup/site/warehouse/salesline/due/kitqty.
- `Pieces` copied raw.
- SSRS quantity region uses legacy totals (no per-series denominator).

### [DEV]
- DP also carries `Per_Series`, `UnitCounts`, `PWSBuildScheduleId` context.
- SSRS artifact still contains some legacy quantity regions.
- If per-series expression is not uniformly applied, Summary can disagree with Detail.

## Report B — WorkOrderCoverSheet

### [PROD]
- DP groups to produce cover aggregation rowset.
- `CutGroupId` comes from `getCutGroups(...)` aggregate string.
- `NewPageGroupBy` built from model/prefix/site/move-to/date.

### [DEV]
- same base behavior plus copied `Per_Series` and extra display strings.
- risk: cover remains mostly display-centric, but any quantity field bound to legacy expression will not match per-series expectation.

## Report C — WorkOrderDetail

### [PROD]
- DP is most transform-heavy path.
- `Pieces` is pre-expanded (`Pieces * KitQty`).
- usage/unit/dimension formatting done here.
- SSRS expressions vary by region (`Sum(Pieces)*KitQty` vs `Sum(Pieces)`).

### [DEV]
- same DP pre-expansion still present.
- SSRS adds per-series formula using `Pieces * KitQty` in numerator.
- if this region receives pre-expanded pieces, effective numerator can become `rawPieces * KitQty^2`.
- denominator fallback to 1 for missing `Per_Series` (common on module-origin rows) can further inflate output.

---

## 5) End-to-end divergence points (root causes)

1. **Creation-layer asymmetry in DEV**
   - salesline path sets `Per_Series`, module path does not.
2. **SSRS schema asymmetry across environments**
   - PROD dataset has no `Per_Series`; DEV does.
3. **Mixed `Pieces` semantics**
   - detail DP expands pieces; some report expressions multiply by kitqty again.
4. **Mixed expression model in DEV SSRS**
   - new and legacy quantity expressions coexist by region.
5. **Safe denominator fallback masks data defects**
   - missing `Per_Series` produces numeric output (denominator 1) instead of hard failure.

---

## 6) Practical, start-to-finish debug script for a single discrepant line

1. Identify report design + usage type (Summary / Cover / Detail, Linear/Sheet).
2. Capture source row origin (salesline vs module).
3. Query `McaCutlist` row and verify: Qty, Pieces, KitQty, Per_Series.
4. Recreate DP transform for the specific design:
   - especially `Pieces` written to `McaCutlistTmp`.
5. Locate exact SSRS textbox expression for displayed final quantity in that design.
6. Evaluate expression manually using captured temp-row values.
7. Compare with business-intended formula and record first divergence stage.

This identifies whether the error is from:
- create population,
- DP transform,
- or report expression binding.
