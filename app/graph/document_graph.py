from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from typing import TypedDict, Dict
import os
from pymongo import MongoClient

from app.graph.nodes.pm_agent import fetch_pm_data_node
from app.graph.nodes.doc_agent import create_docs_node
from app.graph.nodes.human_review_node import human_review_node
from app.graph.nodes.doc_finalize_node import finalize_doc_node

mongo_client = MongoClient(os.getenv("MONGODB_URI"))

checkpointer = MongoDBSaver(
    mongo_client,
    db_name="Doc_Gen",
    collection_name="workflow_checkpoints"
)

class WorkflowState(TypedDict, total=False):
    project_id: str
    user_id: str
    template: str
    pm_data: Dict
    draft_doc: str
    reviewed_doc: str
    final_doc: str


graph = StateGraph(WorkflowState)

# =====================================================
# 🔥 DEBUG WRAPPERS (IMPORTANT)
# =====================================================

async def debug_pm_agent(state):
    print("\n🔥 [DEBUG] ENTER pm_agent")
    print("STATE:", state)
    result = await fetch_pm_data_node(state)
    print("🔥 [DEBUG] EXIT pm_agent")
    return result


async def debug_doc_draft(state):
    print("🔥 ENTER doc_draft")
    print("STATE:", state)

    try:
        result = await create_docs_node(state)
        print("🔥 EXIT doc_draft")
        return result
    except Exception as e:
        print("❌ DOC_DRAFT ERROR:", str(e))
        raise e

async def debug_human_review(state):
    print("\n🔥 [DEBUG] ENTER human_review")
    print("draft_doc length:", len(state.get("draft_doc", "")))

    result = await human_review_node(state)

    print("🔥 [DEBUG] INTERRUPT TRIGGERED")
    print("VALUE:", result)

    return result


async def debug_finalize(state):
    print("\n🔥 [DEBUG] ENTER finalize")
    result = await finalize_doc_node(state)
    print("🔥 [DEBUG] EXIT finalize")
    return result


# =====================================================
# GRAPH BUILD
# =====================================================

graph.add_node("pm_agent", debug_pm_agent)
graph.add_node("doc_draft", debug_doc_draft)
graph.add_node("human_review", debug_human_review)
graph.add_node("doc_finalize", debug_finalize)

graph.add_edge(START, "pm_agent")
graph.add_edge("pm_agent", "doc_draft")
graph.add_edge("doc_draft", "human_review")
graph.add_edge("human_review", "doc_finalize")
graph.add_edge("doc_finalize", END)

workflow = graph.compile(checkpointer=checkpointer)

print("🔥 GRAPH COMPILED WITH DEBUG MODE")
