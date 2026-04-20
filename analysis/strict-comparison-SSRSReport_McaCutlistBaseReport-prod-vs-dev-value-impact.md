# SSRS value-impact comparison: `SSRSReport_McaCutlistBaseReport` (PROD vs DEV)

## Scope
- PROD: `SR423365/code/Production Code/SSRS/SSRSReport_McaCutlistBaseReport.xpo`
- DEV: `SR423365/code/Current Dev Code/SSRSReport_McaCutlistBaseReport.xpo`

## Report designs in scope
- `WorkOrderSummary`
- `WorkOrderCoverSheet`
- `WorkOrderDetail`

## Key value-impact deltas

### 1) Dataset schema expands in DEV (critical prerequisite)
- DEV dataset includes `Per_Series`, `PWSBuildScheduleId`, and `UnitCounts` in dataset field definitions / dataset field list payload.
- PROD dataset field payload does not include these additions.

Impact:
- DEV report expressions can divide by `Per_Series` and display schedule/unit-count metadata.
- PROD cannot execute these calculations/displays because those fields are absent at SSRS dataset layer.

---

### 2) `WorkOrderSummary` quantity expression changes
- PROD uses `=Sum(Fields!KitQty.Value)`.
- DEV uses `=Ceiling(Sum(Fields!KitQty.Value))`.

Impact on values:
- DEV rounds up fractional totals to next integer.
- Therefore DEV summary piece/count figures can be greater than PROD whenever summed kit quantity is non-integer.

---

### 3) `WorkOrderCoverSheet` quantity expression changes
- PROD uses `=Sum(Fields!KitQty.Value)`.
- DEV uses `=Ceiling(Sum(Fields!KitQty.Value))`.

Impact on values:
- Same rounding-up behavior as Summary.
- Cover counts become integer-rounded-up totals in DEV.

---

### 4) `WorkOrderDetail` quantity logic changes from legacy to per-series normalization
- PROD expression(s) include:
  - `=Sum(Fields!Pieces.Value) * Fields!KitQty.Value`
  - and in other regions `=Sum(Fields!Pieces.Value)`
- DEV expression uses:
  - `=Ceiling(Sum(Fields!Pieces.Value * Fields!KitQty.Value) / IIf(IsNothing(Max(Fields!Per_Series.Value)) OrElse Max(Fields!Per_Series.Value) <= 0, 1, Max(Fields!Per_Series.Value)))`
  - plus display fallback: `IIf(...Per_Series<=0, "Not Set", Per_Series)`

Impact on values:
- DEV introduces per-series denominator normalization.
- If `Per_Series > 1`, DEV output is reduced versus non-normalized formulas.
- If `Per_Series` is null/0, DEV fallback divides by 1 (no reduction) and labels `Not Set`.
- Because formula structure differs from PROD, value parity is not expected.

---

### 5) Mixed expression behavior risk
- PROD and DEV both contain multiple data regions, but DEV has newer normalized formulas while still using legacy-style totals in other places.

Impact on values:
- Different sections of the same report can show different totals by design.
- This can appear as inconsistency unless each textbox expression is traced to its region-level formula.

## Concise per-report impact summary
- `WorkOrderSummary`: DEV may output larger integer totals due to `Ceiling` on kit quantity sums.
- `WorkOrderCoverSheet`: same `Ceiling` behavior as Summary.
- `WorkOrderDetail`: DEV shifts to per-series normalized math; values can be lower/higher/different depending on `Per_Series` and source `Pieces/KitQty` semantics.
