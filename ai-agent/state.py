"""
AgentState — LangGraph TypedDict state contract for the Text2SQL multi-agent pipeline.
"""

from typing import TypedDict, Optional


class AgentState(TypedDict):
    # ── Input ──────────────────────────────────────────────────────────────────
    question: str
    role: str                      # INDIVIDUAL | CORPORATE | ADMIN
    user_id: Optional[int]         # set when role == INDIVIDUAL
    store_id: Optional[int]        # set when role == CORPORATE

    # ── Guardrails ─────────────────────────────────────────────────────────────
    is_in_scope: bool
    is_greeting: bool

    # ── SQL pipeline ───────────────────────────────────────────────────────────
    sql_query: Optional[str]
    query_result: Optional[str]    # JSON string of rows returned from DB
    error: Optional[str]           # error type slug  (e.g. "sql_error")
    error_message: Optional[str]   # human-readable error detail

    # ── Output ─────────────────────────────────────────────────────────────────
    final_answer: Optional[str]
    visualization_code: Optional[str]   # Plotly JSON string or None
    needs_viz: bool

    # ── Routing helpers ────────────────────────────────────────────────────────
    iteration_count: int           # retry counter for Error Agent (max 3)
    intent: Optional[str]          # detected intent label (e.g. "top_products")
