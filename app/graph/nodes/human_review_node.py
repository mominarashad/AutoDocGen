from langgraph.types import interrupt

async def human_review_node(state):
    return interrupt({
        "draft_doc": state.get("draft_doc"),
        "message": "Edit the document and submit"
    })
