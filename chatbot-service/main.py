"""
DataPulse Text2SQL Multi-Agent Chatbot
Implements a real LangGraph StateGraph with 6 specialized agents:
  Guardrails → SQL Generator → SQL Executor → Error Handler → Analyzer → Viz Decision → Visualizer
"""
import os
import json
import logging
from typing import TypedDict, Optional, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from langgraph.graph import StateGraph, END

from sqlalchemy import create_engine, text
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("datapulse-chatbot")

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

USE_MOCK = os.environ.get("OPENAI_API_KEY") is None
DB_URL   = os.environ.get("DATABASE_URL", "mysql+pymysql://root:Ayhan2929.@localhost:3306/datapulse_ecommerce")

if not USE_MOCK:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

try:
    engine = create_engine(DB_URL, pool_pre_ping=True)
    logger.info("Database connection configured.")
except Exception as e:
    engine = None
    logger.warning(f"DB engine creation failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Database Schema (used in SQL prompts)
# ─────────────────────────────────────────────────────────────────────────────

DB_SCHEMA = """
MySQL Database Schema for DataPulse E-Commerce Platform:

users          (id, full_name, email, role ENUM('ADMIN','CORPORATE','INDIVIDUAL'), gender, age, city, country, enabled, created_at)
stores         (id, owner_id→users, name, description, is_open, created_at)
categories     (id, name, parent_id→categories)
products       (id, store_id→stores, category_id→categories, name, description, sku, price DECIMAL, stock INT, image_url, rating, review_count, created_at)
orders         (id, user_id→users, order_number, status ENUM('PENDING','PROCESSING','SHIPPED','DELIVERED','CANCELLED'), total_amount DECIMAL, payment_method, order_date)
order_items    (id, order_id→orders, product_id→products, quantity INT, unit_price DECIMAL)
shipments      (id, order_id→orders, tracking_number, warehouse_block, mode_of_shipment, status, customer_care_calls, shipped_date, delivery_date)
reviews        (id, user_id→users, product_id→products, star_rating INT, review_text, helpful_votes, total_votes, created_at)
cart_items     (id, user_id→users, product_id→products, quantity INT)
wishlist_items (id, user_id→users, product_id→products)
customer_profiles (id, user_id→users, membership_type, total_spend DECIMAL, items_purchased INT, avg_rating DECIMAL, discount_applied BOOLEAN, satisfaction_level)
"""

# ─────────────────────────────────────────────────────────────────────────────
# Agent State
# ─────────────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    question:           str
    role:               str          # INDIVIDUAL | CORPORATE | ADMIN
    user_id:            Optional[int]
    is_in_scope:        bool
    is_greeting:        bool
    sql_query:          Optional[str]
    query_result:       Optional[str]
    error:              Optional[str]
    error_message:      Optional[str]
    final_answer:       Optional[str]
    needs_viz:          bool
    visualization_code: Optional[str]
    iteration_count:    int

# ─────────────────────────────────────────────────────────────────────────────
# Node Functions
# ─────────────────────────────────────────────────────────────────────────────

GREETING_KW  = ["hello","hi","merhaba","selam","hey","nasılsın","naber","hey there"]
IN_SCOPE_KW  = ["sales","order","customer","revenue","product","review","satış","ürün",
                "sipariş","gelir","müşteri","değerlendirme","store","mağaza","shipment",
                "kargo","category","kategori","stock","stok","payment","ödeme",
                "inventory","envanter","top","en çok","trend","analyse","analiz"]


def guardrails_node(state: AgentState) -> AgentState:
    """Guardrails Agent — filters greetings and out-of-scope queries."""
    q = state["question"].lower()

    if any(k in q for k in GREETING_KW):
        state["is_greeting"]  = True
        state["is_in_scope"]  = False
        state["final_answer"] = (
            "Merhaba! Ben DataPulse AI Asistanım 👋\n\n"
            "E-ticaret verileriniz hakkında doğal dil ile sorular sorabilirsiniz. Örneğin:\n"
            "• 'Geçen ayki toplam satışlar ne kadar?'\n"
            "• 'En çok satan 5 ürünü göster'\n"
            "• 'Kategori bazlı gelir dağılımı'\n"
            "• 'Beklemedeki sipariş sayısı kaç?'"
        )
        return state

    state["is_greeting"] = False

    if USE_MOCK:
        state["is_in_scope"] = any(k in q for k in IN_SCOPE_KW)
        if not state["is_in_scope"]:
            state["final_answer"] = (
                "Bu soru e-ticaret veri analizimizin kapsamı dışında. "
                "Lütfen satışlar, siparişler, ürünler veya müşteriler hakkında sorular sorun."
            )
        return state

    prompt = (
        "You are a strict guardrails system for an e-commerce analytics platform.\n"
        "Determine if the question is related to e-commerce data analysis "
        "(sales, orders, products, customers, reviews, shipments, revenue, inventory, stores).\n"
        "Reply with exactly one word: SCOPE or OUT_OF_SCOPE\n\n"
        f"Question: {state['question']}"
    )
    try:
        ans = llm.invoke([HumanMessage(content=prompt)]).content.strip().upper()
        state["is_in_scope"] = "OUT" not in ans and "SCOPE" in ans
    except Exception:
        state["is_in_scope"] = any(k in q for k in IN_SCOPE_KW)

    if not state["is_in_scope"]:
        state["final_answer"] = (
            "Bu soru e-ticaret veri analizimizin kapsamı dışında. "
            "Satışlar, siparişler, ürünler veya müşteriler hakkında sorular sorun."
        )
    return state


def sql_generator_node(state: AgentState) -> AgentState:
    """SQL Agent — converts natural language to a MySQL SELECT query."""
    role    = state.get("role", "INDIVIDUAL")
    user_id = state.get("user_id")

    role_ctx = ""
    if role == "INDIVIDUAL" and user_id:
        role_ctx = (
            f"\nIMPORTANT: This is INDIVIDUAL user with user_id={user_id}. "
            "ALL queries MUST filter by user_id to show ONLY this user's data."
        )
    elif role == "CORPORATE":
        role_ctx = "\nIMPORTANT: This is a CORPORATE user. Restrict data to their own store."
    else:
        role_ctx = "\nThis is an ADMIN user — full platform access, no restrictions."

    prev_err = state.get("error_message", "")
    fix_hint = f"\nPrevious attempt failed with: {prev_err}\nFix that error." if prev_err else ""

    if USE_MOCK:
        state["sql_query"]     = (
            "SELECT c.name AS category, "
            "SUM(oi.unit_price * oi.quantity) AS total_revenue "
            "FROM order_items oi "
            "JOIN products p ON oi.product_id = p.id "
            "LEFT JOIN categories c ON p.category_id = c.id "
            "GROUP BY c.name ORDER BY total_revenue DESC LIMIT 10;"
        )
        state["error"]         = None
        state["error_message"] = None
        return state

    prompt = (
        f"You are a senior MySQL developer for an e-commerce analytics platform.\n"
        f"{DB_SCHEMA}\n"
        f"{role_ctx}{fix_hint}\n"
        "Rules:\n"
        "1. Return ONLY the raw SQL — no markdown, no explanation\n"
        "2. Only SELECT statements (never INSERT/UPDATE/DELETE/DROP/ALTER)\n"
        "3. LIMIT 100 rows maximum\n"
        "4. Use table aliases for readability\n"
        "5. Handle NULLs with COALESCE\n\n"
        f"Question: {state['question']}\n"
        "SQL:"
    )
    try:
        raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        sql = raw.replace("```sql", "").replace("```", "").strip()
        if not sql.endswith(";"):
            sql += ";"
        state["sql_query"]     = sql
        state["error"]         = None
        state["error_message"] = None
    except Exception as ex:
        state["error"]         = "generation_failed"
        state["error_message"] = str(ex)
    return state


def sql_executor_node(state: AgentState) -> AgentState:
    """Executes the SQL query safely against the MySQL database."""
    sql = state.get("sql_query", "")
    if not sql:
        state["error"] = "no_sql"
        return state

    sql_up = sql.upper().strip()

    # Security: only allow SELECT
    if not sql_up.startswith("SELECT"):
        state["error"]         = "security_violation"
        state["error_message"] = "Only SELECT statements are permitted."
        state["final_answer"]  = "Güvenlik kısıtlaması: Yalnızca SELECT sorguları çalıştırılabilir."
        return state

    for kw in ["DROP","DELETE","INSERT","UPDATE","TRUNCATE","ALTER","CREATE","EXEC","GRANT"]:
        if kw in sql_up:
            state["error"]         = "security_violation"
            state["error_message"] = f"Forbidden keyword: {kw}"
            state["final_answer"]  = "Güvenlik kısıtlaması: Bu tür bir sorgu çalıştırılamaz."
            return state

    if engine is None:
        # No DB connection — return mock data
        state["query_result"]  = json.dumps([{"category": "Elektronik", "total_revenue": 45000},
                                              {"category": "Giyim",      "total_revenue": 32000}])
        state["error"]         = None
        state["error_message"] = None
        return state

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows   = result.fetchmany(100)
            cols   = list(result.keys())
            df     = pd.DataFrame(rows, columns=cols)
            state["query_result"]  = df.to_json(orient="records", default_handler=str) if not df.empty else "[]"
            state["error"]         = None
            state["error_message"] = None
    except Exception as ex:
        state["error"]         = "sql_error"
        state["error_message"] = str(ex)
        state["query_result"]  = None
    return state


def error_handler_node(state: AgentState) -> AgentState:
    """Error Agent — diagnoses and fixes failed SQL queries (max 3 retries)."""
    state["iteration_count"] = state.get("iteration_count", 0) + 1

    if state["iteration_count"] >= 3:
        state["final_answer"] = (
            "Sorgu 3 denemeden sonra çalıştırılamadı. "
            "Lütfen sorunuzu daha basit veya spesifik bir şekilde tekrar deneyin."
        )
        state["error"] = "max_retries"
        return state

    if USE_MOCK:
        state["sql_query"]     = "SELECT 1 AS result;"
        state["error"]         = None
        state["error_message"] = None
        return state

    prompt = (
        f"You are a MySQL expert. Fix the SQL error below.\n\n"
        f"Original question: {state['question']}\n"
        f"Failed SQL:\n{state['sql_query']}\n"
        f"Error: {state['error_message']}\n\n"
        f"{DB_SCHEMA}\n"
        "Return ONLY the corrected SQL query:"
    )
    try:
        fixed = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        fixed = fixed.replace("```sql", "").replace("```", "").strip()
        if not fixed.endswith(";"):
            fixed += ";"
        state["sql_query"]     = fixed
        state["error"]         = None
        state["error_message"] = None
    except Exception as ex:
        state["error"]         = "fix_failed"
        state["error_message"] = str(ex)
    return state


def analysis_node(state: AgentState) -> AgentState:
    """Analysis Agent — explains query results in natural language."""
    result = state.get("query_result", "[]")

    if result == "[]" or not result:
        state["final_answer"] = "Sorgunuz için herhangi bir veri bulunamadı."
        return state

    if USE_MOCK:
        state["final_answer"] = (
            "Analiz tamamlandı. Veriler başarıyla getirildi. "
            "Kategori bazlı gelir incelendiğinde Elektronik kategorisinin öne çıktığı görülmektedir. "
            "Detaylı veriler aşağıdaki grafikte görüntülenebilir."
        )
        return state

    prompt = (
        "You are a helpful data analyst. Explain these database results to a business user.\n"
        "Be concise (2-4 sentences) and highlight key findings.\n"
        "Respond in the same language as the question.\n\n"
        f"Question: {state['question']}\n"
        f"Results (first 2000 chars): {result[:2000]}\n\n"
        "Analysis:"
    )
    try:
        state["final_answer"] = llm.invoke([HumanMessage(content=prompt)]).content.strip()
    except Exception:
        state["final_answer"] = "Veriler başarıyla getirildi. Detaylar aşağıda görüntülenebilir."
    return state


def viz_decision_node(state: AgentState) -> AgentState:
    """Decides whether a chart should be generated."""
    result = state.get("query_result", "[]")
    if not result or result == "[]":
        state["needs_viz"] = False
        return state

    try:
        data = json.loads(result)
        if len(data) < 2:
            state["needs_viz"] = False
            return state
    except Exception:
        state["needs_viz"] = False
        return state

    q = state["question"].lower()
    viz_kw = ["chart","graph","trend","distribution","compare","show","visualize",
              "grafik","göster","dağılım","karşılaştır","trend","en çok","top","liste"]
    state["needs_viz"] = any(k in q for k in viz_kw) or len(data) >= 3
    return state


def visualization_node(state: AgentState) -> AgentState:
    """Visualization Agent — generates Plotly JSON for the Angular frontend."""
    result = state.get("query_result", "[]")
    if not result or result == "[]":
        return state

    if USE_MOCK:
        try:
            data     = json.loads(result)
            keys     = list(data[0].keys())
            x_key    = keys[0]
            y_key    = keys[-1] if len(keys) > 1 else keys[0]
            labels   = [str(row.get(x_key, "")) for row in data[:15]]
            values   = [float(row.get(y_key, 0) or 0) for row in data[:15]]
            chart    = {
                "data": [{"x": labels, "y": values, "type": "bar",
                          "marker": {"color": "#8c52ff", "opacity": 0.85}}],
                "layout": {"title": state["question"][:60],
                           "paper_bgcolor": "rgba(0,0,0,0)",
                           "plot_bgcolor":  "rgba(0,0,0,0)",
                           "font": {"family": "Segoe UI, sans-serif"}}
            }
            state["visualization_code"] = json.dumps(chart)
        except Exception as ex:
            logger.warning(f"Mock viz failed: {ex}")
        return state

    prompt = (
        "You are a Plotly.js visualization expert.\n"
        "Create a Plotly chart JSON for the data below.\n\n"
        f"Data: {result[:1500]}\n"
        f"Question: {state['question']}\n\n"
        "Rules:\n"
        "1. Return ONLY valid JSON with 'data' (array) and 'layout' keys\n"
        "2. Choose appropriate chart type (bar, line, pie, scatter)\n"
        "3. Primary color: #8c52ff\n"
        "4. Transparent background: paper_bgcolor and plot_bgcolor = 'rgba(0,0,0,0)'\n"
        "5. No markdown, no code blocks — raw JSON only\n\n"
        "JSON:"
    )
    try:
        raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        raw = raw.replace("```json","").replace("```","").strip()
        json.loads(raw)          # validate
        state["visualization_code"] = raw
    except Exception as ex:
        logger.warning(f"Viz generation failed: {ex}")
        state["visualization_code"] = None
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Routing Functions
# ─────────────────────────────────────────────────────────────────────────────

def route_guardrails(state: AgentState) -> Literal["sql_generator", "__end__"]:
    return "sql_generator" if state["is_in_scope"] and not state.get("is_greeting") else END

def route_executor(state: AgentState) -> Literal["error_handler", "analyzer"]:
    err = state.get("error")
    return "error_handler" if err and err not in ("security_violation",) else "analyzer"

def route_error(state: AgentState) -> Literal["sql_executor", "__end__"]:
    err = state.get("error")
    return END if err in ("max_retries", "fix_failed", "security_violation") else "sql_executor"

def route_viz(state: AgentState) -> Literal["visualizer", "__end__"]:
    return "visualizer" if state.get("needs_viz") else END


# ─────────────────────────────────────────────────────────────────────────────
# Build LangGraph
# ─────────────────────────────────────────────────────────────────────────────

def build_graph():
    wf = StateGraph(AgentState)

    wf.add_node("guardrails",    guardrails_node)
    wf.add_node("sql_generator", sql_generator_node)
    wf.add_node("sql_executor",  sql_executor_node)
    wf.add_node("error_handler", error_handler_node)
    wf.add_node("analyzer",      analysis_node)
    wf.add_node("viz_decision",  viz_decision_node)
    wf.add_node("visualizer",    visualization_node)

    wf.set_entry_point("guardrails")

    wf.add_conditional_edges("guardrails",    route_guardrails,
        {"sql_generator": "sql_generator", END: END})

    wf.add_edge("sql_generator", "sql_executor")

    wf.add_conditional_edges("sql_executor",  route_executor,
        {"error_handler": "error_handler", "analyzer": "analyzer"})

    wf.add_conditional_edges("error_handler", route_error,
        {"sql_executor": "sql_executor", END: END})

    wf.add_edge("analyzer", "viz_decision")

    wf.add_conditional_edges("viz_decision",  route_viz,
        {"visualizer": "visualizer", END: END})

    wf.add_edge("visualizer", END)

    return wf.compile()


# Compile once at startup
agent_graph = build_graph()
logger.info(f"LangGraph compiled — mode: {'MOCK (no OpenAI key)' if USE_MOCK else 'LIVE (OpenAI)'}")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="DataPulse Text2SQL Multi-Agent API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    role:    str          = "INDIVIDUAL"
    user_id: Optional[int] = None


@app.post("/api/chat/ask")
def process_chat(req: ChatRequest):
    initial_state: AgentState = {
        "question":           req.message,
        "role":               req.role,
        "user_id":            req.user_id,
        "is_in_scope":        False,
        "is_greeting":        False,
        "sql_query":          None,
        "query_result":       None,
        "error":              None,
        "error_message":      None,
        "final_answer":       None,
        "needs_viz":          False,
        "visualization_code": None,
        "iteration_count":    0,
    }

    try:
        final = agent_graph.invoke(initial_state)
    except Exception as ex:
        logger.error(f"Graph invocation error: {ex}")
        return {
            "answer":   "AI servisinde beklenmedik bir hata oluştu. Lütfen tekrar deneyin.",
            "sql":      None,
            "plotData": None,
        }

    return {
        "answer":   final.get("final_answer") or "Yanıt üretilemedi.",
        "sql":      final.get("sql_query"),
        "plotData": final.get("visualization_code"),
    }


@app.get("/health")
def health():
    return {"status": "ok", "mode": "mock" if USE_MOCK else "live", "db": engine is not None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
