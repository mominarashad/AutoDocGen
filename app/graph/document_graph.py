# app/graph/workflow_graph.py
from langgraph.graph import StateGraph, START, END
from app.graph.nodes.pm_agent import fetch_pm_data_node
from app.graph.nodes.doc_agent import create_docs_node  # import doc node
from typing import TypedDict, List, Dict
from app.graph.nodes.doc_draft_node import create_draft_node
from app.graph.nodes.human_review_node import human_review_node
from app.graph.nodes.doc_finalize_node import finalize_doc_node
from langgraph.checkpoint.memory import MemorySaver

class WorkflowState(TypedDict, total=False):
    project_id: str
    user_trello_key: str
    user_trello_token: str

    pm_data: Dict

    draft_doc: str              # AI generated draft
    reviewed_doc: str           # human edited version
    final_doc: str              # final output


graph = StateGraph(WorkflowState)
checkpointer = MemorySaver()
# Add nodes
graph.add_node("pm_agent", fetch_pm_data_node)
graph.add_node("doc_draft", create_draft_node)
graph.add_node("human_review", human_review_node)
graph.add_node("doc_finalize", finalize_doc_node)

graph.add_edge(START, "pm_agent")
graph.add_edge("pm_agent", "doc_draft")
graph.add_edge("doc_draft", "human_review")
graph.add_edge("human_review", "doc_finalize")
graph.add_edge("doc_finalize", END)

workflow = graph.compile(checkpointer=checkpointer)
