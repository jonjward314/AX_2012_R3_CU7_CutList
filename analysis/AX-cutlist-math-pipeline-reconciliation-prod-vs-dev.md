# Executive Summary (non-technical)
Production and Dev are not doing the exact same cutlist math today. Production mainly totals `Pieces` and `KitQty` with legacy expressions, while Dev introduces a new “divide by Per_Series and round up” formula in some report regions. The result is that users can see different totals between environments, and even within the same Dev report if different textboxes use different formulas. The biggest functional gap is that Dev currently populates `Per_Series` in the salesline create path but not consistently in the module path, so the new denominator can silently default to `1` and inflate outputs. This is why stakeholders are seeing confusion and drift rather than one consistent intended behavior.

Recommended intended behavior for decision: use one canonical quantity definition per report column, ensure `Per_Series` is populated for *all* cutlist row origins (or explicitly excluded), and remove mixed legacy/new expression overlap so the same business quantity is calculated the same way on Cover, Detail, and Summary.

# End-to-End Pipeline (Prod)
1. **User action / orchestration**
   - User initiates report/file generation flow; `McaCutlistReports.createReports()` dispatches Summary, Cover, and Detail controllers.
   - Detail runs twice by usage type (Linear then Sheet) by adding a usage range.
2. **Controller flag flow**
   - Cover controller sets `parmCoverSheet(true)` and passes query.
   - Summary controller sets `parmPrintSummary(true)` and passes query.
   - Detail controller sets `parmPrintDetail(true)` and passes query.
3. **Contract parameter flow**
   - `McaCutlistReportContract` carries packed query plus booleans (`parmCoverSheet`, `parmPrintDetail`, `parmPrintSummary`) into DP.
4. **DP processing methods**
   - `processReport()` dispatches to:
     - `processCoverReport()` (grouped rows)
     - `processSummaryReport()` (grouped rows)
     - `processDetailReport()` (row-level, transform-heavy)
5. **Query / range / grouping behavior**
   - Cover groups by model/module/prefix/site/move-to/warehouse/salesline/due/kitqty grain.
   - Summary groups by model/module/cutgroup/site/warehouse/salesline/due/kitqty grain.
   - Detail does not group; iterates rows and applies transforms.
6. **Dataset field derivations (math-impacting)**
   - Create path stores `Qty=BOMQty`, `Pieces=McaPieces`, `KitQty` from explode/module temp.
   - No production `Per_Series` propagation in analyzed path.
   - Detail DP sets `Pieces = real2int(cutlist.Pieces * cutlist.KitQty)` (pre-expanded).
7. **SSRS expression math (Prod)**
   - Observed expressions include `Sum(Pieces)` and `Sum(Pieces) * KitQty` depending on region.
   - No `Per_Series` divisor in production SSRS artifact.

# End-to-End Pipeline (Dev)
1. **User action / orchestration**
   - Same three report designs and controller dispatch model as Prod.
2. **Controller flag flow**
   - Same contract flags (`parmCoverSheet`, `parmPrintSummary`, `parmPrintDetail`) and query pass-through.
3. **Contract parameter flow**
   - Same packed query + booleans structure via `McaCutlistReportContract`.
4. **DP processing methods**
   - Same method family, plus extra metadata shaping (unit counts / schedule strings) and `Per_Series` propagation to temp.
5. **Query / range / grouping behavior**
   - Cover/Summary retain grouped grains; Detail remains row-level.
   - Dev adds explicit aggregate selection for some grouped paths (for example summed `Pieces`/`Qty` in cover).
6. **Dataset field derivations (math-impacting)**
   - Salesline create path adds `cutlist.Per_Series = bomRawMaterial.BOMQtySerie`.
   - Module create path is not consistently assigning `Per_Series` in current analyzed implementation.
   - Detail DP still pre-expands `Pieces = real2int(cutlist.Pieces * cutlist.KitQty)`.
   - DP copies `Per_Series` to temp fields.
7. **SSRS expression math (Dev)**
   - New expression appears: `Ceiling(Sum(Pieces * KitQty) / safe(Max(Per_Series)))` where safe fallback uses `1` for null/<=0.
   - Legacy expressions still exist in parts of artifact (mixed-mode behavior).

# Formula Dictionary (table)
| Report field / output concept | Plain-English formula | Pseudo-code | Source object / method | Confidence |
|---|---|---|---|---|
| Base Qty (row) | Quantity from BOM line | `Qty = bomRawMaterial.BOMQty` | `McaCutlistCreate.createCutlistRecord()` + module create equivalent | Confirmed |
| Base Pieces (row) | Pieces from BOM line | `Pieces = bomRawMaterial.McaPieces` | create classes (salesline + module) | Confirmed |
| KitQty (salesline row) | Kit qty from exploded BOM context | `KitQty = mcaBOMExplodeTmp.BOMQty` | salesline create path | Confirmed |
| KitQty (module row) | Kit qty from module temp qty | `KitQty = cutlistModuleTmp.Qty` | module create path | Confirmed |
| Per_Series (Prod) | Not available in analyzed prod report path | `Per_Series = <not populated>` | prod create/report path | Confirmed |
| Per_Series (Dev salesline) | Series denominator from BOMQtySerie | `Per_Series = bomRawMaterial.BOMQtySerie` | dev `McaCutlistCreate` | Confirmed |
| Per_Series (Dev module) | Intended denominator for module rows | `Per_Series = bomRawMaterial.BOMQtySerie` | dev module create path status varies by artifact/snapshot | Inferred |
| Detail Pieces (DP temp) | Expand pieces by kit quantity before SSRS | `Tmp.Pieces = real2int(cutlist.Pieces * cutlist.KitQty)` | `McaCutlistReportDP.processDetailReport()` | Confirmed |
| Cover/Summary Pieces (DP temp) | Keep pieces raw in grouped paths | `Tmp.Pieces = cutlist.Pieces` | `processCoverReport()` / `processSummaryReport()` | Confirmed |
| Prod legacy displayed quantity (region-dependent) | Either sum pieces, or sum pieces then multiply by kit qty | `Q = Sum(Pieces)` OR `Q = Sum(Pieces) * KitQty` | Prod `SSRSReport_McaCutlistBaseReport` expressions | Confirmed |
| Dev normalized displayed quantity | Sum piece*kit, divide by per-series, round up; protect denominator with 1 | `Q = Ceiling(Sum(Pieces*KitQty) / (Max(Per_Series)<=0?1:Max(Per_Series)))` | Dev `SSRSReport_McaCutlistBaseReport` expressions | Confirmed |
| Per_Series display label | Show “Not Set” if denominator missing/non-positive | `Txt = (Per_Series<=0 or null)?"Not Set":Per_Series` | Dev SSRS textbox expression | Confirmed |
| UnitCounts display helper | Distinct SalesLine counts at model/prefix grain rendered as helper text | `UnitCounts = countDistinct(SalesLineRefRecId by Model,Prefix)` | Dev DP helper logic | Inferred |
| Build schedule helper text | Distinct schedules compacted into display string | `Schedules = concatDistinct(PWSBuildScheduleId)` | Dev DP helper logic | Inferred |
| Menu/security routing for each design | Which menu items/privileges invoke each design | `N/A` | Not determinable from provided snapshot | Unknown |

# Worked Examples (step-by-step math)
## Scenario 1 — Linear usage (expected normalized path)
**Input row assumptions**
- UsageType: Linear
- Raw Pieces = 4
- KitQty = 3
- Per_Series = 5

**Computation (intended Dev normalized formula)**
1. Numerator = `Pieces * KitQty = 4 * 3 = 12`
2. Denominator = `Per_Series = 5`
3. Result = `Ceiling(12 / 5) = Ceiling(2.4) = 3`

**Interpretation**
- If this column’s business meaning is “required count normalized by series,” 3 is the intended output.

## Scenario 2 — Sheet usage (legacy-compatible path)
**Input row assumptions**
- UsageType: Sheet
- Raw Pieces = 6
- KitQty = 2
- Per_Series not used in Prod legacy region

**Computation (Prod legacy region `Sum(Pieces) * KitQty`)**
1. Sum(Pieces) at region grain = 6
2. Multiply by kit qty = `6 * 2 = 12`

**Interpretation**
- This can match DP-expanded pathways in some regions, but not where new denominator logic is expected.

## Scenario 3 — Edge case (null denominator + potential double multiply)
**Input row assumptions**
- Row origin: module-created
- Raw Pieces = 4
- KitQty = 3
- Per_Series = null (or 0)
- Detail DP pre-expands pieces first

**Computation chain (risk path)**
1. DP Detail sets `Pieces_tmp = real2int(4 * 3) = 12`
2. Dev normalized SSRS numerator uses `Pieces * KitQty` again => `12 * 3 = 36`
3. Denominator fallback applies (`Per_Series<=0 => 1`)
4. Output = `Ceiling(36 / 1) = 36`

**Interpretation**
- Intended logical result for raw formula with valid denominator (e.g., 5) would be 3; risk path outputs 36.
- This is the critical “double-count / double-multiply” callout.

# Prod vs Dev Differences (table)
| What changed | Why it matters | Impacted sheet/column | Risk |
|---|---|---|---|
| Dev added `Per_Series` field usage in SSRS datasets/expressions | Enables denominator normalization that Prod cannot do | Primarily WorkOrderDetail quantity outputs; also any region binding Per_Series | High |
| Prod has no per-series denominator path in report math | Prod/Dev parity breaks even with same inputs | Detail quantity totals across environments | High |
| Dev salesline create path assigns `Per_Series`; Prod does not | Dev rows can participate in new formula; Prod rows cannot | All designs where Per_Series shown/used | High |
| Dev module path `Per_Series` assignment is incomplete/inconsistent in analyzed snapshot | Missing denominator silently falls back to 1 and inflates totals | Detail and any normalized region touching module rows | High |
| Detail DP in both envs pre-expands `Pieces = Pieces * KitQty` | If SSRS also multiplies by KitQty, numerator can be squared by kit qty | WorkOrderDetail quantity columns | High |
| Dev retains legacy expressions in parts of RDL alongside new formula | Same report can show different logic by textbox | WorkOrderCoverSheet, WorkOrderSummary, WorkOrderDetail mixed columns | Medium |
| Dev grouped DP paths include explicit sum selections in some methods | Changes rollup grain behavior and aggregate values | Cover/Summary grouped totals | Medium |
| Dev adds schedule/unit-count helper derivations | Can alter display context and user interpretation but less math-critical | Header/helper fields on all sheets | Low |

# Risks & Ambiguities
1. **Double multiplication risk (prominent):** Detail DP pre-expands pieces; any SSRS expression doing `Pieces * KitQty` again can materially overstate values.
2. **Fallback masking risk:** `Per_Series<=0 => 1` prevents runtime error but hides data defects and can produce plausible-but-wrong totals.
3. **Mixed-mode expression drift:** Dev artifact contains both legacy and normalized formulas; totals may differ by region “by design,” which appears inconsistent to users.
4. **Module-origin denominator gap:** If module rows do not carry valid `Per_Series`, normalization behavior is unstable.
5. **Not determinable from provided XPO/MD:** full menu/security invocation map and runtime parameter defaults outside supplied artifacts.
6. **Snapshot caveat:** one dev class export appears mislabeled; shared project export appears authoritative for DP comparison.

# Meeting Agenda (60 minutes)
1. **0–10 min: business framing**
   - Confirm target business definition of each displayed quantity field.
2. **10–20 min: Prod walkthrough**
   - User action → controller flag → contract → DP method → SSRS expression.
3. **20–35 min: Dev walkthrough**
   - Same walkthrough; mark exact divergence points.
4. **35–45 min: worked examples live check**
   - Recalculate three scenarios row-by-row and compare to current outputs.
5. **45–55 min: decisions**
   - Approve intended canonical formula per field and per sheet.
6. **55–60 min: action assignment**
   - Validation queries, code/report changes, owner/date commitments.

# Actions & Owners
1. **AX Dev Owner** — Implement/verify `Per_Series` population for module-origin cutlist rows; add guardrail warning when missing.
2. **AX Dev + Report Dev** — Normalize all quantity textboxes to agreed canonical formula model (remove mixed legacy/new drift per column intent).
3. **Functional Consultant** — Approve business meaning per numeric column on Cover/Detail/Summary (what each number should represent).
4. **QA/Analyst** — Build a 3-scenario validation pack (Linear, Sheet, edge case null/rounding/kit interaction) with expected outputs and signoff checklist.
5. **DB/Tech Analyst** — Run lineage spot-checks from `McaCutlist` to `McaCutlistTmp` to rendered dataset values for sampled records in Prod and Dev.
6. **Project Lead (Kelly)** — Decide go/no-go on immediate hotfix scope: (A) denominator data quality first, (B) expression normalization first, or (C) both in one release.
