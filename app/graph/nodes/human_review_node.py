def human_review_node(state):
    if state.get("reviewed_doc"):
        print("✅ Review already done → skipping interrupt")
        return state

    return {
        "__interrupt__": [{
            "id": "review_1",
            "value": {
                "message": "Review generated document",
                "draft_doc": state.get("final_doc")
            }
        }]
    }
