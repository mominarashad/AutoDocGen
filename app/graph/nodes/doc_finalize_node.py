def finalize_doc_node(state):
    print("🔥 [finalize_doc] ENTER")

    draft = state.get("draft_doc", "")
    feedback = state.get("user_feedback", "")

    # ✅ CLEAN FINAL DOC STRUCTURE
    if feedback:
        final = {
            "content": draft,
            "feedback_applied": feedback,
            "status": "improved"
        }
    else:
        final = {
            "content": draft,
            "feedback_applied": None,
            "status": "final"
        }

    print("🔥 [finalize_doc] EXIT")

    return {
        "final_doc": final
    }
