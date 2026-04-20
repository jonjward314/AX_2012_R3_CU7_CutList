# Prod vs Dev Math Reconciliation by Report (SQL + SSRS)

## Purpose
This page treats the three report designs as **independent pipelines** and provides parameterized SQL checks for each one.

Reports covered independently:
1. WorkOrderCoverSheet
2. WorkOrderDetail
3. WorkOrderSummary

> If any value cannot be proven from provided artifacts, it is explicitly marked as **Not determinable from provided XPO/MD**.

## Shared SQL Parameters
Use these parameters in all validation scripts.

```sql
DECLARE @FromDueDate      date         = '2026-01-01';
DECLARE @ToDueDate        date         = '2026-12-31';
DECLARE @InventSiteId     nvarchar(10) = NULL;
DECLARE @ShipToWarehouse  nvarchar(30) = NULL;
DECLARE @ModelItemId      nvarchar(30) = NULL;
DECLARE @Prefix           nvarchar(30) = NULL;
DECLARE @UsageType        int          = NULL;  -- Linear/Sheet enum value if needed
```

Base filter pattern used below:

```sql
WHERE c.DueDateTime >= @FromDueDate
  AND c.DueDateTime < DATEADD(day, 1, @ToDueDate)
  AND (@InventSiteId    IS NULL OR c.InventSiteId    = @InventSiteId)
  AND (@ShipToWarehouse IS NULL OR c.ShipToWarehouse = @ShipToWarehouse)
  AND (@ModelItemId     IS NULL OR c.ModelItemId     = @ModelItemId)
  AND (@Prefix          IS NULL OR c.Prefix          = @Prefix)
```

## 1) WorkOrderCoverSheet

### Pipeline grain (independent of other reports)
- DP path: `McaCutlistReportDP.processCoverReport()` grouped path.
- Grouping intent: cover-level buckets (model/module/prefix/site/move-to/warehouse/salesline/due/kitqty).
- Pieces behavior in DP: treated as raw/grouped cover value (not detail-expanded behavior).

### Parameterized SQL validation (Prod-aligned cover totals)

```sql
WITH base AS (
    SELECT c.*
    FROM McaCutlist c
    WHERE c.DueDateTime >= @FromDueDate
      AND c.DueDateTime < DATEADD(day, 1, @ToDueDate)
      AND (@InventSiteId    IS NULL OR c.InventSiteId    = @InventSiteId)
      AND (@ShipToWarehouse IS NULL OR c.ShipToWarehouse = @ShipToWarehouse)
      AND (@ModelItemId     IS NULL OR c.ModelItemId     = @ModelItemId)
      AND (@Prefix          IS NULL OR c.Prefix          = @Prefix)
)
SELECT
    b.ModelItemId,
    b.ModuleItemId,
    b.Prefix,
    b.InventSiteId,
    b.MoveToAreaId,
    b.ShipToWarehouse,
    b.SalesLineRefRecId,
    CONVERT(date, b.DueDateTime) AS DueDate,
    b.KitQty,
    SUM(b.Pieces) AS SumPieces,
    SUM(b.Pieces) * MAX(b.KitQty) AS Prod_Legacy_SumPiecesTimesKitQty,
    SUM(b.KitQty) AS Prod_Legacy_SumKitQty
FROM base b
GROUP BY
    b.ModelItemId,
    b.ModuleItemId,
    b.Prefix,
    b.InventSiteId,
    b.MoveToAreaId,
    b.ShipToWarehouse,
    b.SalesLineRefRecId,
    CONVERT(date, b.DueDateTime),
    b.KitQty
ORDER BY DueDate, b.Prefix, b.ModelItemId;
```

### Parameterized SQL validation (Dev cover math checks)

```sql
WITH base AS (
    SELECT c.*
    FROM McaCutlist c
    WHERE c.DueDateTime >= @FromDueDate
      AND c.DueDateTime < DATEADD(day, 1, @ToDueDate)
      AND (@InventSiteId    IS NULL OR c.InventSiteId    = @InventSiteId)
      AND (@ShipToWarehouse IS NULL OR c.ShipToWarehouse = @ShipToWarehouse)
      AND (@ModelItemId     IS NULL OR c.ModelItemId     = @ModelItemId)
      AND (@Prefix          IS NULL OR c.Prefix          = @Prefix)
)
SELECT
    b.ModelItemId,
    b.ModuleItemId,
    b.Prefix,
    b.InventSiteId,
    b.MoveToAreaId,
    b.ShipToWarehouse,
    b.SalesLineRefRecId,
    CONVERT(date, b.DueDateTime) AS DueDate,
    b.KitQty,
    SUM(b.Pieces) AS SumPieces,
    CEILING(SUM(b.KitQty)) AS Dev_CeilingSumKitQty,
    CEILING(
        SUM(b.Pieces * b.KitQty) /
        NULLIF(CASE WHEN MAX(ISNULL(b.Per_Series, 0)) <= 0 THEN 1 ELSE MAX(b.Per_Series) END, 0)
    ) AS Dev_Normalized_IfRegionUsesPerSeries
FROM base b
GROUP BY
    b.ModelItemId,
    b.ModuleItemId,
    b.Prefix,
    b.InventSiteId,
    b.MoveToAreaId,
    b.ShipToWarehouse,
    b.SalesLineRefRecId,
    CONVERT(date, b.DueDateTime),
    b.KitQty
ORDER BY DueDate, b.Prefix, b.ModelItemId;
```

### CoverSheet math: Prod vs Dev at SQL level
- **Prod baseline:** legacy totals (`Sum(Pieces)` or `Sum(Pieces)*KitQty`, and in some regions `Sum(KitQty)`).
- **Dev candidate behavior:** regions may use `Ceiling(Sum(KitQty))`; some regions can use per-series normalized expression if bound there.
- **Impact:** Cover counts can increase due to `Ceiling`, and can diverge further if denominator-based math is enabled for that region.

### CoverSheet math: Prod vs Dev at SSRS level
- **Prod SSRS:** no per-series denominator in observed expressions.
- **Dev SSRS:** introduces per-series expression and keeps legacy expressions in other regions.
- **Result:** same cover sheet can show mixed formula semantics by textbox until expressions are normalized.

---

## 2) WorkOrderDetail

### Pipeline grain (independent of other reports)
- DP path: `McaCutlistReportDP.processDetailReport()` row-level path.
- No GROUP BY in DP detail path.
- Critical transform: `Tmp.Pieces = real2int(cutlist.Pieces * cutlist.KitQty)` before SSRS.

### Parameterized SQL validation (Prod-aligned detail math)

```sql
WITH base AS (
    SELECT c.*
    FROM McaCutlist c
    WHERE c.DueDateTime >= @FromDueDate
      AND c.DueDateTime < DATEADD(day, 1, @ToDueDate)
      AND (@InventSiteId    IS NULL OR c.InventSiteId    = @InventSiteId)
      AND (@ShipToWarehouse IS NULL OR c.ShipToWarehouse = @ShipToWarehouse)
      AND (@ModelItemId     IS NULL OR c.ModelItemId     = @ModelItemId)
      AND (@Prefix          IS NULL OR c.Prefix          = @Prefix)
      AND (@UsageType       IS NULL OR c.UsageType       = @UsageType)
)
SELECT
    b.RecId,
    b.ModelItemId,
    b.ModuleItemId,
    b.ItemId,
    b.Prefix,
    b.UsageType,
    b.KitQty,
    b.Pieces AS RawPieces,
    CAST(ROUND(b.Pieces * b.KitQty, 0) AS int) AS DP_DetailExpandedPieces,
    CAST(ROUND(b.Pieces * b.KitQty, 0) AS int) AS Prod_IfSSRSSumsExpandedPieces,
    CAST(ROUND(b.Pieces * b.KitQty, 0) AS int) * b.KitQty AS Prod_IfRegionMultipliesAgain
FROM base b
ORDER BY b.DueDateTime, b.Prefix, b.ModelItemId;
```

### Parameterized SQL validation (Dev detail math checks)

```sql
WITH base AS (
    SELECT c.*
    FROM McaCutlist c
    WHERE c.DueDateTime >= @FromDueDate
      AND c.DueDateTime < DATEADD(day, 1, @ToDueDate)
      AND (@InventSiteId    IS NULL OR c.InventSiteId    = @InventSiteId)
      AND (@ShipToWarehouse IS NULL OR c.ShipToWarehouse = @ShipToWarehouse)
      AND (@ModelItemId     IS NULL OR c.ModelItemId     = @ModelItemId)
      AND (@Prefix          IS NULL OR c.Prefix          = @Prefix)
      AND (@UsageType       IS NULL OR c.UsageType       = @UsageType)
)
SELECT
    b.RecId,
    b.ModelItemId,
    b.ModuleItemId,
    b.ItemId,
    b.Prefix,
    b.UsageType,
    b.KitQty,
    b.Pieces AS RawPieces,
    ISNULL(b.Per_Series, 0) AS PerSeries,
    CAST(ROUND(b.Pieces * b.KitQty, 0) AS int) AS DP_DetailExpandedPieces,
    CEILING(
      (CAST(ROUND(b.Pieces * b.KitQty, 0) AS decimal(38,10)) * b.KitQty) /
      CASE WHEN ISNULL(b.Per_Series,0) <= 0 THEN 1 ELSE b.Per_Series END
    ) AS Dev_RiskPath_DoubleMultiplyWithFallback,
    CEILING(
      (CAST(b.Pieces AS decimal(38,10)) * b.KitQty) /
      CASE WHEN ISNULL(b.Per_Series,0) <= 0 THEN 1 ELSE b.Per_Series END
    ) AS Dev_IntendedRawPath_Normalized
FROM base b
ORDER BY b.DueDateTime, b.Prefix, b.ModelItemId;
```

### Detail math: Prod vs Dev at SQL level
- **Prod:** detail DP pre-expands pieces (`Pieces*KitQty`), then SSRS region behavior decides whether this is final or multiplied again.
- **Dev:** adds denominator normalization capability (`Per_Series`) but still inherits pre-expanded detail pieces; if SSRS multiplies by `KitQty` again, output can inflate to `Pieces*KitQty^2/Per_Series`.
- **Highest-risk row type:** module-origin rows with null/0 `Per_Series` where denominator falls back to `1`.

### Detail math: Prod vs Dev at SSRS level
- **Prod SSRS detail:** observed legacy formulas (`Sum(Pieces)` and `Sum(Pieces)*KitQty`).
- **Dev SSRS detail:** introduces `Ceiling(Sum(Pieces*KitQty)/safe(Max(Per_Series)))` plus legacy leftovers.
- **Result:** Detail is the largest parity-break area and highest risk for double multiplication.

---

## 3) WorkOrderSummary

### Pipeline grain (independent of other reports)
- DP path: `McaCutlistReportDP.processSummaryReport()` grouped path.
- Grouping intent: model/module/cutgroup/site/warehouse/salesline/due/kitqty summary grain.

### Parameterized SQL validation (Prod-aligned summary totals)

```sql
WITH base AS (
    SELECT c.*
    FROM McaCutlist c
    WHERE c.DueDateTime >= @FromDueDate
      AND c.DueDateTime < DATEADD(day, 1, @ToDueDate)
      AND (@InventSiteId    IS NULL OR c.InventSiteId    = @InventSiteId)
      AND (@ShipToWarehouse IS NULL OR c.ShipToWarehouse = @ShipToWarehouse)
      AND (@ModelItemId     IS NULL OR c.ModelItemId     = @ModelItemId)
      AND (@Prefix          IS NULL OR c.Prefix          = @Prefix)
)
SELECT
    b.ModelItemId,
    b.ModuleItemId,
    b.CutGroupId,
    b.InventSiteId,
    b.ShipToWarehouse,
    b.SalesLineRefRecId,
    CONVERT(date, b.DueDateTime) AS DueDate,
    b.KitQty,
    SUM(b.Pieces) AS SumPieces,
    SUM(b.KitQty) AS Prod_Summary_SumKitQty
FROM base b
GROUP BY
    b.ModelItemId,
    b.ModuleItemId,
    b.CutGroupId,
    b.InventSiteId,
    b.ShipToWarehouse,
    b.SalesLineRefRecId,
    CONVERT(date, b.DueDateTime),
    b.KitQty
ORDER BY DueDate, b.ModelItemId, b.ModuleItemId;
```

### Parameterized SQL validation (Dev summary math checks)

```sql
WITH base AS (
    SELECT c.*
    FROM McaCutlist c
    WHERE c.DueDateTime >= @FromDueDate
      AND c.DueDateTime < DATEADD(day, 1, @ToDueDate)
      AND (@InventSiteId    IS NULL OR c.InventSiteId    = @InventSiteId)
      AND (@ShipToWarehouse IS NULL OR c.ShipToWarehouse = @ShipToWarehouse)
      AND (@ModelItemId     IS NULL OR c.ModelItemId     = @ModelItemId)
      AND (@Prefix          IS NULL OR c.Prefix          = @Prefix)
)
SELECT
    b.ModelItemId,
    b.ModuleItemId,
    b.CutGroupId,
    b.InventSiteId,
    b.ShipToWarehouse,
    b.SalesLineRefRecId,
    CONVERT(date, b.DueDateTime) AS DueDate,
    b.KitQty,
    SUM(b.Pieces) AS SumPieces,
    CEILING(SUM(b.KitQty)) AS Dev_Summary_CeilingSumKitQty,
    CEILING(
      SUM(b.Pieces * b.KitQty) /
      NULLIF(CASE WHEN MAX(ISNULL(b.Per_Series,0)) <= 0 THEN 1 ELSE MAX(b.Per_Series) END, 0)
    ) AS Dev_Summary_IfRegionUsesPerSeries
FROM base b
GROUP BY
    b.ModelItemId,
    b.ModuleItemId,
    b.CutGroupId,
    b.InventSiteId,
    b.ShipToWarehouse,
    b.SalesLineRefRecId,
    CONVERT(date, b.DueDateTime),
    b.KitQty
ORDER BY DueDate, b.ModelItemId, b.ModuleItemId;
```

### Summary math: Prod vs Dev at SQL level
- **Prod:** summary quantity regions align to legacy sum behavior.
- **Dev:** observed use of `Ceiling(Sum(KitQty))` in summary regions; per-series math may exist in other regions depending on binding.
- **Impact:** Dev can round up totals where Prod would keep non-integer sums.

### Summary math: Prod vs Dev at SSRS level
- **Prod SSRS summary:** `Sum(KitQty)` style totals.
- **Dev SSRS summary:** `Ceiling(Sum(KitQty))` plus additional fields available in dataset.
- **Result:** Even without per-series denominator, summary totals can differ due to rounding rule change.

---

## Decision Guidance by Report (keep independent)

### WorkOrderCoverSheet
- Decide whether cover quantity is legacy total, rounded kit total, or per-series normalized quantity.
- Use only one expression family per displayed quantity column.

### WorkOrderDetail
- Decide whether DP should send raw pieces or expanded pieces to SSRS.
- If expanded pieces are kept, SSRS must not multiply by `KitQty` again.
- Block/fail data when `Per_Series` is missing for rows expected to use normalized formula.

### WorkOrderSummary
- Confirm whether summary should round (`Ceiling`) or preserve decimal sums.
- Keep summary math definition independent from detail semantics.

## Known Gaps
- Exact runtime menu-item invocation paths and full security privilege mapping are **Not determinable from provided XPO/MD**.
