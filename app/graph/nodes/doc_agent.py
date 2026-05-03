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

    strict_instruction = f"""
YOU ARE A STRICT DOCUMENT EDITOR.

RULES:
1. NEVER remove existing content
2. NEVER use placeholders like [To be added], TBD
3. NEVER reorder sections
4. ONLY edit relevant sections
5. PRESERVE structure exactly
6. Overview MUST always contain real content
"""

    feedback_block = ""

    if user_feedback:
        feedback_block = f"""
USER REQUEST:
{user_feedback}

RULES:
- modify only relevant sections
- do NOT rewrite full document
"""

    # 🔥 FIXED CONTEXT HANDLING
    final_input = f"""
SYSTEM RULES:
{strict_instruction}

{feedback_block}

DOCUMENT:
{cleaned_pm_data}
"""

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

    pattern = r"(#{1,6}\s.*)"

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

    user_feedback = state.get("user_feedback", "")

    if not pm_data:
        return {
            "draft_doc": "⚠️ No PM data found",
            "sections": {}
        }

    # 🔥 FIXED: use actual document if exists
    cleaned_pm_data = state.get("draft_doc", "") or str(pm_data)

    docs = generate_documentation(
        cleaned_pm_data=cleaned_pm_data,
        pdf_headings=pdf_headings,
        selected_headings=selected_headings,
        template=template,
        user_feedback=user_feedback
    )

    sections = convert_to_sections(docs)

    return {
        "draft_doc": docs,
        "sections": sections
    }
