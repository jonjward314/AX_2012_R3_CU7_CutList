# SSRS .XPO Deep Diff — Why outputs diverge

This file focuses only on **report behavior** extracted from:
- [PROD] `SR423365/code/Production Code/SSRS/SSRSReport_McaCutlistBaseReport.xpo`
- [DEV] `SR423365/code/Current Dev Code/SSRSReport_McaCutlistBaseReport.xpo`

---

## 1) Dataset schema differences in SSRS

## [PROD]
- Dataset includes `KitQty` and `Pieces` fields.
- No `Per_Series` field references were found in the production report dataset.

## [DEV]
- Dataset includes `KitQty`, `Pieces`, and **`Per_Series`**.
- `Per_Series` is carried through multiple report dataset definitions/duplicates in the .xpo.

Meaning:
- [DEV] can execute series-normalized math in SSRS.
- [PROD] cannot, because denominator field is absent at report layer.

---

## 2) Expression-level math differences (critical)

## [PROD] expressions observed
- `=Sum(Fields!Pieces.Value) * Fields!KitQty.Value`
- `=Sum(Fields!Pieces.Value)`

These are legacy piece/kit totals and do not divide by `Per_Series`.

## [DEV] expressions observed
- New per-series math:
  - `=Ceiling(Sum(Fields!Pieces.Value * Fields!KitQty.Value) / IIf(IsNothing(Max(Fields!Per_Series.Value)) OrElse Max(Fields!Per_Series.Value) <= 0, 1, Max(Fields!Per_Series.Value)))`
- New display fallback:
  - `=IIf(IsNothing(Fields!Per_Series.Value) OrElse Fields!Per_Series.Value <= 0, "Not Set", Fields!Per_Series.Value)`
- Legacy expressions still present in other data regions:
  - `=Ceiling(Sum(Fields!KitQty.Value))`

Meaning:
- [DEV] report is **mixed-mode**: not every region uses the same quantity logic.

---

## 3) Why this matters with DP behavior

Report DP detail path sets:
- [PROD]/[DEV] `mcaCutlistTmp.Pieces = real2int(cutlist.Pieces * cutlist.KitQty)`

If a tablix that expects raw `Pieces` receives already-expanded `Pieces`, then the DEV formula
`Sum(Pieces * KitQty)` can effectively become `Sum(rawPieces * KitQty^2)`.

This is a direct SSRS-level reason users can see unexpectedly large quantities.

---

## 4) Region consistency check (practical debug checklist)

For each tablix/textbox showing a “final quantity”:
1. Confirm exact expression (`Sum(Pieces)`, `Sum(Pieces)*KitQty`, `Ceiling(Sum(Pieces*KitQty)/Per_Series)`, or `Ceiling(Sum(KitQty))`).
2. Confirm source dataset fields for that region include/omit `Per_Series`.
3. Confirm whether `Pieces` in that region is raw or pre-expanded from DP.
4. Confirm denominator fallback triggered (`Per_Series<=0/null -> 1`).

If step 1 differs between regions, numbers will diverge by design.

---

## 5) SSRS-driven explanation of stakeholder confusion

Confusion is mathematically expected because:
- [PROD] and [DEV] report schemas differ (`Per_Series` absent vs present).
- [DEV] includes both new and legacy quantity expressions in the same report artifact.
- `Pieces` semantics vary by path (raw vs expanded), but SSRS formulas may assume one semantic.
- safe-divide fallback hides missing `Per_Series` population by returning a number instead of error.
