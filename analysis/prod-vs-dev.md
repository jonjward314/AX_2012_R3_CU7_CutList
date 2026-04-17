# PROD vs DEV Diff Engine (Cutlist)

## Rules applied
- Systems modeled independently first.
- No logic merging.
- Every statement tagged [PROD] or [DEV].

---

## 1) Field population differences

### Field: `Per_Series`
- [PROD] Not present in analyzed production table/report data path; no set operation in create classes.
- [DEV] Added to `McaCutlist` and `McaCutlistTmp`; set in salesline create path from `BOM.BOMQtySerie`.
- [DEV] **Module path gap**: `McaCutlistCreate_Module.createCutlistRecord()` does not set `cutlist.Per_Series`.

Impact:
- [DEV] Same report can process mixed-quality rows (salesline rows with `Per_Series`, module rows without it).

### Field: `Pieces`
- [PROD] Populated from `BOM.McaPieces` in both create paths.
- [DEV] Same population pattern.
- [PROD]/[DEV] DP detail path transforms to `real2int(Pieces * KitQty)`.

Impact:
- Mixed semantics (raw vs expanded pieces by report section) exist in both systems; becomes more dangerous in DEV when combined with new series divisor formula.

### Field: `KitQty`
- [PROD] Salesline from `McaBOMExplodeTmp.BOMQty`; module from `cutlistModuleTmp.Qty`.
- [DEV] Same.

### Field: `Qty`
- [PROD]/[DEV] from `BOM.BOMQty`.

---

## 2) Code path differences

### Salesline create path
- [PROD] Query selects BOM fields incl. `BOMQty`, `McaPieces`; no `BOMQtySerie` usage.
- [DEV] Query select list includes `BOMQtySerie`; create writes `cutlist.Per_Series = BOMQtySerie`.

### Module create path
- [PROD] No per-series field handling.
- [DEV] Comment indicates intended per-series retrieval, but implementation still only sets `Pieces`; `Per_Series` absent.

### Report DP path
- [PROD] No per-series propagation to tmp.
- [DEV] Adds `mcaCutlistTmp.Per_Series = cutlist.Per_Series` across cover/detail/summary.

### SSRS path
- [PROD] Expressions observed are piece/kit aggregates (e.g., `Sum(Pieces)*KitQty`, `Sum(Pieces)`).
- [DEV] Adds target expression `Ceiling(Sum(Pieces*KitQty)/safe(Max(Per_Series)))` and display fallback `Not Set`.

---

## 3) Behavioral differences (same conceptual input)

Given: raw pieces=4, kitqty=3, per_series=5

- [PROD] No per-series division path -> output sections use legacy piece/kit totals.
- [DEV] Intended output -> `Ceiling((4*3)/5)=3` where data assumptions hold.

When row is module-originated (per_series missing):
- [PROD] unaffected (no per-series logic).
- [DEV] denominator fallback to 1 -> output becomes 12 (or higher with double-multiply contexts).

Divergence point:
- At create stage for module rows (`Per_Series` not populated), then amplified in SSRS safe-divide logic.

---

## 4) Hidden breakpoints / failure modes

1. **Expected field not populated**
   - [DEV] `Per_Series` expected by SSRS, but module path leaves null/0.

2. **Defaulting masks upstream defects**
   - [DEV] `IIf(... <=0, 1, Per_Series)` prevents divide-by-zero but hides data quality issue and distorts quantity math.

3. **Math assumption mismatch on `Pieces`**
   - [PROD]/[DEV] DP detail pre-expands `Pieces = Pieces * KitQty`.
   - [DEV] New SSRS numerator multiplies `Pieces * KitQty` again if pointed at expanded rows.

4. **Artifact consistency risk in Current Dev folder**
   - [DEV] standalone `Class_McaCutlistReportDP.xpo` appears mislabeled; shared-project export appears authoritative.
   - Risk: reviewers compare wrong files and conclude contradictory behavior.

---

## 5) Why stakeholders are confused about the math

1. [PROD] and [DEV] are being mentally merged as one system.
2. [DEV] formula uses `Per_Series`, but [PROD] does not expose this path.
3. [DEV] module path incompletely implements per-series assignment.
4. `Pieces` means different things by stage/section (raw vs expanded).
5. Safe divide (`<=0 -> 1`) produces plausible numbers that are still mathematically wrong for intended business logic.

---

## 6) Minimal debug checkpoints for working session

1. Separate row origin: salesline vs module before evaluating report math.
2. Inspect `McaCutlist.Per_Series` population by origin.
3. Confirm whether specific SSRS data region consumes raw or already-expanded `Pieces`.
4. Validate denominator values before fallback coercion.
5. Recompute expected quantity externally and compare by row/group.

---

## 7) SSRS-specific findings reference

For report-level root-cause analysis (dataset schema + expression-by-expression differences),
see: `analysis/ssrs-report-diff.md`.

For full end-to-end creation -> persistence -> DP -> SSRS pathing (all 3 report designs),
see: `analysis/end-to-end-transformation.md`.
