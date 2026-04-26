def finalize_doc_node(state):
    print("🔥 [finalize_doc] ENTER")

    draft = state.get("draft_doc")

    if not draft:
        print("❌ No draft_doc found in state")
        return {
            "final_doc": "⚠️ Error: No document generated"
        }

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

    print("🔥 [finalize_doc] FINAL LENGTH:", len(final_doc))
    print("🔥 [finalize_doc] EXIT")

    return {
        "final_doc": final_doc
    }
