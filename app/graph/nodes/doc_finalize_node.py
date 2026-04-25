def finalize_doc_node(state):
    content = state.get("reviewed_doc") or state.get("draft_doc")

    return {
        **state,
        "final_doc": content
    }
