from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from typing import TypedDict, Dict
import os
from pymongo import MongoClient

from app.graph.nodes.pm_agent import fetch_pm_data_node
from app.graph.nodes.doc_draft_node import create_draft_node
from app.graph.nodes.human_review_node import human_review_node
from app.graph.nodes.doc_finalize_node import finalize_doc_node

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
    reviewed_doc: str
    final_doc: str


graph = StateGraph(WorkflowState)

# =====================================================
# 🔥 DEBUG WRAPPERS (FULL TRACE)
# =====================================================

async def debug_pm_agent(state):
    print("\n🔥 [pm_agent] ENTER")
    print("STATE KEYS:", list(state.keys()))
    print("PM DATA:", state.get("pm_data"))

    result = await fetch_pm_data_node(state)

    print("🔥 [pm_agent] EXIT")
    print("RESULT KEYS:", list(result.keys()) if isinstance(result, dict) else result)

    return result


async def debug_doc_draft(state):
    print("\n🔥 [doc_draft] ENTER")
    print("STATE KEYS:", list(state.keys()))
    print("PM DATA:", state.get("pm_data"))

    try:
        result = await create_draft_node(state)   # ✅ FIXED HERE

        print("🔥 [doc_draft] GENERATED DRAFT LENGTH:",
              len(result.get("draft_doc", "")))

        print("🔥 [doc_draft] EXIT")
        return result

    except Exception as e:
        print("\n❌❌❌ DOC_DRAFT CRASH ❌❌❌")
        print("ERROR TYPE:", type(e))
        print("ERROR:", str(e))
        raise


async def debug_human_review(state):
    print("\n🔥 [human_review] ENTER")
    print("DRAFT LENGTH:", len(state.get("draft_doc", "")))

    result = await human_review_node(state)

    print("\n🧠 INTERRUPT TRIGGERED")
    print("RAW RESULT:", result)

    return result


async def debug_finalize(state):
    print("\n🔥 [doc_finalize] ENTER")
    print("REVIEWED DOC:", state.get("reviewed_doc"))

    result = await finalize_doc_node(state)

    print("🔥 [doc_finalize] EXIT")
    print("FINAL LENGTH:", len(result.get("final_doc", "")))

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

print("🔥 GRAPH COMPILED WITH FULL DEBUG MODE")
