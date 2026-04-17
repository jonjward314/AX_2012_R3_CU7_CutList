# [PROD] Math Reconstruction

## Scope
This is the quantitative behavior reconstructed from **Production Code** artifacts only.

---

## 1) Row-level math (McaCutlist creation)

For each created cutlist row:
- `Qty = BOM.BOMQty`
- `Pieces = BOM.McaPieces`
- `KitQty = McaBOMExplodeTmp.BOMQty` (salesline path) OR `cutlistModuleTmp.Qty` (module path)
- `Per_Series = N/A in PROD model` (no production field assignment/path in analyzed snapshot)

No row-level division by series occurs in production create classes.

---

## 2) DP aggregation/staging math

In `McaCutlistReportDP`:
- Cover/Summary: `mcaCutlistTmp.Pieces = cutlist.Pieces` (raw)
- Detail: `mcaCutlistTmp.Pieces = real2int(cutlist.Pieces * cutlist.KitQty)` (expanded)
- `KitQty` is still passed to temp rows.

So, depending on report section, `Pieces` in temp means either:
- raw pieces per component, or
- expanded pieces (`Pieces * KitQty`).

---

## 3) SSRS math in PROD snapshot

Observed formulas include:
1. `=Sum(Fields!Pieces.Value) * Fields!KitQty.Value`
2. `=Sum(Fields!Pieces.Value)`

No production per-series divisor formula was found in Production Code SSRS artifact.

---

## 4) Derived effective quantity expression

Because PROD uses section-dependent expressions, effective final quantity is contextual:

- **Case A (expression #1)**:  
  `FinalQuantity = Sum(Pieces) * KitQty`

- **Case B (expression #2)**:  
  `FinalQuantity = Sum(Pieces)`

And in detail sections where DP already expanded pieces:
- `Pieces_tmp = Pieces_row * KitQty_row`
- If SSRS multiplies again by `KitQty`, this can over-scale (depends on grouping/data region).

---

## 5) Numeric examples (PROD)

Assume one logical line:
- source `Pieces = 4`
- source `KitQty = 3`

### Example 1: DP detail expansion + report sums Pieces only
- DP: `Pieces_tmp = 4 * 3 = 12`
- SSRS: `Sum(Pieces) = 12`
- Final = 12

### Example 2: report uses `Sum(Pieces) * KitQty` against raw pieces section
- `Sum(Pieces)=4`, `KitQty=3`
- Final = 12

### Example 3: if expanded pieces are again multiplied by KitQty
- `Pieces_tmp=12`
- SSRS `12 * 3 = 36`
- Final = 36 (potential double-multiply risk if this path occurs on same semantic row set).

---

## 6) Reconciliation against target formula
Target requested formula:

`Ceiling( Sum(Pieces * KitQty) / Per_Series )`

### [PROD] Reconciliation result
- **Mismatch: YES**

Why:
1. `Per_Series` is not modeled/propagated in PROD snapshot.
2. PROD SSRS expressions found are piece/kit-based only (no series divisor).
3. PROD DP already expands `Pieces` in detail, creating mixed semantics for `Pieces` across report sections.

Conclusion:
- [PROD] cannot natively compute the target per-series formula as written because denominator field/path is absent in deployed artifacts.
