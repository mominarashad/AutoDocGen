# app/graph/nodes/doc_finalize_node.py

def finalize_doc_node(state):
    content = state.get("reviewed_doc") or state.get("draft_doc")

    final = f"""
    FINAL DOCUMENT

    {content}
    """

    return {
        **state,
        "final_doc": final
    }
