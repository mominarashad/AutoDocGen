def finalize_doc_node(state):
    print("\n🔥 [doc_finalize] ENTER")

    reviewed = state.get("reviewed_doc")
    draft = state.get("draft_doc")

    final = reviewed if reviewed else draft

    print("FINAL LENGTH:", len(final or ""))

    return {"final_doc": final}
