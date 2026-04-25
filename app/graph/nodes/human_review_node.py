from langgraph.types import interrupt

def human_review_node(state):
    draft = state.get("draft_doc", "")

    user_feedback = interrupt({
        "draft": draft,
        "message": "Review and edit the document"
    })

    return {
        **state,
        "reviewed_doc": user_feedback
    }
