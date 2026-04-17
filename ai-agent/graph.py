"""
graph.py — LangGraph StateGraph wiring for the Text2SQL multi-agent pipeline.

Workflow:
  User Query
    → guardrails_node          (① Guardrails Agent)
        ├─ out-of-scope / greeting → END (final_answer already set)
        └─ in-scope →
    → sql_generator_node       (② SQL Agent)
    → sql_executor_node        (direct DB call — Spring Boot or SQLAlchemy)
        ├─ error → error_handler_node  (③ Error Agent, max 3 retries)
        │              └─ retry → sql_executor_node
        └─ success →
    → analysis_node            (④ Analysis Agent)
    → viz_decision_node        (row-count gate)
        ├─ no chart needed → END
        └─ chart needed →
    → visualization_node       (⑤ Visualization Agent)
    → END
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, StateGraph

from agents import (
    analysis_node,
    error_handler_node,
    guardrails_node,
    sql_executor_node,
    sql_generator_node,
    viz_decision_node,
    visualization_node,
)
from state import AgentState


# ──────────────────────────────────────────────────────────────────────────────
# Routing functions
# ──────────────────────────────────────────────────────────────────────────────

def route_guardrails(state: AgentState) -> Literal["sql_generator", "__end__"]:
    if state.get("is_in_scope") and not state.get("is_greeting"):
        return "sql_generator"
    return END


def route_executor(state: AgentState) -> Literal["error_handler", "analyzer", "__end__"]:
    err = state.get("error")
    if err == "security_violation":
        return END   # final_answer already set — skip analyzer
    if err and err not in {"db_unavailable", None}:
        return "error_handler"
    return "analyzer"


def route_error(state: AgentState) -> Literal["sql_executor", "__end__"]:
    terminal = {"max_retries", "fix_failed", "security_violation", "db_unavailable"}
    if state.get("error") in terminal:
        return END
    return "sql_executor"


def route_viz(state: AgentState) -> Literal["visualizer", "__end__"]:
    return "visualizer" if state.get("needs_viz") else END


# ──────────────────────────────────────────────────────────────────────────────
# Graph builder
# ──────────────────────────────────────────────────────────────────────────────

def build_graph():
    wf = StateGraph(AgentState)

    # Register nodes
    wf.add_node("guardrails",    guardrails_node)
    wf.add_node("sql_generator", sql_generator_node)
    wf.add_node("sql_executor",  sql_executor_node)
    wf.add_node("error_handler", error_handler_node)
    wf.add_node("analyzer",      analysis_node)
    wf.add_node("viz_decision",  viz_decision_node)
    wf.add_node("visualizer",    visualization_node)

    # Entry point
    wf.set_entry_point("guardrails")

    # Edges
    wf.add_conditional_edges(
        "guardrails",
        route_guardrails,
        {"sql_generator": "sql_generator", END: END},
    )
    wf.add_edge("sql_generator", "sql_executor")
    wf.add_conditional_edges(
        "sql_executor",
        route_executor,
        {"error_handler": "error_handler", "analyzer": "analyzer", END: END},
    )
    wf.add_conditional_edges(
        "error_handler",
        route_error,
        {"sql_executor": "sql_executor", END: END},
    )
    wf.add_edge("analyzer", "viz_decision")
    wf.add_conditional_edges(
        "viz_decision",
        route_viz,
        {"visualizer": "visualizer", END: END},
    )
    wf.add_edge("visualizer", END)

    return wf.compile()


# Singleton — imported by app.py
agent_graph = build_graph()
