from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver

from typing import TypedDict, Dict
import os

from app.graph.nodes.pm_agent import fetch_pm_data_node
from app.graph.nodes.doc_agent import create_docs_node
from app.graph.nodes.human_review_node import human_review_node
from app.graph.nodes.doc_finalize_node import finalize_doc_node


# ==================================================
# CHECKPOINTER (repo style)
# ==================================================
checkpointer = MongoDBSaver.from_conn_string(
    os.getenv("MONGODB_URI"),
    db_name="Doc_Gen",
    collection_name="workflow_checkpoints"
)


# ==================================================
# STATE
# ==================================================
class WorkflowState(TypedDict, total=False):
    project_id: str
    user_id: str
    template: str

    pm_data: Dict

    draft_doc: str
    reviewed_doc: str
    final_doc: str


# ==================================================
# GRAPH (STRICT REPO FLOW)
# ==================================================
graph = StateGraph(WorkflowState)

graph.add_node("pm_agent", fetch_pm_data_node)
graph.add_node("doc_draft", create_docs_node)
graph.add_node("human_review", human_review_node)
graph.add_node("doc_finalize", finalize_doc_node)

# linear flow with HITL interrupt
graph.add_edge(START, "pm_agent")
graph.add_edge("pm_agent", "doc_draft")
graph.add_edge("doc_draft", "human_review")
graph.add_edge("human_review", "doc_finalize")
graph.add_edge("doc_finalize", END)

workflow = graph.compile(checkpointer=checkpointer)
