def finalize_doc_node(state):
    return {
        **state,
        "final_doc": state.get("reviewed_doc")
    }
