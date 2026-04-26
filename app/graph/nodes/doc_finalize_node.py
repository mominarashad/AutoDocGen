def finalize_doc_node(state):
    draft = state.get("draft_doc", "")
    feedback = state.get("user_feedback")

    if feedback:
        final = f"IMPROVED...\n{feedback}\n{draft}"
    else:
        final = draft

    return {"final_doc": final}
