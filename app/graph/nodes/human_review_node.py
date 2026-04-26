from langgraph.types import interrupt

def human_review_node(state):
    print("\n🔥 [human_review] ENTER")

    final_doc = state.get("final_doc", "")

    result = interrupt({
        "message": "Review document. You may optionally send feedback or new headings.",
        "final_doc": final_doc
    })

    return {
        "user_feedback": result.get("user_feedback", "") or "",
        "new_headings": result.get("new_headings", []) or [],
        "pdf_headings": state.get("pdf_headings", []),
        "selected_headings": (
            state.get("selected_headings", []) +
            result.get("new_headings", [])
        )
    }
