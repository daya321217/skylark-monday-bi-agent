import os
import json
from openai import OpenAI

SYSTEM = """
You are Skylark Drones' Business Intelligence Agent.

Answer founder/executive questions using evidence supplied from read-only Deals and Work Orders data.
Never invent values. Distinguish actual, pipeline, weighted pipeline, billed, collected and receivable.
State assumptions for ambiguous terms. Flag material missing data. Give concise executive context, not just raw numbers.
If the evidence uses the latest available data quarter because the sample is historical, say so explicitly.
If a requested sector is not an exact available sector, do not silently substitute another sector.
For leadership updates use: headline, key metrics, notable signals, risks/caveats, suggested follow-ups.
If evidence is insufficient, say exactly what is missing.
"""


def _money(x):
    if x is None:
        return "N/A"
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "N/A"
    if x != x:
        return "N/A"
    if abs(x) >= 1e7: return f"₹{x/1e7:.2f} Cr"
    if abs(x) >= 1e5: return f"₹{x/1e5:.2f} L"
    return f"₹{x:,.0f}"


def _scope_text(context):
    ts = context.get("time_scope", {})
    if not ts.get("requested"): return "all available data"
    basis = ts.get("basis", "the requested quarter")
    start, end = ts.get("start"), ts.get("end")
    return f"{basis}, {start} to {end}" if start and end else basis


def _leadership(context):
    d, w, dq = context.get("deals", {}), context.get("work_orders", {}), context.get("data_quality", {})
    fm = w.get("financial_totals", {})
    sectors = d.get("pipeline_by_sector", [])
    top = sectors[0] if sectors else None
    billed = fm.get("billed_inc_gst")
    collected = fm.get("collected_inc_gst")
    receivable = fm.get("receivable")
    collection_rate = (float(collected) / float(billed) * 100) if billed not in (None, 0) and collected is not None else None
    lines = [
        "## Leadership Update",
        "",
        f"**Headline:** {d.get('scoped_open_rows', 0)} open deals represent {_money(d.get('scoped_open_pipeline_value'))} of valued pipeline; operational financial visibility covers {w.get('total_rows', 0)} work orders.",
        "",
        "**Key metrics**",
        f"- Open pipeline: **{_money(d.get('scoped_open_pipeline_value'))}**",
        f"- Weighted pipeline: **{_money(d.get('scoped_open_weighted_value'))}**",
        f"- Billed: **{_money(billed)}**",
        f"- Collected: **{_money(collected)}**",
        f"- Receivable: **{_money(receivable)}**",
    ]
    if collection_rate is not None:
        lines.append(f"- Collection against billed value: **{collection_rate:.1f}%**")
    if top:
        lines += ["", "**Notable signal**", f"- **{top.get('sector_norm') or 'Unspecified'}** has the largest valued open pipeline at **{_money(top.get('pipeline_value'))}** across {int(top.get('open_deals', 0))} open deals."]
    lines += [
        "", "**Risks / caveats**",
        f"- {dq.get('deals_missing_value', 0)} deals are missing value and {dq.get('deals_missing_probability', 0)} are missing probability; weighted pipeline therefore understates/does not fully represent the entire open funnel.",
        f"- {dq.get('work_missing_billed', 0)} work orders have missing billed values and {dq.get('work_missing_receivable', 0)} have missing receivables.",
        "", "**Suggested follow-ups**",
        "- Validate high-value open deals with missing probability or value.",
        "- Review receivables and partially billed work orders for near-term cash impact.",
        "- Confirm sector taxonomy before rolling similar labels into a single leadership category.",
    ]
    return "\n".join(lines)


def _rule_based(question, context):
    q = question.lower()
    d, w, dq = context.get("deals", {}), context.get("work_orders", {}), context.get("data_quality", {})
    sector_filter = context.get("applied_sector_filter")
    available = context.get("available_sectors", [])
    scope = _scope_text(context)

    if "leadership" in q or "leadership update" in q or "business review" in q or "weekly update" in q:
        return _leadership(context)

    if any(word in q for word in ["energy sector", "energy"]) and not sector_filter:
        relevant = [s for s in available if s.lower() in {"renewables", "powerline"}]
        return (
            "### Pipeline snapshot\n\n"
            "- **Exact sector match:** None — the dataset does not contain a sector labelled `Energy`.\n"
            f"- **Available potentially relevant labels:** {', '.join(relevant) or ', '.join(available[:8])}.\n"
            "- I have **not** combined those sectors automatically, because that would change the dataset definition.\n\n"
            f"**Time scope:** {scope}.\n\n"
            f"**Data caveat:** {dq.get('deals_missing_value', 0)} deals are missing value and {dq.get('deals_missing_probability', 0)} are missing probability."
        )

    # Cross-board questions must be checked before generic "pipeline + sector" handling.
    if any(x in q for x in ["strong sales pipeline", "weak execution", "sales pipeline but", "cross-board"]):
        p = {str(r.get('sector_norm')): r for r in d.get('pipeline_by_sector', [])}
        ops = {str(r.get('sector_norm')): r for r in w.get('by_sector', [])}
        rows = []
        for sector, pr in p.items():
            if sector == "nan": continue
            op = ops.get(sector, {})
            billed = op.get("billed")
            contract = op.get("contract_value")
            execution_gap = (1 - float(billed) / float(contract)) * 100 if billed is not None and contract not in (None, 0) else None
            rows.append((sector, pr.get("pipeline_value"), execution_gap, op.get("work_orders", 0)))
        rows.sort(key=lambda x: (-(x[1] or 0), -(x[2] or -1)))
        lines = ["### Cross-board sector view", "", "I compared open sales pipeline with billed-versus-contract execution where both boards share an exact sector label."]
        for sector, pipe, gap, wo in rows[:8]:
            gap_txt = f"{gap:.1f}% of contract value remains unbilled" if gap is not None else "execution billing data incomplete"
            lines.append(f"- **{sector}:** {_money(pipe)} open pipeline; {gap_txt}; {int(wo or 0)} work orders")
        lines += ["", "**Caveat:** This is an operational comparison, not a prediction of future performance."]
        return "\n".join(lines)


    if ("pipeline by sector" in q) or ("pipeline" in q and "sector" in q):
        rows = d.get("pipeline_by_sector", [])
        if not rows: return f"### Pipeline by sector\n\nNo valued open deals were found in {scope}."
        lines = ["### Open pipeline by sector", f"\n**Scope:** {scope}\n"]
        total = d.get("scoped_open_pipeline_value") or 0
        for r in rows:
            name = r.get("sector_norm") or "Unspecified"
            share = (float(r.get("pipeline_value") or 0) / float(total) * 100) if total else 0
            lines.append(f"- **{name}:** {int(r.get('open_deals', 0))} open deals, {_money(r.get('pipeline_value'))} ({share:.1f}% of valued pipeline)")
        if rows:
            top = rows[0]
            lines.append(f"\n**Leadership takeaway:** {top.get('sector_norm') or 'Unspecified'} is the largest valued pipeline segment at {_money(top.get('pipeline_value'))}. This is a concentration signal, not a forecast.")
        lines.append(f"\n**Total open pipeline:** {_money(total)} across {d.get('scoped_open_rows', 0)} open deals.")
        lines.append(f"\n**Data caveat:** {dq.get('deals_missing_value', 0)} deals are missing value and {dq.get('deals_missing_probability', 0)} are missing probability.")
        return "\n".join(lines)

    if any(x in q for x in ["billed", "collected", "receivable", "work order", "operations"]):
        fm = w.get("financial_totals", {})
        return (
            "### Operations snapshot\n\n"
            f"- Contract value incl. GST: **{_money(fm.get('contract_value_inc_gst'))}**\n"
            f"- Billed: **{_money(fm.get('billed_inc_gst'))}**\n"
            f"- Collected: **{_money(fm.get('collected_inc_gst'))}**\n"
            f"- Receivable: **{_money(fm.get('receivable'))}**\n\n"
            f"**Data caveat:** {dq.get('work_missing_billed', 0)} work orders have missing billed values and {dq.get('work_missing_receivable', 0)} have missing receivables."
        )

    if "pipeline" in q or "deal" in q:
        return (
            "### Pipeline snapshot\n\n"
            f"- **Open deals in scope:** {d.get('scoped_open_rows', 0)}\n"
            f"- **Open pipeline value:** {_money(d.get('scoped_open_pipeline_value'))}\n"
            f"- **Weighted pipeline:** {_money(d.get('scoped_open_weighted_value'))}\n"
            f"- **Scope:** {scope}\n\n"
            f"**Data caveat:** {dq.get('deals_missing_value', 0)} deals are missing value and {dq.get('deals_missing_probability', 0)} are missing probability, so the financial view is incomplete."
        )

    return "I can analyze pipeline, deals, work-order execution, billing, collection, receivables, sectors, cross-board performance, and leadership updates. Try asking one of those questions."


def answer_question(question, context, model=None):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _rule_based(question, context)
    try:
        client = OpenAI(api_key=api_key)
        model = model or os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        response = client.responses.create(
            model=model, instructions=SYSTEM,
            input=f"Founder question:\n{question}\n\nEvidence:\n{json.dumps(context, default=str, ensure_ascii=False)}",
        )
        return response.output_text
    except Exception:
        return _rule_based(question, context)
