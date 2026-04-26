from langgraph.types import interrupt

def finalize_doc_node(state):
    print("\n🔥 [doc_finalize] ENTER")

    reviewed = state.get("reviewed_doc")
    draft = state.get("draft_doc")

    final = reviewed if reviewed else draft

    print("FINAL LENGTH:", len(final or ""))

    # 🚨 PAUSE HERE (NOT A SEPARATE NODE)
    return interrupt({
        "message": "Do you want to review this document?",
        "final_doc": final
    })
