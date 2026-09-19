import pandas as pd
import numpy as np

PROB = {"high": 0.75, "medium": 0.50, "low": 0.25}


def _fmt_inr(x):
    if x is None or pd.isna(x):
        return "N/A"
    x = float(x)
    if abs(x) >= 1e7:
        return f"₹{x/1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x/1e5:.2f} L"
    return f"₹{x:,.0f}"


def _quarter_dates(today=None):
    today = pd.Timestamp.today().normalize() if today is None else pd.Timestamp(today).normalize()
    q = (today.month - 1) // 3
    start = pd.Timestamp(year=today.year, month=q * 3 + 1, day=1)
    end = start + pd.offsets.QuarterEnd()
    return start, end


def _latest_data_date(deals):
    candidates = []
    for c in ("tentative_close_date", "close_date", "created_date"):
        if c in deals:
            s = pd.to_datetime(deals[c], errors="coerce").dropna()
            if not s.empty:
                candidates.append(s.max())
    return max(candidates) if candidates else None


def _quarter_label(start, end):
    return f"Q{((start.month - 1) // 3) + 1} {start.year}"


def _requested_sector(question, available):
    q = question.lower()
    normalized = {str(x).strip().lower(): x for x in available if pd.notna(x)}
    for key in sorted(normalized, key=len, reverse=True):
        if key and key in q:
            return normalized[key]
    return None


def _has_quarter_scope(question):
    q = question.lower()
    return any(term in q for term in (
        "this quarter", "current quarter", "latest quarter", "this qtr", "current qtr"
    ))


def _has_last_quarter_scope(question):
    q = question.lower()
    return "last quarter" in q or "previous quarter" in q


def _has_next_quarter_scope(question):
    return "next quarter" in question.lower()


def _quarter_scope_for_question(deals, question):
    if not (_has_quarter_scope(question) or _has_last_quarter_scope(question) or _has_next_quarter_scope(question)):
        return None, None, "all available data"

    today = pd.Timestamp.today().normalize()
    current_start, current_end = _quarter_dates(today)
    latest = _latest_data_date(deals)

    if latest is not None and latest < current_start:
        anchor_start, anchor_end = _quarter_dates(latest)
        basis = f"latest available data quarter ({_quarter_label(anchor_start, anchor_end)})"
    else:
        anchor_start, anchor_end = current_start, current_end
        basis = f"calendar quarter ({_quarter_label(anchor_start, anchor_end)})"

    if _has_last_quarter_scope(question):
        start = (anchor_start - pd.offsets.QuarterBegin(startingMonth=1)).to_period("Q").start_time
        end = start.to_period("Q").end_time.normalize()
        basis = f"previous quarter ({_quarter_label(start, end)})"
    elif _has_next_quarter_scope(question):
        start = (anchor_end + pd.Timedelta(days=1)).to_period("Q").start_time
        end = start.to_period("Q").end_time.normalize()
        basis = f"next quarter ({_quarter_label(start, end)})"
    else:
        start, end = anchor_start, anchor_end
    return start, end, basis


def _sector_table(df):
    if "sector_norm" not in df or "deal_value" not in df:
        return pd.DataFrame()
    x = df[df["deal_status"].astype("string").str.lower().eq("open")].copy()
    if x.empty:
        return pd.DataFrame()
    return (x.groupby("sector_norm", dropna=False)
            .agg(open_deals=("deal_status", "size"), pipeline_value=("deal_value", "sum"),
                 valued_deals=("deal_value", lambda s: int(s.notna().sum())))
            .reset_index()
            .sort_values("pipeline_value", ascending=False, na_position="last"))


def build_context(work, deals, question):
    quarter_start, quarter_end, quarter_basis = _quarter_scope_for_question(deals, question)
    d = deals.copy()
    w = work.copy()

    available_sectors = d["sector_norm"].dropna().unique().tolist() if "sector_norm" in d else []
    sector = _requested_sector(question, available_sectors)
    if sector and "sector_norm" in d:
        d = d[d["sector_norm"].eq(sector)]
    if sector and "sector_norm" in w:
        w = w[w["sector_norm"].eq(sector)]

    open_mask = d["deal_status"].astype("string").str.lower().eq("open") if "deal_status" in d else pd.Series(True, index=d.index)
    open_deals = d[open_mask]

    q_deals = d.copy()
    if quarter_start is not None:
        # Prefer tentative close date; fall back to close date for rows where tentative is missing.
        if "tentative_close_date" in d or "close_date" in d:
            t = d.get("tentative_close_date", pd.Series(pd.NaT, index=d.index))
            c = d.get("close_date", pd.Series(pd.NaT, index=d.index))
            effective = pd.to_datetime(t, errors="coerce").fillna(pd.to_datetime(c, errors="coerce"))
            q_deals = d[effective.between(quarter_start, quarter_end, inclusive="both")].copy()

    q_open = q_deals[q_deals["deal_status"].astype("string").str.lower().eq("open")] if "deal_status" in q_deals else q_deals

    weighted = 0.0
    if "deal_value" in q_open:
        probs = q_open.get("closure_probability", pd.Series(index=q_open.index, dtype=object)).astype("string").str.lower().map(PROB)
        weighted = float((q_open["deal_value"].fillna(0) * probs.fillna(0)).sum())

    work_metrics = {}
    for c in ["contract_value_inc_gst", "billed_inc_gst", "collected_inc_gst", "to_bill_inc_gst", "receivable"]:
        if c in w:
            work_metrics[c] = float(w[c].sum(min_count=1)) if not w.empty else 0

    pipeline_by_sector = _sector_table(q_deals)

    # Operational sector view for cross-board questions.
    work_by_sector = pd.DataFrame()
    if "sector_norm" in w:
        agg = {"work_orders": ("sector_norm", "size")}
        if "contract_value_inc_gst" in w: agg["contract_value"] = ("contract_value_inc_gst", "sum")
        if "billed_inc_gst" in w: agg["billed"] = ("billed_inc_gst", "sum")
        if "collected_inc_gst" in w: agg["collected"] = ("collected_inc_gst", "sum")
        if "receivable" in w: agg["receivable"] = ("receivable", "sum")
        work_by_sector = w.groupby("sector_norm", dropna=False).agg(**agg).reset_index()

    status_counts = d["deal_status"].astype("string").str.title().value_counts(dropna=False).to_dict() if "deal_status" in d else {}
    exec_counts = w["execution_status"].value_counts(dropna=False).to_dict() if "execution_status" in w else {}

    missing_value_open = int(q_open["deal_value"].isna().sum()) if "deal_value" in q_open else None
    valued_open = int(q_open["deal_value"].notna().sum()) if "deal_value" in q_open else None
    missing_prob_open = int(q_open["closure_probability"].isna().sum()) if "closure_probability" in q_open else None

    evidence = {
        "as_of": str(pd.Timestamp.today().normalize().date()),
        "time_scope": {
            "requested": bool(quarter_start is not None), "basis": quarter_basis,
            "start": str(quarter_start.date()) if quarter_start is not None else None,
            "end": str(quarter_end.date()) if quarter_end is not None else None,
        },
        "applied_sector_filter": sector,
        "available_sectors": sorted([str(x) for x in available_sectors]),
        "deals": {
            "total_rows": len(deals), "rows_in_scope": len(d), "open_rows": len(open_deals),
            "scoped_rows": len(q_deals), "scoped_open_rows": len(q_open),
            "scoped_open_pipeline_value": float(q_open["deal_value"].sum(min_count=1)) if "deal_value" in q_open else None,
            "scoped_open_weighted_value": weighted,
            "scoped_open_missing_value_rows": missing_value_open,
            "scoped_open_valued_rows": valued_open,
            "scoped_open_missing_probability_rows": missing_prob_open,
            "status_counts": status_counts,
            "pipeline_by_sector": pipeline_by_sector.to_dict("records") if not pipeline_by_sector.empty else [],
        },
        "work_orders": {
            "total_rows": len(work), "rows_in_scope": len(w), "execution_status": exec_counts,
            "financial_totals": work_metrics,
            "by_sector": work_by_sector.where(pd.notna(work_by_sector), None).to_dict("records") if not work_by_sector.empty else [],
        },
        "data_quality": {
            "deals_missing_value": int(deals["deal_value"].isna().sum()) if "deal_value" in deals else None,
            "deals_missing_tentative_close": int(deals["tentative_close_date"].isna().sum()) if "tentative_close_date" in deals else None,
            "deals_missing_probability": int(deals["closure_probability"].isna().sum()) if "closure_probability" in deals else None,
            "work_missing_billed": int(work["billed_inc_gst"].isna().sum()) if "billed_inc_gst" in work else None,
            "work_missing_receivable": int(work["receivable"].isna().sum()) if "receivable" in work else None,
        },
    }
    return evidence
