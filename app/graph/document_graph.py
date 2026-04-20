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

    generated_docs: str
    review_notes: str
    improved_docs: str

    feedback: str   # 👈 user input


graph = StateGraph(WorkflowState)

# -----------------------
# Nodes
# -----------------------
graph.add_node("pm_agent", fetch_pm_data_node)
graph.add_node("doc_agent", create_docs_node)
graph.add_node("review_agent", review_document_node)
graph.add_node("improve_agent", improve_document_node)

# -----------------------
# Base flow
# -----------------------
graph.add_edge(START, "pm_agent")
graph.add_edge("pm_agent", "doc_agent")


# -----------------------
# 🔥 CONDITIONAL LOGIC
# -----------------------

def should_review(state: WorkflowState):
    feedback = state.get("feedback")
    return bool(feedback and feedback.strip())


# If feedback exists → go review → improve
graph.add_conditional_edges(
    "doc_agent",
    should_review,
    {
        True: "review_agent",
        False: END
    }
)

# review → improve
graph.add_edge("review_agent", "improve_agent")

# improve → END
graph.add_edge("improve_agent", END)

# -----------------------
# Compile
# -----------------------
workflow = graph.compile()
