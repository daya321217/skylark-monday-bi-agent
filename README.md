# 🚁 Skylark Drones — Monday.com Business Intelligence Agent

A Business Intelligence Agent built as a technical assignment for Skylark Drones.

The idea behind this project is simple: instead of manually going through different Monday.com boards to answer business questions, the application brings the data together and turns it into useful, founder-level insights.

The agent connects to Monday.com in read-only mode, processes data from Work Orders and Deal Funnel boards, performs the required calculations, and presents the results through a simple interface.

---

## 💡 What I Built

The application is designed around the kind of questions a founder or business leader might ask, for example:

- What is the pipeline by sector?
- What is the current billed vs collected work-order value?
- Which sectors have strong sales pipeline but weak execution performance?
- How is the business performing overall?
- Can you prepare a leadership update for the weekly business review?

Instead of just displaying raw board data, the application processes it and provides a structured answer along with relevant data caveats.

---

## 🔗 Monday.com Integration

The application connects to two Monday.com boards:

1. **Work Order Tracker**
2. **Deal Funnel**

The boards contain the business data used for the analysis.

The application is **read-only** — it retrieves information from Monday.com but does not create, modify, or delete records.

For development and testing, I also included a **Demo XLSX mode**, so the application can be tested without requiring a live Monday.com connection.

---

## 📊 What the Agent Can Analyse

### Sales Pipeline

The application can calculate and display:

- Number of open deals
- Open pipeline value
- Weighted pipeline
- Pipeline by sector
- Percentage contribution of sectors
- Missing deal values
- Missing probability values

For example, the application can identify how the open pipeline is distributed across sectors such as:

- Tender
- Railways
- DSP
- Mining
- Renewables
- Security and Surveillance
- Powerline
- Construction

---

### Work Order / Operations Data

The application also analyses the Work Orders board and provides:

- Contract value
- Billed value
- Collected value
- Receivables
- Collection against billed value
- Data completeness information

This makes it possible to look at operational and financial information alongside the sales pipeline.

---

### Cross-Board Analysis

One of the main parts of the project is comparing information from both boards.

For example:

> Which sectors have strong sales pipeline but weak execution performance?

The application matches sectors between the Deal Funnel and Work Orders data and displays the available pipeline and execution information together.

If the required information is missing, the application explicitly says so instead of making up a result.

---

## 🧠 How the Agent Works

I separated the data processing from the natural-language part of the application.

The basic flow is:

```text
Monday.com
    │
    ├── Work Order Board
    │
    └── Deal Funnel Board
             │
             ▼
      Data Normalization
             │
             ▼
       Business Analytics
             │
             ▼
     Question Interpretation
             │
             ▼
       Founder-Level Answer

```

The important business calculations are performed by the application first. The LLM is then used for understanding the founder's question, selecting the appropriate analysis, and presenting the result in a readable way.

This keeps financial calculations deterministic instead of relying on the model to perform the arithmetic itself.

---

## ⚠️ Handling Messy Business Data

Real business data is not always complete, so data quality is included in the output.

The application can identify:

- Missing deal values
- Missing deal probabilities
- Missing billing values
- Missing receivables
- Requested sectors that do not exist as exact labels

Instead of silently filling missing values, the application shows a data caveat to the user.

For example, if a requested sector is not present as an exact label, the application does not automatically combine other sectors just because they may be related.

---

## 📈 Leadership Update

The application includes a leadership-update view that brings the important numbers together.

It can present:

- Open pipeline
- Weighted pipeline
- Billed value
- Collected value
- Receivables
- Collection percentage
- Major pipeline signals
- Data risks and caveats
- Suggested follow-up actions

The goal is to turn the underlying board data into something that can be used during a business review.

---

## 🖥️ Application

The interface provides:

- Monday.com connection
- Demo XLSX mode
- Board configuration
- Data refresh
- Founder question input
- Example questions
- Business analysis results
- Data quality information
- Monday board configuration information

The application was tested using the supplied dataset as well as the Monday.com boards created from that data.

---

## 📁 Project Structure

```text
skylark-monday-bi-agent/
│
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
│
├── agent.py
├── analytics.py
├── app.py
├── data_model.py
├── decision_log.md
├── demo_loader.py
├── monday_client.py
│
└── tests/
    └── test_data_model.py
```

### Main Files

| File | Purpose |
|---|---|
| `app.py` | Main Streamlit application and interface |
| `agent.py` | Handles founder-question interpretation and response generation |
| `analytics.py` | Performs business calculations and analysis |
| `data_model.py` | Handles data structures, normalization and value parsing |
| `monday_client.py` | Connects to Monday.com and retrieves board data |
| `demo_loader.py` | Loads the supplied XLSX data for demo mode |
| `decision_log.md` | Documents important implementation decisions |
| `tests/test_data_model.py` | Tests data parsing and normalization |
| `requirements.txt` | Python dependencies |
| `.env.example` | Example environment configuration |

---

## 🧪 Testing

Tests are included for important parts of the data-processing layer, including:

- Money/value parsing
- Board data normalization

The tests are located in:

```text
tests/test_data_model.py
```

Run them with:

```bash
pytest
```

---

## 🔐 Configuration

The application uses environment variables for the Monday.com connection.

The expected configuration is represented in:

```text
.env.example
```

The configuration includes:

```text
MONDAY_API_TOKEN=
WORK_ORDERS_BOARD_ID=
DEALS_BOARD_ID=
OPENAI_MODEL=
```

The actual API token and `.env` file should never be committed to GitHub.

---

## 🚀 Running Locally

### 1. Clone the repository

```bash
git clone <repository-url>
cd skylark-monday-bi-agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the environment

Create a local `.env` file using `.env.example` as a reference.

Add the required Monday.com credentials and board IDs.

### 5. Start the application

```bash
streamlit run app.py
```

The application will open in the browser.

---

## 🔒 Read-Only Design

The Monday.com integration is intentionally read-only.

The application retrieves information required for analysis but does not:

- Create Monday.com items
- Modify existing items
- Delete items
- Change board configuration

---

## 📝 Design Decisions

Important implementation decisions and trade-offs are documented in:

```text
decision_log.md
```

This includes decisions related to data handling, analytics, missing values, and the use of the LLM.

---

## 🎯 What This Project Demonstrates

This project demonstrates practical work with:

- Python
- Streamlit
- Monday.com API
- Data normalization
- Business analytics
- Cross-board analysis
- LLM-assisted question interpretation
- Data quality handling
- Environment configuration
- Automated testing

The main focus was not just displaying raw board data, but turning that data into structured answers to real business questions.

---

## 👩‍💻 Project

**Skylark Drones — Monday.com Business Intelligence Agent**

Built as a technical assignment to demonstrate how operational and sales data from Monday.com can be transformed into structured, founder-level business insights through a simple analytics interface.


