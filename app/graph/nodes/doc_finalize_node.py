def finalize_doc_node(state):
    print("🔥 [finalize_doc] ENTER")

    draft = state.get("draft_doc")

    if not draft:
        return {"final_doc": "⚠️ No document generated"}

    feedback = state.get("user_feedback", "")

    if feedback:
        final_doc = f"""# FINAL DOCUMENT (IMPROVED)

{draft}

---

## Feedback Applied:
{feedback}
"""
    else:
        final_doc = f"""# FINAL DOCUMENT

{draft}
"""

    return {"final_doc": final_doc}
