def generate_section_content(heading, conversation, document_type="general", feedback=None):
    """
    Universal LLM prompt for ANY software document type:
    SRS, Test Cases, WBS, Sprint Report, Technical Docs, etc.
    """

    prompt = f"""
You are a senior Software Documentation Expert.

You are writing a professional {document_type.upper()} document.

================ RULES =================
- Do NOT include raw conversation text
- Do NOT mention Slack, Trello, or sources
- Do NOT say "based on"
- Do NOT output JSON, tables, or code
- Write in professional documentation style
- Keep content structured and clear
- Use bullet points only when necessary
- Focus only on documentation content

================ PROJECT CONTEXT =================
{conversation}

================ SECTION =================
{heading}

================ USER FEEDBACK =================
{feedback if feedback else "None"}

================ OUTPUT =================
Write ONLY the final section content.
No heading repetition.
No explanation.
No labels.
"""

    # 🔥 CONNECT YOUR LLM HERE (OpenAI / Gemini / etc.)
    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[{"role": "user", "content": prompt}]
    # )
    # return response.choices[0].message.content

    return f"⚠️ LLM NOT CONNECTED\n\nPROMPT:\n{prompt}"


def create_draft_node(state):
    print("🔥 [doc_draft] ENTER")

    pm_data = state.get("pm_data", {})
    feedback = state.get("user_feedback", "")

    document_type = state.get("template", "General Document")

    selected_headings = state.get("selected_headings", [])
    pdf_headings = state.get("pdf_headings", [])

    selected_headings = selected_headings or pdf_headings or []

    print("📄 Document Type:", document_type)
    print("📌 Selected Headings:", selected_headings)

    conversation = pm_data.get("conversation", "")

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
                document_type=document_type,
                feedback=None
            )

            sections.append(f"""
## {heading}

{content}
""")

        draft = f"""
# {document_type} Document

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
                document_type=document_type,
                feedback=feedback
            )

            sections.append(f"""
## {heading}

{content}
""")

        draft = f"""
# {document_type} Document (Revised)

---

{chr(10).join(sections)}
"""

    print("🔥 [doc_draft] EXIT")

    return {"draft_doc": draft}
