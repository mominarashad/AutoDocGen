from langgraph.types import interrupt

def finalize_doc_node(state):
    print("\n🔥 FINALIZE ENTER")

    draft = state.get("draft_doc", "")
    feedback = state.get("user_feedback")

    if feedback:
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

    # IMPORTANT: return dict wrapper
    return {
        "__interrupt__": interrupt({
            "message": "Review your document",
            "final_doc": final
        })
    }
