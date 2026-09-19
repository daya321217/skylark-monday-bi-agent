import re
import numpy as np
import pandas as pd

ALIASES = {
    "deals": {
        "deal name": "deal_name",
        "owner code": "owner_code",
        "client code": "client_code",
        "deal status": "deal_status",
        "close date (a)": "close_date",
        "closure probability": "closure_probability",
        "masked deal value": "deal_value",
        "tentative close date": "tentative_close_date",
        "deal stage": "deal_stage",
        "product deal": "product",
        "sector/service": "sector",
        "created date": "created_date",
    },
    "work_orders": {
        "deal name masked": "deal_name",
        "customer name code": "customer_code",
        "serial #": "serial_no",
        "nature of work": "nature_of_work",
        "last executed month of recurring project": "last_executed_month",
        "execution status": "execution_status",
        "data delivery date": "data_delivery_date",
        "date of po/loi": "po_date",
        "document type": "document_type",
        "probable start date": "start_date",
        "probable end date": "end_date",
        "bd/kam personnel code": "owner_code",
        "sector": "sector",
        "type of work": "work_type",
        "is any skylark software platform part of the client deliverables in this deal?": "software",
        "last invoice date": "last_invoice_date",
        "latest invoice no.": "invoice_no",
        "amount in rupees (excl of gst) (masked)": "contract_value_ex_gst",
        "amount in rupees (incl of gst) (masked)": "contract_value_inc_gst",
        "amount in rupees (excl of gst) (masked)": "contract_value_ex_gst",
        "billed value in rupees (excl of gst.) (masked)": "billed_ex_gst",
        "billed value in rupees (incl. gst.) (masked)": "billed_inc_gst",
        "billed value in rupees (incl. of gst.) (masked)": "billed_inc_gst",
        "billed value in rupees (incl of gst.) (masked)": "billed_inc_gst",
        "collected amount in rupees (incl. gst.) (masked)": "collected_inc_gst",
        "collected amount in rupees (incl. of gst.) (masked)": "collected_inc_gst",
        "collected amount in rupees (incl of gst.) (masked)": "collected_inc_gst",
        "amount to be billed in rs. (exl. of gst) (masked)": "to_bill_ex_gst",
        "amount to be billed in rs. (incl. of gst) (masked)": "to_bill_inc_gst",
        "amount receivable (masked)": "receivable",
        "ar priority account": "ar_priority",
        "quantity by ops": "quantity_ops",
        "quantities as per po": "quantity_po",
        "quantity billed (till date)": "quantity_billed",
        "balance in quantity": "quantity_balance",
        "invoice status": "invoice_status",
        "expected billing month": "expected_billing_month",
        "expected billing month": "expected_billing_month",
        "actual billing month": "actual_billing_month",
        "actual collection month": "actual_collection_month",
        "wo status (billed)": "wo_billed_status",
        "collection status": "collection_status",
        "collection date": "collection_date",
        "billing status": "billing_status",
    }
}

DATE_FIELDS = {
    "close_date", "tentative_close_date", "created_date",
    "data_delivery_date", "po_date", "start_date", "end_date",
    "last_invoice_date", "collection_date"
}
MONEY_FIELDS = {
    "deal_value", "contract_value_ex_gst", "contract_value_inc_gst",
    "billed_ex_gst", "billed_inc_gst", "collected_inc_gst",
    "to_bill_ex_gst", "to_bill_inc_gst", "receivable"
}

def clean_key(s):
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def parse_money(x):
    if pd.isna(x) or str(x).strip() == "":
        return np.nan
    s = str(x).replace(",", "").replace("₹", "").strip()
    # Ignore formulas/labels instead of inventing a number.
    try:
        return float(re.sub(r"[^0-9.\-]", "", s))
    except Exception:
        return np.nan

def normalize_board(raw, kind):
    title_to_id = {clean_key(c["title"]): c["id"] for c in raw["meta"]["columns"]}
    aliases = ALIASES[kind]
    rows = []
    for item in raw["items"]:
        row = {"monday_item_id": item["id"], "item_name": item["name"]}
        for cv in item.get("column_values", []):
            # Resolve by column title from metadata; fall back to column id.
            title = next((c["title"] for c in raw["meta"]["columns"] if c["id"] == cv["id"]), cv["id"])
            canonical = aliases.get(clean_key(title), clean_key(title).replace(" ", "_"))
            row[canonical] = cv.get("text")
        rows.append(row)

    df = pd.DataFrame(rows)

    for c in DATE_FIELDS:
        if c in df:
            df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=False)

    for c in MONEY_FIELDS:
        if c in df:
            df[c] = df[c].map(parse_money)

    for c in df.select_dtypes(include="object").columns:
        if c not in {"monday_item_id"}:
            df[c] = df[c].map(lambda x: np.nan if x is None or str(x).strip() == "" else str(x).strip())

    # Common naming normalization while preserving original values for auditability.
    if "sector" in df:
        df["sector_norm"] = df["sector"].astype("string").str.strip().str.lower().replace({
            "sector/service": pd.NA,
            "": pd.NA
        }).str.title()

    return df

def profile_data(df):
    out = pd.DataFrame({
        "column": df.columns,
        "missing": [int(df[c].isna().sum()) for c in df.columns],
        "missing_pct": [round(float(df[c].isna().mean()*100), 1) for c in df.columns],
        "distinct": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })
    return out.sort_values(["missing_pct", "column"], ascending=[False, True])
