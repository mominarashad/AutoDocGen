def finalize_doc_node(state):
    print("\n🔥 FINALIZE ENTER")

    draft = state.get("draft_doc", "")
    feedback = state.get("user_feedback")

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

    return {
        "final_doc": final
    }
