# Strict Comparison: Class_McaCutlistCreate_Module (PROD vs DEV with Per_Series assignment)

## Basis
This comparison is based on:
- PROD class export: `SR423365/code/Production Code/Classes/Class_McaCutlistCreate_Module.xpo`
- DEV `createCutlistRecord()` snippet provided in review comments, which adds:
  - `cutlist.Per_Series = bomRawMaterial.BOMQtySerie;`

## Exact deltas in `createCutlistRecord()`
1. Added executable assignment after Qty:
   - PROD: `cutlist.Qty = bomRawMaterial.BOMQty;` then `cutlist.Pieces = ...`
   - DEV: same plus `cutlist.Per_Series = bomRawMaterial.BOMQtySerie;` between those lines.
2. Non-functional formatting change:
   - blank line after `cutlist.insert();`

## Behavioral impact
- DEV now persists `Per_Series` into `McaCutlist` rows for module-created records.
- Input/output change: same BOM line input now yields an inserted row with populated `Per_Series` (instead of default/blank in PROD).

## System impact
- Data produced: DIFFERENT records (field-level), not necessarily more/fewer records.
- Query/filtering: no filter predicate changes shown in the modified snippet.
- BOM resolution/fallback: no path changes shown in the modified snippet.
- Date handling: no DateOffLine/ReqDate changes in the modified snippet.
- Insert/update semantics: still insert-only path (`validateWrite()` then `insert()`).

## Risks
- Report/output math that references `Per_Series` will change for module-created cutlist rows.
- If `BOMQtySerie` is null/zero, downstream calculations may still require guarding.
- Ensure `bomRawMaterial.BOMQtySerie` is selected/populated in data retrieval path; otherwise inserted values may be default at runtime.

## Classification
- `cutlist.Per_Series = bomRawMaterial.BOMQtySerie;` -> [LOGIC CHANGE]
- blank line after insert -> [NO FUNCTIONAL IMPACT]

## Mandatory focus checks
- DateOffLine -> ReqDate: no change shown here.
- while select filters: no change shown here.
- activeRawMaterial() inputs: no change shown here (`today()` in this class path).
- fallback resolution paths: no change shown here.
- insert vs update: no change (insert path only).
