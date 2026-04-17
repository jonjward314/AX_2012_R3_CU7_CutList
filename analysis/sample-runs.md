# Sample Runs (Meeting Tool)

Purpose: Walk through identical conceptual inputs across [PROD], [DEV], and intended-correct behavior.

---

## Shared sample input baseline

Use one BOM component row for clarity:
- BOM component `Pieces` (`McaPieces`) = 4
- BOM component `Qty` (`BOMQty`) = 2
- BOM component `Per_Series` candidate (`BOMQtySerie`) = 5
- Exploded kit multiplier `KitQty` = 3
- Row origin toggle: Salesline path vs Module path

---

## Scenario A — [PROD] Real behavior

## INPUT
- [PROD] Salesline-origin row (or module-origin row; per-series is irrelevant in PROD math).

## TRANSFORM
1. [PROD] `McaCutlistCreate.createCutlistRecord()`
   - `Qty=2`
   - `Pieces=4`
   - `KitQty=3`
   - no `Per_Series` assignment path
2. [PROD] `McaCutlistReportDP.processDetailReport()`
   - `McaCutlistTmp.Pieces = real2int(4*3)=12`
   - `McaCutlistTmp.KitQty=3`
3. [PROD] SSRS section expression depends on data region:
   - either `Sum(Pieces)`
   - or `Sum(Pieces)*KitQty`

## OUTPUT
- [PROD] If using `Sum(Pieces)` in this detail case -> 12.
- [PROD] If applying `*KitQty` after expanded pieces -> 36 (potential over-scale path).
- [PROD] No per-series normalized output exists in source snapshot.

## TRACE FULL PATH
`SalesLine -> McaCutlistCreate -> McaCutlist -> McaCutlistReportDP(detail transform) -> McaCutlistTmp -> SSRS legacy expressions`

---

## Scenario B — [DEV] Current behavior

## INPUT
Case B1 (salesline row): same baseline values.  
Case B2 (module row): same baseline values but module create path omits `Per_Series`.

## TRANSFORM
### B1 Salesline row
1. [DEV] `McaCutlistCreate.createCutlistRecord()`
   - `Qty=2`, `Pieces=4`, `KitQty=3`, `Per_Series=5`
2. [DEV] DP copies `Per_Series` into temp row.
3. [DEV] SSRS new expression computes:
   - `Ceiling(Sum(Pieces*KitQty)/safe(Max(Per_Series)))`

### B2 Module row
1. [DEV] `McaCutlistCreate_Module.createCutlistRecord()`
   - `Qty=2`, `Pieces=4`, `KitQty=3`, `Per_Series` missing (0/null)
2. [DEV] DP copies missing `Per_Series` as 0/null.
3. [DEV] SSRS safe denominator -> 1.

## OUTPUT
- B1 expected with raw-piece assumption: `Ceiling((4*3)/5)=3`
- B2 module: `Ceiling((4*3)/1)=12`
- If a region receives DP-expanded pieces and still multiplies by `KitQty`, numerator can inflate (`4*3*3=36`) -> `Ceiling(36/5)=8`.

## TRACE FULL PATH
B1: `SalesLine -> DEV create (Per_Series populated) -> DP copy -> SSRS per-series formula`  
B2: `ModuleTmp -> DEV module create (Per_Series missing) -> DP copy -> SSRS safe-divide fallback`

---

## Scenario C — Intended correct model (target business math)

## INPUT
Same baseline:
- raw pieces=4
- kitqty=3
- per_series=5
- qty=2 (independent BOM qty, not direct divisor)

## TRANSFORM (INTENDED)
1. Populate `Per_Series` consistently for **all** row origins (salesline + module).
2. Keep a single semantic rule for `Pieces` at report-calculation point:
   - either keep `Pieces` raw and multiply once in SSRS,
   - or pre-expand in DP and do not multiply again.
3. Apply normalized formula once:
   - `FinalQuantity = Ceiling(Sum(rawPieces * KitQty) / Per_Series)`

## OUTPUT
- `FinalQuantity = Ceiling((4*3)/5)=3`

## TRACE FULL PATH
`Any origin -> create populates Qty/Pieces/KitQty/Per_Series consistently -> DP preserves agreed Pieces semantics -> SSRS applies one non-duplicative formula`

---

## Meeting cheat-sheet: divergence trigger

If final number jumps from ~3 to ~12 or ~8 on similar data:
- Check row origin (module rows missing `Per_Series`?)
- Check whether `Pieces` was already multiplied by `KitQty` before SSRS expression
- Check denominator fallback activation (`Per_Series <= 0 -> 1`)
