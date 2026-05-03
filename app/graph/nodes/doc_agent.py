import re
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from app.langsmith.load_prompt import load_prompt_from_langsmith


# ==========================================================
# 🧠 LLM DOCUMENT GENERATION (FEEDBACK-BASED EDITING FIXED)
# ==========================================================
def generate_documentation(
    cleaned_pm_data: str,
    pdf_headings: list,
    selected_headings: list,
    template: str,
    user_feedback: str = ""
):

    prompt = load_prompt_from_langsmith("doc_prompt_pdf_selected")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    chain = prompt | llm

    # ======================================================
    # 🔒 STRICT SYSTEM INSTRUCTIONS
    # ======================================================
    strict_instruction = f"""
YOU ARE A STRUCTURED DOCUMENT EDITING ENGINE.

IMPORTANT RULES:
1. Follow ONLY the structure relevant to template: {template}
2. DO NOT randomly change formatting or headings
3. DO NOT merge or rename sections
4. Maintain markdown hierarchy (#, ##, ###)
5. Work like a document editor, not a generator
6. Preserve existing valid content
"""

    # ======================================================
    # 🔥 FEEDBACK + CONTEXT-AWARE EDITING (CORE FIX)
    # ======================================================
    feedback_block = ""

    if user_feedback:
        feedback_block = f"""
YOU ARE EDITING AN EXISTING DOCUMENT.

CURRENT DOCUMENT:
{cleaned_pm_data}

USER FEEDBACK:
{user_feedback}

INSTRUCTION:
- DO NOT rewrite entire document
- ONLY modify relevant sections
- PRESERVE all correct existing content
- APPLY user feedback precisely

RULES:
- "add" → append new content
- "improve" → expand existing section
- "make detailed" → elaborate only affected parts
- "edit section" → modify only that section
"""

    # ======================================================
    # 🧠 FINAL INPUT (IMPORTANT FIX)
    # ======================================================
    final_input = strict_instruction + "\n" + feedback_block

    result = chain.invoke({
        "cleaned_pm_data": final_input,
        "pdf_headings": pdf_headings,
        "selected_headings": selected_headings
    })

    return result.content if hasattr(result, "content") else str(result)


# ==========================================================
# 🧠 SECTION PARSER (FOR STRUCTURED EDITING)
# ==========================================================
def convert_to_sections(text: str):
    """
    Converts markdown document into structured sections
    for section-wise editing (Notion-style AI)
    """

    pattern = r"(#+\s.*)"
    parts = re.split(pattern, text)

    sections = {}
    current_heading = "intro"
    buffer = ""

    for part in parts:
        if part.startswith("#"):
            if buffer:
                sections[current_heading] = buffer.strip()

            current_heading = part.strip()
            buffer = ""
        else:
            buffer += part

    if buffer:
        sections[current_heading] = buffer.strip()

    return sections


# ==========================================================
# 🧠 WORKFLOW NODE (UPDATED)
# ==========================================================
def create_docs_node(state):

    pm_data = state.get("pm_data", {})
    pdf_headings = state.get("pdf_headings", [])
    selected_headings = state.get("selected_headings", [])
    template = state.get("template", "")

    # 🔥 feedback input from state
    user_feedback = state.get("user_feedback", "")

    if not pm_data:
        return {
            "draft_doc": "⚠️ No PM data found",
            "sections": {}
        }

    cleaned_pm_data = str(pm_data)

    # ======================================================
    # 🚀 GENERATE DOCUMENT (EDIT MODE ENABLED)
    # ======================================================
    docs = generate_documentation(
        cleaned_pm_data=cleaned_pm_data,
        pdf_headings=pdf_headings,
        selected_headings=selected_headings,
        template=template,
        user_feedback=user_feedback
    )

    # ======================================================
    # 🧩 STRUCTURE OUTPUT INTO SECTIONS
    # ======================================================
    sections = convert_to_sections(docs)

    return {
        "draft_doc": docs,
        "sections": sections
    }
