"""LangGraph StateGraph construction and compilation for Mira's workflow."""
from langgraph.graph import END, START, StateGraph

from .compose import compose
from .interpret import interpret
from .logging_utils import log_node_errors
from .persistence import save
from .quote import quote_node
from .retrieve import retrieve
from .routing import post_interpret_route, quote_route
from .state import GraphState

builder = StateGraph(GraphState)
for name, fn in [("interpret", interpret), ("retrieve", retrieve), ("quote", quote_node),
                 ("compose", compose), ("save", save)]:
    builder.add_node(name, fn if name == "save" else log_node_errors(fn))
builder.add_edge(START, "interpret")
builder.add_conditional_edges("interpret", post_interpret_route, {"save": "save", "retrieve": "retrieve"})
builder.add_conditional_edges("retrieve", quote_route, {"quote": "quote", "compose": "compose"})
builder.add_edge("quote", "compose")
builder.add_edge("compose", "save")
builder.add_edge("save", END)
graph = builder.compile()
