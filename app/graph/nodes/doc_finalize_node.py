def finalize_doc_node(state):

    sections = state.get("sections", {})

    final_doc = "\n\n".join(
        f"{k}\n{v}" for k, v in sections.items()
    )

    return {
        "final_doc": final_doc,
        "sections": sections
    }
