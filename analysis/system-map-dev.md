# SYSTEM B — [DEV] Cutlist System Map (Debug Model)

## Scope
Current Dev artifacts analyzed:
- `SR423365/code/Current Dev Code/SharedProject_J_SR423365_1560_Enhance_Cutsheet_Changes.xpo` (contains bundled class/table/report changes)
- `SR423365/code/Current Dev Code/Table_McaCutlist.xpo`
- `SR423365/code/Current Dev Code/Table_McaCutlistTmp.xpo`
- `SR423365/code/Current Dev Code/SSRSReport_McaCutlistBaseReport.xpo`
- `SR423365/code/Current Dev Code/Class_McaCutlistCreate.xpo`
- `SR423365/code/Current Dev Code/Class_McaCutlistCreate_Module.xpo`

Important artifact hygiene note:
- [DEV] `Class_McaCutlistReportDP.xpo` file in this folder appears mismatched (contains `McaCutlistCreate_Module` content). For DEV intent, `SharedProject_...xpo` contains the coherent `McaCutlistReportDP` definition.

---

## 1) Entry points and execution surfaces

### [DEV] Create pipeline (salesline)
- Same controller/service chain as PROD (`McaCutlistCreateController/Service` design pattern retained).
- `McaCutlistCreate.createCutlistRecord()` now writes new field `Per_Series` from BOM.

### [DEV] Module create pipeline
- `McaCutlistCreate_Module.createCutlistRecord()` still sets Qty/Pieces/KitQty, but **does not set `Per_Series`**.

### [DEV] Report pipeline
- `McaCutlistReportDP.processReport()` still dispatches cover/detail/summary.
- DEV DP includes additional helper maps and alignment logic (`UnitCounts`, build-schedule display aggregation).
- DEV DP writes `Per_Series` to temp rows in cover/detail/summary:
  - `mcaCutlistTmp.Per_Series = cutlist.Per_Series`.

### [DEV] SSRS pipeline
- SSRS dataset includes `Per_Series` field.
- New expressions include formula:
  - `Ceiling(Sum(Pieces * KitQty) / safe(Per_Series))`.

---

## 2) Core flow map (record lifecycle)

```text
[DEV]
SalesLine query
  -> McaBOMSearchCutlist
  -> doCutlistItems() (includes BOMQtySerie in select list)
  -> createCutlistRecord() writes Per_Series
  -> McaCutlist
  -> McaCutlistReportDP writes Per_Series into McaCutlistTmp
  -> SSRS uses Per_Series-aware expression
```

```text
[DEV module path]
McaCutlistModuleTmp rows
  -> McaCutlistCreate_Module.createCutlistRecord()
  -> McaCutlist (Per_Series likely default/0 because not assigned)
  -> DP copies Per_Series (0/null)
  -> SSRS safe-divide falls back denominator to 1
```

---

## 3) Table roles

### [DEV] `McaCutlist`
- Includes `Per_Series` (REAL, EDT `BOMQtySerie`) and `Pieces`.
- `Per_Series` is intended to carry BOM quantity-per-series to reporting math.

### [DEV] `McaCutlistTmp`
- Includes `Per_Series`, `Pieces`, plus extra display field `UnitCounts` and `PWSBuildScheduleId` in dev report model.

### [DEV] supporting structures
- Same base supporting tables as PROD.
- DP adds extra string/token utility behavior for model/prefix count display alignment.

---

## 4) Field lineage (critical)

## Qty
- **Set**:
  - [DEV] `cutlist.Qty = bomRawMaterial.BOMQty` (salesline + module).
- **Transform**:
  - [DEV] copied through DP into temp rows.
- **Consumed**:
  - [DEV] report sections display/use Qty similarly to PROD.

## KitQty
- **Set**:
  - [DEV] salesline path from `mcaBOMExplodeTmp.BOMQty`.
  - [DEV] module path from `cutlistModuleTmp.Qty`.
- **Transform**:
  - [DEV] copied into temp rows.
- **Consumed**:
  - [DEV] used in expression numerator (`Pieces * KitQty`) and other existing totals.

## Pieces
- **Set**:
  - [DEV] both creation paths set `cutlist.Pieces = bomRawMaterial.McaPieces`.
- **Transform**:
  - [DEV] detail DP: `mcaCutlistTmp.Pieces = real2int(cutlist.Pieces * cutlist.KitQty)` (same as PROD detail transform).
  - [DEV] cover/summary often carry raw pieces.
- **Consumed**:
  - [DEV] SSRS formulas include `Pieces * KitQty` in numerator for new per-series calc.

## Per_Series
- **Set**:
  - [DEV] salesline create path: `cutlist.Per_Series = bomRawMaterial.BOMQtySerie`.
  - [DEV] module create path: **NOT SET**.
- **Transform**:
  - [DEV] DP cover/detail/summary copies `cutlist.Per_Series` into `mcaCutlistTmp.Per_Series`.
- **Consumed**:
  - [DEV] SSRS expression safe-divides by `Max(Per_Series)` with fallback to 1.

### Consequence
- [DEV] math design expects `Per_Series`, but module-originated rows can still carry 0/null because module create path omits assignment.

---

## 5) Known unknowns
- [DEV][UNKNOWN] Which of duplicated artifacts (`SharedProject_...`, standalone class/report files) is actually deployed in the next DEV package.
- [DEV][UNKNOWN] Whether all SSRS sections were migrated consistently to the new per-series expression (some legacy expressions remain in report XML).

---

For full, stage-by-stage generation and transformation trace through all three report designs,
see `analysis/end-to-end-transformation.md`.
