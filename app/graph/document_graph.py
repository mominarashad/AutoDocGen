from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from typing import TypedDict, Dict
import os
from pymongo import MongoClient
from langgraph.types import interrupt
from app.graph.nodes.pm_agent import fetch_pm_data_node
from app.graph.nodes.doc_agent import create_docs_node
from app.graph.nodes.doc_finalize_node import finalize_doc_node
from app.graph.nodes.human_review_node import human_review_node

# =====================================================
# MONGODB CHECKPOINTER
# =====================================================
mongo_client = MongoClient(os.getenv("MONGODB_URI"))

checkpointer = MongoDBSaver(
    mongo_client,
    db_name="Doc_Gen",
    collection_name="workflow_checkpoints"
)


# =====================================================
# STATE
# =====================================================
class WorkflowState(TypedDict, total=False):
    project_id: str
    user_id: str
    template: str

    pm_data: Dict

    draft_doc: str
    final_doc: str

    user_feedback: str
    review_status: str   
    pdf_headings: list        # ✅ ADD
    selected_headings: list   # ✅ ADD

graph = StateGraph(WorkflowState)


# =====================================================
# DEBUG WRAPPERS
# =====================================================

def debug_pm_agent(state):
    print("\n🔥 [pm_agent] ENTER")
    result = fetch_pm_data_node(state)
    print("🔥 [pm_agent] EXIT")
    return result


def debug_doc_draft(state):
    print("\n🔥 [doc_draft] ENTER")

    result = create_draft_node(state)

    print("🔥 [doc_draft] GENERATED LENGTH:", len(result.get("draft_doc", "")))

    print("🔥 [doc_draft] EXIT")
    return result




def debug_finalize(state):
    print("\n🔥 [doc_finalize] ENTER")

    result = finalize_doc_node(state)

    print("🔥 [doc_finalize] FINAL LENGTH:", len(result.get("final_doc", "")))

    return result

# =====================================================
# GRAPH BUILD (CLEAN LINEAR FLOW - NO LOOP)
# =====================================================



graph.add_node("pm_agent", debug_pm_agent)
graph.add_node("doc_draft", create_docs_node)
graph.add_node("doc_finalize", debug_finalize)
graph.add_node("human_review", human_review_node)

graph.add_edge(START, "pm_agent")
graph.add_edge("pm_agent", "doc_draft")
graph.add_edge("doc_draft", "doc_finalize")

graph.add_edge("doc_finalize", END)

# =====================================================
# COMPILE GRAPH
# =====================================================
workflow = graph.compile(checkpointer=checkpointer)

print("🔥 GRAPH COMPILED SUCCESSFULLY (NO LOOP, NO HUMAN NODE)")
