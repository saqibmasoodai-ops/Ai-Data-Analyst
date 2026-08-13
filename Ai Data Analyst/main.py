import re
import sqlite3
from sqlalchemy import create_engine, inspect
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaLLM
 
db_url = "sqlite:///amazon.db"
 
def extract_schema(db_url):
    engine = create_engine(db_url)
    inspector = inspect(engine)
    schema = {}
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        schema[table_name] = [col["name"] for col in columns]
    return json.dumps(schema, indent=4)
 
def clean_sql_query(raw_sql: str) -> str:
    """Strong cleaning to remove markdown, explanations, etc."""
    sql = raw_sql.strip()
 
    # Remove markdown code blocks
    if "```" in sql:
        parts = sql.split("```")
        for part in parts:
            cleaned = part.strip()
            if cleaned.lower().startswith("sql"):
                cleaned = cleaned[3:].strip()
            if cleaned and not cleaned.lower().startswith("sql") and not cleaned.startswith("```"):
                return cleaned
        # Fallback
        sql = parts[1] if len(parts) > 1 else parts[0]
 
    # Remove common unwanted prefixes
    unwanted = ["sql", "SQL", "Here is the query", "The SQL query is", "```sql", "```"]
    for word in unwanted:
        if sql.lower().startswith(word.lower()):
            sql = sql[len(word):].strip()
 
    return sql.strip()
 
def text_to_sql(user_prompt, schema):
    SYSTEM_PROMPT = """
    You are a strict SQL expert for SQLite.
    - Generate ONLY valid SQL SELECT query/queries.
    - NEVER add any explanation, comments, or markdown (no ```sql).
    - Use correct table and column names from the given schema.
    - Always use proper JOIN syntax when combining tables.
 
    - If the user's question contains multiple distinct, unrelated questions
      (for example: "who is the top customer" AND "what are the top products"
      AND "how many orders did X place"), generate a SEPARATE SELECT statement
      for EACH question, separated by a semicolon (;). Do NOT merge unrelated
      questions into a single query with one shared WHERE clause — each
      question must be answered by its own independent, unfiltered query
      unless that specific question itself asks for a filter.
 
    - When filtering by a person's name, ALWAYS use a partial, case-insensitive
      match instead of an exact match, since the user will usually give only a
      first name or partial name rather than the full name stored in the
      database. Use: WHERE name LIKE '%Eve%' (not WHERE name = 'Eve').
      Apply the same LIKE-based partial matching to any other text filters
      such as city or category names.
 
    - Only generate a query for parts of the question that can genuinely be
      answered using the tables and columns in the given schema. If part of
      the question is unrelated to this schema (general knowledge, weather,
      current events, or anything not represented in the tables), do NOT
      invent a fabricated answer or a fake SELECT statement with a hardcoded
      string as the "answer". Simply generate no SQL for that unrelated part
      and only answer the parts that are genuinely about this database.
 
    - Output ONLY the raw SQL query/queries, nothing else.
    """
 
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", "Database Schema:\n{schema}\n\nUser Question: {user_prompt}\n\nReturn only the SQL query:")
    ])
 
    # `timeout` is how long (in seconds) to wait for Ollama to respond
    # before giving up. Increase this if your machine is slow or the model
    # is large — Ollama itself has no fixed limit, this is just a safety cap.
    model = OllamaLLM(model="qwen2.5-coder:7b", temperature=0.0, timeout=120)
 
    chain = prompt_template | model | StrOutputParser()
 
    raw_output = chain.invoke({"schema": schema, "user_prompt": user_prompt})
 
    final_sql = clean_sql_query(raw_output)
    return final_sql
 
 
def is_safe_select(sql_query: str) -> bool:
    """
    Hard security guard: only allow a single SELECT statement.
    Blocks INSERT, UPDATE, DELETE, DROP, ALTER, ATTACH, PRAGMA, etc.
    If ANY statement in a multi-part response fails this, the entire
    response is refused — this check is about preventing data changes,
    so it stays strict and all-or-nothing.
    """
    query = sql_query.strip()
 
    if not query.lower().startswith("select"):
        return False
 
    blocked_keywords = [
        "insert", "update", "delete", "drop", "alter",
        "create", "attach", "detach", "pragma", "replace", "truncate"
    ]
    lowered = query.lower()
    for word in blocked_keywords:
        if word in lowered:
            return False
 
    return True
 
 
def is_real_data_query(sql_query: str) -> bool:
    """
    Detects fabricated/hallucinated 'answers' disguised as SQL, e.g.:
        SELECT 'Amazon CEO is Jeff Bezos.' AS ceo_info
    A genuine question about the sales database always needs to reference
    an actual table via a FROM clause. If there's no FROM clause, this is
    almost certainly a made-up non-answer, not a real data query — so we
    skip it rather than run it and display fabricated content as if it
    came from the database. This is a code-level backstop, since prompt
    instructions alone aren't reliable enough to prevent this on a small
    local model.
    """
    return bool(re.search(r"\bfrom\b", sql_query, re.IGNORECASE))
 
 
def split_sql_statements(sql_text: str) -> list:
    """
    Splits the model's output into individual SQL statements on ';'.
    The model sometimes answers a question with more than one query
    (e.g. one for 'top customer', one for 'top products'). Running
    each separately avoids the sqlite3 'one statement at a time' error.
    """
    return [s.strip() for s in sql_text.split(";") if s.strip()]
 
 
def get_data_from_database(user_prompt):
    """
    Returns a structured dict instead of a pre-formatted string, so the
    frontend can render real tables, download buttons, and metrics.
 
    Shapes returned:
 
    Success:
        {
            "success": True,
            "queries": [
                {"sql": str, "columns": [str, ...], "rows": [tuple, ...]},
                ...
            ],
            "skipped_count": int   # how many parts were fabricated/off-topic and skipped
        }
 
    Failure (refused / no SQL / all parts off-topic / execution error):
        {
            "success": False,
            "kind": "refusal" | "no_sql" | "off_topic" | "error",
            "message": str,
            "sql": str | None   # only set for "error", to show what failed
        }
    """
    sql_text = None
    try:
        schema = extract_schema(db_url)
        sql_text = text_to_sql(user_prompt, schema)
 
        print(f"🔧 Generated SQL:\n{sql_text}\n")   # For debugging
 
        statements = split_sql_statements(sql_text)
 
        if not statements:
            return {
                "success": False,
                "kind": "no_sql",
                "message": "⚠️ No SQL was generated for this question. Try rephrasing it.",
            }
 
        # Hard security check first: if ANY statement is a write/DDL attempt
        # (or isn't a SELECT at all), refuse the whole response outright.
        for stmt in statements:
            if not is_safe_select(stmt):
                return {
                    "success": False,
                    "kind": "refusal",
                    "message": (
                        "⚠️ I can only answer questions about the data — "
                        "I'm not able to add, edit, or delete anything in the database."
                    ),
                }
 
        # Now separate genuine data queries from fabricated/off-topic ones.
        real_statements = [s for s in statements if is_real_data_query(s)]
        skipped_count = len(statements) - len(real_statements)
 
        if not real_statements:
            return {
                "success": False,
                "kind": "off_topic",
                "message": (
                    "That doesn't look related to your sales data — "
                    "I can only answer questions based on what's actually in the database."
                ),
            }
 
        # Open the connection in read-only mode as a hard safety net.
        # Even if a query somehow slipped past the checks above, SQLite
        # itself will refuse to execute any write against a read-only connection.
        conn = sqlite3.connect("file:amazon.db?mode=ro", uri=True, timeout=30)
        cursor = conn.cursor()
 
        queries = []
        for stmt in real_statements:
            cursor.execute(stmt)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            queries.append({"sql": stmt, "columns": columns, "rows": rows})
 
        conn.close()
        return {"success": True, "queries": queries, "skipped_count": skipped_count}
 
    except Exception as e:
        return {
            "success": False,
            "kind": "error",
            "message": f"❌ Error: {str(e)}",
            "sql": sql_text,
        }
 