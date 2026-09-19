# Skylark Drones — Decision Log

## 1. Interpretation of the problem

I interpreted the assignment as a **read-only executive BI agent** over two operational
sources: Deals (commercial pipeline) and Work Orders (execution/billing/collection).
The agent should answer natural-language questions while making data-quality limitations
visible instead of hiding them.

I treated the current quarter as the calendar quarter containing the current date. When
a founder asks for "pipeline", the default is open deals; when they ask for weighted
pipeline, closure probability is applied to open deal value using High=75%, Medium=50%,
Low=25%. Missing probability contributes no weighted value and is disclosed.

## 2. Architecture choice

I chose **Python + Streamlit + Monday GraphQL API + OpenAI Responses API**.

Why:
- Streamlit provides a conversational prototype quickly within the six-hour constraint.
- Monday's GraphQL API provides direct read access to boards and cursor pagination.
- Pandas is appropriate for normalization and deterministic BI calculations.
- The LLM is used for interpretation and synthesis, not as the calculator of record.

The Monday client is deliberately read-only: it performs board/item queries and no
mutations.

## 3. Data resilience decisions

The source files contain nulls, inconsistent/masked values, mixed date completeness,
and categorical inconsistencies. I therefore:
- normalize date fields with coercion;
- parse numeric/currency fields conservatively;
- normalize sectors for grouping;
- preserve raw values where possible;
- calculate missingness metrics;
- expose material caveats in the final answer.

A missing value is not replaced with zero unless the metric definition explicitly makes
that safe. In particular, missing deal value is excluded from monetary sums and called
out.

## 4. Query understanding

The first implementation uses a deterministic analytics layer to calculate core
metrics, with query-aware sector filtering. The LLM then turns those metrics and
relevant evidence into a founder-level response.

If two interpretations would materially change the result, the agent is instructed to
ask a clarification rather than silently guessing.

## 5. Leadership updates

I interpreted the optional "leadership update" requirement as a concise weekly executive
brief containing:
1. a headline;
2. 3–5 decision-relevant metrics;
3. notable operational/pipeline movements or risks;
4. data-quality caveats;
5. suggested follow-up questions/actions.

The agent does not claim that an action was taken; it only prepares the update.

## 6. Trade-offs

**Speed vs. production depth:** Streamlit was selected over a custom React/FastAPI
application because the assignment is a six-hour prototype.

**Full-board reads vs. server-side filtering:** the prototype reads each board dynamically
and paginates it, then performs analysis locally. This makes cross-board analysis simple
for the supplied data size. For much larger boards, server-side `items_page` filtering
and query-specific retrieval would reduce latency and token usage.

**Personal API token vs. OAuth:** a personal V2 token is simpler for an assignment. A
production deployment should use OAuth/secret management and application-level access
controls.

## 7. What I would do with more time

- Add OAuth and evaluator login.
- Add a formal metric dictionary: pipeline, weighted pipeline, booked revenue,
  billed revenue, collected revenue, receivables, backlog.
- Add historical snapshots to support true trend/change questions.
- Add automated data-quality tests and regression tests.
- Add charts and downloadable leadership briefs.
- Add caching, retries and observability.
- Add query planning so only relevant Monday rows are retrieved for large boards.
- Add a proper semantic layer for joining deals and work orders using stable IDs where
  the source system provides them.

## 8. Known limitation

The supplied datasets contain masked identifiers and incomplete financial/date fields.
Therefore some founder questions can only be answered as directional analysis, not as
a complete financial ledger. The agent is designed to state that limitation explicitly.
