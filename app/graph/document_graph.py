# app/graph/workflow_graph.py

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict

from app.graph.nodes.pm_agent import fetch_pm_data_node
from app.graph.nodes.doc_agent import create_docs_node
from app.graph.nodes.review_agent import review_document_node
from app.graph.nodes.improve_agent import improve_document_node


class WorkflowState(TypedDict):
    project_id: str
    project_name: str

    user_trello_key: str
    user_trello_token: str

    uploaded_pdf_bytes: bytes
    pdf_headings: List[str]
    selected_headings: List[str]

    pm_data: Dict

    # 👇 ADD THESE
    generated_docs: str          # draft
    review_notes: str            # critique
    improved_docs: str           # final output

    feedback: str                # optional user feedback


graph = StateGraph(WorkflowState)

# -----------------------
# Add nodes
# -----------------------
graph.add_node("pm_agent", fetch_pm_data_node)
graph.add_node("doc_agent", create_docs_node)
graph.add_node("review_agent", review_document_node)
graph.add_node("improve_agent", improve_document_node)

# -----------------------
# Add edges (full pipeline)
# -----------------------
graph.add_edge(START, "pm_agent")
graph.add_edge("pm_agent", "doc_agent")
graph.add_edge("doc_agent", "review_agent")
graph.add_edge("review_agent", "improve_agent")
graph.add_edge("improve_agent", END)

# -----------------------
# Compile graph
# -----------------------
workflow = graph.compile()
