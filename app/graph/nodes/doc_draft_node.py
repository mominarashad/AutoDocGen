# app/graph/nodes/doc_draft_node.py

def create_draft_node(state):
    pm_data = state.get("pm_data", {})

    draft = f"""
    Project Overview:
    {pm_data}

    (Generated draft — user can edit)
    """

    return {
        **state,
        "draft_doc": draft
    }
