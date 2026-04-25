def create_draft_node(state):
    pm_data = state.get("pm_data", {})
    feedback = state.get("reviewed_doc")

    if feedback:
        draft = f"""
        Regenerated Document (based on feedback):
        Feedback:
        {feedback}

        Original Data:
        {pm_data}
        """
    else:
        draft = f"""
        Initial Draft:
        {pm_data}
        """

    return {
        **state,
        "draft_doc": draft
    }
