from langgraph.types import interrupt

def human_review_node(state):

    if state.get("reviewed_doc"):
        return state

    reviewed = interrupt({
        "type": "review_document",
        "message": "Edit or approve the generated document",
        "draft": state.get("draft_doc", "")
    })

    return {
        **state,
        "reviewed_doc": reviewed
    }
