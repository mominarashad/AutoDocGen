from langgraph.types import interrupt

def human_review_node(state):
    """
    HITL pause point (as per official LangGraph HITL pattern)
    """

    draft = state.get("draft_doc", "")

    # 🔴 THIS CREATES THE PAUSE (same as repo)
    return interrupt({
        "draft_doc": draft
    })
