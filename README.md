# Skylark Drones — Monday.com Business Intelligence Agent

## Architecture

```text
Founder question
      |
      v
Streamlit conversational UI
      |
      +--> Monday GraphQL API (read-only)
      |       +--> Work Orders board
      |       +--> Deals board
      |
      v
Normalization / data-quality layer
      |
      v
Deterministic analytics + query-aware filtering
      |
      v
OpenAI Responses API
      |
      v
Founder-ready answer + caveats + follow-ups
```

The agent does **not** embed the supplied CSV/XLSX rows in code. Every production answer
is based on a fresh read from Monday.com.

## 1. Monday.com setup

Import the supplied files as two separate boards:

- `Work Orders`
- `Deals`

Recommended column types:

### Deals
- Deal Name — item name / text
- Owner code — text
- Client Code — text
- Deal Status — Status
- Close Date (A) — Date
- Closure Probability — Status or Dropdown
- Masked Deal value — Numbers
- Tentative Close Date — Date
- Deal Stage — Status/Dropdown
- Product deal — Dropdown/Text
- Sector/service — Dropdown/Text
- Created Date — Date

### Work Orders
Use Date columns for dates, Numbers for rupee amounts/quantities, Status for
execution/billing/invoice statuses, and Text/Dropdown for categorical identifiers.

The API client reads column metadata dynamically, so the exact internal Monday column
IDs do not need to be hardcoded.

## 2. Authentication

Create a Monday personal V2 API token with board read access. The token should be
provided as an environment variable; never commit it.

Create an OpenAI API key and provide it as `OPENAI_API_KEY`.

## 3. Run locally

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Fill `.env`, then:

```bash
streamlit run app.py
```

## 4. Hosted prototype

Deploy this repository to Streamlit Community Cloud (or another Python hosting
provider). Add the following secrets/environment variables in the hosting platform:

- MONDAY_API_TOKEN
- WORK_ORDERS_BOARD_ID
- DEALS_BOARD_ID
- OPENAI_API_KEY
- OPENAI_MODEL

No local setup is required for the evaluator after deployment.

## 5. Read-only design

The integration only uses Monday GraphQL queries (`boards`, `items_page`,
`next_items_page`). There are no Monday mutations in this project.

The board API uses cursor-based pagination, so larger boards are read in pages rather
than assuming a fixed row count.

## 6. Data resilience

The normalization layer:
- converts inconsistent date strings with `pandas.to_datetime(errors="coerce")`
- converts masked/currency values into numeric values where safely parseable
- converts blanks to nulls
- normalizes sector names for grouping while preserving the raw value
- tracks missing values
- does not manufacture missing probabilities or values

## 7. Example questions

- How is the pipeline looking for Mining this quarter?
- What is our open pipeline by sector?
- What is the weighted pipeline for Renewables?
- Which work orders have the biggest billing exposure?
- How much has been billed, collected and left to bill?
- What operational issues should leadership know about?
- Prepare a leadership update for this week.

## 8. Production hardening

For a longer implementation:
- add OAuth rather than a personal token
- cache board reads for a short TTL
- add retries/backoff for transient API failures
- add audit logging and request IDs
- use a semantic metric layer with explicit definitions for revenue/pipeline
- add automated tests against a synthetic Monday response fixture
- restrict LLM context to query-relevant rows for larger boards
- add authentication to the hosted app
