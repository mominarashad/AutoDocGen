def create_draft_node(state):
    print("🔥 [doc_draft] ENTER")

    pm_data = state.get("pm_data")
    feedback = state.get("user_feedback")

    if feedback:
        print("🔁 Regenerating with feedback")

        draft = f"""
Improved Document:

User Feedback:
{feedback}

Data:
{pm_data}
"""
    else:
        print("🆕 First generation")

        draft = f"""
Initial Document:

{pm_data}
"""

    return {"draft_doc": draft}
