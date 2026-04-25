# app/graph/workflow_graph.py

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Dict

from app.graph.nodes.pm_agent import fetch_pm_data_node
from app.graph.nodes.doc_draft_node import create_draft_node
from app.graph.nodes.human_review_node import human_review_node
from app.graph.nodes.doc_finalize_node import finalize_doc_node

from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
import os


# ==========================================================
# 🧠 MONGODB PERSISTENT CHECKPOINTER (FIXED)
# ==========================================================
MONGO_URI = os.getenv("MONGODB_URI")

if not MONGO_URI:
    raise RuntimeError("MONGODB_URI not set")

mongo_client = MongoClient(MONGO_URI)  # ✅ SYNC CLIENT (required by LangGraph)

checkpointer = MongoDBSaver(
    mongo_client,
    db_name="Doc_Gen",
    collection_name="workflow_checkpoints"
)


# ==========================================================
# 🧠 WORKFLOW STATE
# ==========================================================
class WorkflowState(TypedDict, total=False):
    project_id: str

    user_trello_key: str
    user_trello_token: str

    pm_data: Dict

    draft_doc: str
    reviewed_doc: str
    final_doc: str

    generated_docs: str  # ✅ IMPORTANT: used for DB + frontend sync


# ==========================================================
# 🧠 BUILD GRAPH
# ==========================================================
graph = StateGraph(WorkflowState)

# ---------------- Nodes ----------------
graph.add_node("pm_agent", fetch_pm_data_node)
graph.add_node("doc_draft", create_draft_node)
graph.add_node("human_review", human_review_node)
graph.add_node("doc_finalize", finalize_doc_node)

# ---------------- Flow ----------------
graph.add_edge(START, "pm_agent")
graph.add_edge("pm_agent", "doc_draft")
graph.add_edge("doc_draft", "human_review")
graph.add_edge("human_review", "doc_finalize")
graph.add_edge("doc_finalize", END)


# ==========================================================
# 🚀 COMPILED WORKFLOW (PERSISTENT)
# ==========================================================
workflow = graph.compile(checkpointer=checkpointer)
