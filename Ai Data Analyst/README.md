# 🤖 AI Data Analyst

A natural-language-to-SQL chatbot that lets you query a sales database using plain English. Ask questions like *"Who is the top spending customer?"* or *"Show me sales by city"*, and the app converts them into SQL, runs them safely against a SQLite database, and returns the results as interactive tables, metrics, and downloadable CSVs — all through a local, chat-style Streamlit interface.

## Demo

![AI Data Analyst demo](Recording%202026-08-13%20170511.gif)

## Overview

The app inspects the schema of a SQLite database, sends it along with your question to a locally running LLM (via [Ollama](https://ollama.com/)), and asks the model to generate one or more SQL `SELECT` queries. Every query is validated before it runs, executed against a **read-only** database connection, and the results are displayed as proper tables — with big-number highlights for single-value answers and one-click CSV export.

Everything runs **locally** — no external API keys or cloud LLM calls are required, since inference happens through Ollama on your own machine.

## Features

- 💬 **Chat-style interface** — ask questions naturally, with full conversation history kept on screen
- 🧠 **Natural-language-to-SQL** conversion using a local LLM via Ollama
- 🗂️ **Multi-part question handling** — a single question like *"top customer, top products, and Eve's orders"* is automatically split into separate queries and answered together
- 📊 **Real results, not text dumps** — data tables, big-number metrics for single-value answers, and CSV downloads
- 🛡️ **Built-in safety guards** — see [Safety & Guardrails](#safety--guardrails) below
- 🧹 **Hallucination filtering** — fabricated "answers" to off-topic questions (weather, general knowledge) are detected and skipped instead of displayed as if they were real data
- 🎯 **Partial name/city/category matching** — "Eve" correctly matches "Eve Brown" instead of requiring an exact name
- 🧪 Includes a script to generate a realistic sample "Amazon sales" database to test against

## Tech Stack

| Component            | Technology                          |
|-------------------------|--------------------------------------|
| UI                    | [Streamlit](https://streamlit.io/)  |
| LLM Orchestration     | [LangChain](https://www.langchain.com/) |
| LLM Runtime           | [Ollama](https://ollama.com/) (`qwen2.5-coder`) |
| Database              | SQLite                              |
| Schema Inspection     | SQLAlchemy                          |
| Data Display          | pandas                              |

## Safety & Guardrails

This app is designed so the LLM can never modify or delete your data, no matter how it's asked:

- **SELECT-only enforcement** — any generated query that isn't a plain `SELECT`, or that contains a write/DDL keyword (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, etc.), is rejected before it ever runs.
- **Read-only database connection** — as a hard backstop, the database is opened in SQLite's read-only mode. Even if a harmful query somehow slipped past validation, the database engine itself would refuse to execute it.
- **Hallucination filtering** — queries that don't reference an actual table (a telltale sign of a fabricated, non-data answer) are filtered out rather than executed and shown as if they were real.

Try asking it to *"delete all customers"* — it will politely decline instead of touching the database.

## Getting Started

### Prerequisites

- Python 3.9+
- [Ollama](https://ollama.com/download) installed and running locally
- A model pulled in Ollama, for example:
  ```bash
  ollama pull qwen2.5-coder:3b
  ```
  > 💡 On lower-spec machines (no dedicated GPU, 8GB RAM), a smaller model like `qwen2.5-coder:3b` or `1.5b` performs noticeably faster than the full `7b` version, with minimal accuracy loss for SQL generation.

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/saqibmasoodai-ops/Ai-Data-Analyst.git
   cd Ai-Data-Analyst
   ```

2. Install dependencies with [uv](https://docs.astral.sh/uv/)
   ```bash
   uv add streamlit sqlalchemy langchain-core langchain-ollama pandas
   ```

### Set Up the Database

Generate the sample SQLite database with realistic Amazon-style sales data:

```bash
uv run python create-database.py
```

This creates `amazon.db` with four related tables: `customers`, `products`, `orders`, and `order_items`.

> ⚠️ If you change the model name in `main.py`, make sure it matches a model you've pulled with `ollama pull`.

### Run the App

Make sure Ollama is running in the background, then start the app:

```bash
uv run streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

## Usage

1. Launch the app and make sure Ollama is running.
2. Type a question in the chat box, or click one of the sample questions in the sidebar — for example:
   - *What is the total revenue?*
   - *Show me sales by city*
   - *Who is the top spending customer?*
   - *What are the top selling products?*
   - *How many orders did Eve from Lahore place?*
3. View the generated SQL (in the collapsible section), the results table or metric, and download the results as CSV if needed.
4. Ask follow-up questions — your conversation stays visible, and "Clear conversation" resets it.

## Project Structure

```
.
├── create-database.py    # Generates the sample SQLite database with test data
├── main.py                 # Core logic: schema extraction, text-to-SQL, safety guards, query execution
├── app.py                   # Streamlit chat interface
├── amazon.db                 # Generated SQLite database (created after running create-database.py)
├── assets/
│   └── demo.gif                # App demo (see Demo section above)
└── README.md
```

## How It Works

1. **Schema Extraction** — `extract_schema()` uses SQLAlchemy to inspect `amazon.db` and list every table and column.
2. **Prompting** — The schema and your question are sent to the local LLM through a system prompt instructing it to return only raw SQL `SELECT` statement(s), split multi-part questions into separate queries, and use partial (`LIKE`) matching for names.
3. **Cleaning** — Markdown, labels, and stray text are stripped from the model's raw output.
4. **Validation** — Each statement is checked: is it a safe `SELECT`? Does it reference a real table (ruling out fabricated answers)?
5. **Execution** — Valid queries run against a read-only SQLite connection.
6. **Display** — Results are rendered as tables, metrics, or CSV downloads, with the underlying SQL available for inspection.

## Known Limitations

- Model accuracy depends on the size of the local model you run — smaller models (better suited to low-spec hardware) may occasionally misinterpret ambiguous or highly complex multi-join questions.
- Only a single, hardcoded database (`amazon.db`) is supported — no file upload or database switcher yet.
- Each question is handled independently; there's no cross-question memory beyond what's visible in the chat history.
- Requires Ollama running locally, which needs a reasonably capable machine — see the model size note under Prerequisites.

## License

This project is licensed under the [MIT License](LICENSE).