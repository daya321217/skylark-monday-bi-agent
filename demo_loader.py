import io
import pandas as pd


def _detect_header_row(df, kind):
    """Find the real header row in the supplied workbook.

    The Work Orders workbook contains a title/formatting row before the actual
    headers, while the Deals workbook starts with headers immediately.
    """
    targets = {
        "work_orders": {"deal name masked", "execution status", "sector", "amount receivable (masked)"},
        "deals": {"deal name", "deal status", "sector/service"},
    }[kind]
    best_idx, best_score = 0, -1
    for idx in range(min(len(df), 12)):
        vals = {str(v).strip().lower() for v in df.iloc[idx].tolist() if pd.notna(v)}
        score = len(targets & vals)
        if score > best_score:
            best_idx, best_score = idx, score
    return best_idx if best_score > 0 else 0


def xlsx_to_raw(uploaded_file, kind):
    """Convert supplied XLSX into the same raw shape used by Monday mode."""
    raw = pd.read_excel(io.BytesIO(uploaded_file.getvalue()), header=None)
    header_row = _detect_header_row(raw, kind)
    headers = [str(v).strip() if pd.notna(v) else f"Unnamed: {i}" for i, v in enumerate(raw.iloc[header_row].tolist())]
    df = raw.iloc[header_row + 1:].copy()
    df.columns = headers
    # Drop fully empty rows/columns introduced by workbook formatting.
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all").reset_index(drop=True)
    # Some supplied sheets repeat their header row inside the data. Remove those
    # rows so the repeated labels are never treated as business records.
    first_header = str(headers[0]).strip().lower() if headers else ""
    if first_header:
        df = df[df.iloc[:, 0].fillna("").astype(str).str.strip().str.lower().ne(first_header)].reset_index(drop=True)
    # Also remove embedded header rows whose other cells repeat the column labels.
    header_tokens = {str(h).strip().lower() for h in headers}
    def _is_repeated_header(row):
        vals = {str(v).strip().lower() for v in row.tolist() if pd.notna(v)}
        return len(vals & header_tokens) >= max(3, min(6, len(header_tokens) // 2))
    if not df.empty:
        df = df.loc[~df.apply(_is_repeated_header, axis=1)].reset_index(drop=True)

    rows = []
    for i, row in df.iterrows():
        item_name = row.iloc[0] if len(row) else f"Row {i+1}"
        values = []
        for col in df.columns:
            value = row[col]
            text = "" if pd.isna(value) else str(value)
            values.append({"id": str(col), "text": text, "value": text, "type": "text"})
        rows.append({"id": str(i + 1), "name": str(item_name), "created_at": None,
                     "updated_at": None, "column_values": values})

    columns = [{"id": str(c), "title": str(c), "type": "text"} for c in df.columns]
    return {"meta": {"id": "demo", "name": f"Demo {kind}", "state": "active",
                      "permissions": "demo", "columns": columns, "item_count": len(rows),
                      "header_row": header_row + 1},
            "items": rows}
