# Strict Comparison: Class_McaCutlistCreate (PROD vs DEV)

## Scope
- PROD: `SR423365/code/Production Code/Classes/Class_McaCutlistCreate.xpo`
- DEV: `SR423365/code/Current Dev Code/Class_McaCutlistCreate.xpo`

## Observed functional deltas
1. DEV sets `cutlist.Per_Series` from `bomRawMaterial.BOMQtySerie` during insert payload construction.
2. DEV adds an `info(...)` popup/log message after successful insert in `createCutlistRecord()`.
3. DEV extends all four `while select` raw-material joins in `doCutlistItems()` to include `BOMQtySerie` in the selected field list.
4. No observed changes to:
   - `DateOffLine` vs `ReqDate` logic.
   - BOM date range predicates (`fromDate`/`toDate`) in `while select` filters.
   - `activeRawMaterial()` argument list.
   - Fallback path structure/order.
   - Insert vs update behavior (still insert-only in this class path).
