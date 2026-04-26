def create_draft_node(state):
    print("🔥 [doc_draft] ENTER")

    pm_data = state.get("pm_data", {})
    feedback = state.get("user_feedback", "")

    template = state.get("template", "")
    selected_headings = state.get("selected_headings", [])
    pdf_headings = state.get("pdf_headings", [])

    selected_headings = selected_headings or pdf_headings or []

    print("📄 Template:", template)
    print("📌 Selected Headings:", selected_headings)

    conversation = pm_data.get("conversation", "")

    # =====================================================
    # 🧠 SIMPLE PROJECT NAME EXTRACTION
    # =====================================================
    project_name = "Software Project"
    if "University Management System" in conversation:
        project_name = "University Management System"

    sections = []

    # =====================================================
    # 🆕 FIRST GENERATION
    # =====================================================
    if not feedback:
        print("🆕 First generation")

        for heading in selected_headings:

            content = generate_section_content(
                heading=heading,
                conversation=conversation,
                feedback=None
            )

            sections.append(f"""
## {heading}

{content}
""")

        draft = f"""
# Software Requirements Specification (SRS)

## Project: {project_name}

---

{chr(10).join(sections)}
"""

    # =====================================================
    # 🔁 REGENERATION
    # =====================================================
    else:
        print("🔁 Regenerating with feedback")

        for heading in selected_headings:

            content = generate_section_content(
                heading=heading,
                conversation=conversation,
                feedback=feedback
            )

            sections.append(f"""
## {heading}

{content}
""")

        draft = f"""
# Software Requirements Specification (SRS)

## Project: {project_name}

---

{chr(10).join(sections)}
"""

    print("🔥 [doc_draft] EXIT")

    return {"draft_doc": draft}
