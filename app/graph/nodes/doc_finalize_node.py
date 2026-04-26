from langgraph.types import interrupt

def finalize_doc_node(state):
    print("\n🔥 FINALIZE ENTER")

    draft = state.get("draft_doc", "")
    feedback = state.get("user_feedback")

    # If user already gave feedback → regenerate
    if feedback:
        print("🔁 Regenerating with feedback")

        final = f"""
IMPROVED DOCUMENT

FEEDBACK:
{feedback}

ORIGINAL:
{draft}
"""
    else:
        final = draft

    print("FINAL LENGTH:", len(final))

    # 🚨 PAUSE HERE (ONLY ONCE)
    return interrupt({
        "message": "Review your document",
        "final_doc": final
    })
