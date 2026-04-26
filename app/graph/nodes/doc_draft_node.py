def create_draft_node(state):
    print("🔥 [doc_draft] ENTER")

    pm_data = state.get("pm_data", {})
    feedback = state.get("user_feedback", "")

    # ✅ NEW: TEMPLATE + HEADINGS
    template = state.get("template", "")
    selected_headings = state.get("selected_headings", [])
    pdf_headings = state.get("pdf_headings", [])

    # fallback safety
    selected_headings = selected_headings or pdf_headings or []

    print("📄 Template:", template)
    print("📌 Selected Headings:", selected_headings)

    # =====================================================
    # 🆕 FIRST GENERATION
    # =====================================================
    if not feedback:
        print("🆕 First generation")

        sections = []

        for heading in selected_headings:
            sections.append(f"""
## {heading}

Generated content for **{heading}** based on:
{pm_data}
""")

        draft = f"""
# {template} Document

{chr(10).join(sections)}
"""

    # =====================================================
    # 🔁 REGENERATION (WITH FEEDBACK)
    # =====================================================
    else:
        print("🔁 Regenerating with feedback")

        sections = []

        for heading in selected_headings:
            sections.append(f"""
## {heading}

Improved content for **{heading}**

User Feedback:
{feedback}

Context:
{pm_data}
""")

        draft = f"""
# {template} Document (Revised)

{chr(10).join(sections)}
"""

    print("🔥 [doc_draft] EXIT")

    return {"draft_doc": draft}
