from langgraph.types import interrupt

def human_review_node(state):
    print("\n🔥 [human_review] ENTER")

    final_doc = state.get("final_doc", "")

    result = interrupt({
        "message": "Review document (optional feedback + optional new headings)",
        "final_doc": final_doc
    })

    # ======================================================
    # SAFE EXTRACTION (USER MAY SEND NOTHING)
    # ======================================================
    return {
        "user_feedback": result.get("user_feedback", "") or "",
        "new_headings": result.get("new_headings", []) or []
    }
