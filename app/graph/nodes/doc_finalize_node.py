import re

def finalize_doc_node(state):
    draft = state.get("draft_doc", "")
    if not draft:
        return {"final_doc": "⚠️ No document generated"}

    # Strip ALL previous FINAL DOCUMENT headers anywhere in the text
    draft = re.sub(r"#{1,6}\s*FINAL DOCUMENT[^\n]*\n*", "", draft, flags=re.IGNORECASE).strip()

    feedback = state.get("user_feedback", "")
    if feedback:
        final_doc = f"# FINAL DOCUMENT (IMPROVED)\n\n{draft}\n\n---\n\n## Feedback Applied:\n{feedback}"
    else:
        final_doc = f"# FINAL DOCUMENT\n\n{draft}"

    return {"final_doc": final_doc}
