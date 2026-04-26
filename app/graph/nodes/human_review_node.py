from langgraph.types import interrupt


def human_review_node(state):
    print("\n🔥 [human_review] ENTER")

    final_doc = state.get("final_doc", "")

    return interrupt({
        "message": "Review document (optional feedback + optional new headings)",
        "final_doc": final_doc
    })
