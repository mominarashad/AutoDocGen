def finalize_doc_node(state):
    content = state.get("reviewed_doc") or state.get("draft_doc")

    final = f"""
FINAL DOCUMENT

{content}
""".strip()

    return {
        **state,
        "final_doc": final,
        "generated_docs": final   # 🔥 ADD THIS (CRITICAL FOR DB/UI SYNC)
    }
