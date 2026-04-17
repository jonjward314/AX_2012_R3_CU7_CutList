# [DEV] Math Reconstruction

## Scope
This model is reconstructed from Current Dev artifacts, primarily the SR shared project export.

---

## 1) Row-level math (McaCutlist creation)

### [DEV] Salesline path
Per created row:
- `Qty = BOM.BOMQty`
- `Pieces = BOM.McaPieces`
- `KitQty = McaBOMExplodeTmp.BOMQty`
- `Per_Series = BOM.BOMQtySerie`  ✅ new DEV assignment

### [DEV] Module path
Per created row:
- `Qty = BOM.BOMQty`
- `Pieces = BOM.McaPieces`
- `KitQty = cutlistModuleTmp.Qty`
- `Per_Series` **NOT assigned** ❌

This is the primary data-quality break in DEV math adoption.

---

## 2) DP aggregation/staging math

In DEV `McaCutlistReportDP`:
- Cover/detail/summary copy `mcaCutlistTmp.Per_Series = cutlist.Per_Series`.
- Detail still expands pieces:
  - `mcaCutlistTmp.Pieces = real2int(cutlist.Pieces * cutlist.KitQty)`
- `KitQty` remains present in temp rows.

So numerator semantics may depend on section:
- sometimes raw pieces + kitqty,
- sometimes already expanded pieces.

---

## 3) Final SSRS math (DEV)

DEV report includes new formula:

`=Ceiling(Sum(Fields!Pieces.Value * Fields!KitQty.Value) / IIf(IsNothing(Max(Fields!Per_Series.Value)) OrElse Max(Fields!Per_Series.Value) <= 0, 1, Max(Fields!Per_Series.Value)))`

Also includes display fallback:

`=IIf(IsNothing(Fields!Per_Series.Value) OrElse Fields!Per_Series.Value <= 0, "Not Set", Fields!Per_Series.Value)`

---

## 4) Expanded formula derivation

Given a report group G:

- Numerator: `N = Sum_G(Pieces * KitQty)`
- Denominator: `D = safe(Max_G(Per_Series))`, where `safe(x)=1 if x<=0/null else x`
- Final: `FinalQuantity = Ceiling(N / D)`

### Important caveat
If `Pieces` reaching this expression is already expanded in DP (`Pieces = rawPieces * KitQty`), then expression effectively becomes:

`N = Sum((rawPieces * KitQty) * KitQty) = Sum(rawPieces * KitQty^2)`

This can inflate output unless the expression is bound only to datasets/regions where `Pieces` is raw.

---

## 5) Numeric examples (DEV)

Assume logical business input:
- raw `Pieces = 4`
- `KitQty = 3`
- `Per_Series = 5`

### Example A — ideal raw-pieces path
- Numerator: `4 * 3 = 12`
- Denominator: `5`
- `Final = Ceiling(12/5) = Ceiling(2.4) = 3`

### Example B — module row with missing Per_Series
- `Per_Series` defaults 0/null -> safe denominator `1`
- Numerator still 12
- `Final = Ceiling(12/1) = 12`
- Massive divergence from Example A.

### Example C — double-multiply risk (expanded pieces fed to same expression)
- DP detail: `Pieces_tmp = 4*3 = 12`
- SSRS numerator: `12 * 3 = 36`
- `Final = Ceiling(36/5)=8`
- This differs from intended 3.

---

## 6) Reconciliation against target formula
Target:

`Ceiling( Sum(Pieces * KitQty) / Per_Series )`

### [DEV] Reconciliation result
- **Implemented in SSRS**: YES (with safety wrapper for denominator).
- **Data-path consistency**: PARTIAL.

Why partial:
1. Module create path does not populate `Per_Series`.
2. DP detail expands `Pieces` prior to SSRS; if same dataset region uses new formula, numerator may be overstated.
3. Report XML still contains legacy expressions in other sections.

Conclusion:
- DEV has the intended formula, but current field-population and mixed `Pieces` semantics can violate the math assumptions.

---

## 7) SSRS artifact note

The DEV SSRS `.xpo` still includes legacy quantity expressions (`Ceiling(Sum(KitQty))`) alongside the new
per-series expression. This means different report regions may legitimately return different totals until
all regions are normalized to one formula model.
