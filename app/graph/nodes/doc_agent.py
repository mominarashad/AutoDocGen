from langchain_google_genai import ChatGoogleGenerativeAI
from app.langsmith.load_prompt import load_prompt_from_langsmith
import re


# ==========================================================
# 🧠 LLM DOCUMENT GENERATION (UPDATED WITH FEEDBACK SUPPORT)
# ==========================================================
def generate_documentation(
    cleaned_pm_data: str,
    pdf_headings: list,
    selected_headings: list,
    template: str,
    user_feedback: str = ""   # 🔥 NEW
):

    prompt = load_prompt_from_langsmith("doc_prompt_pdf_selected")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    chain = prompt | llm

    # ======================================================
    # 🔒 STRICT SYSTEM INSTRUCTIONS
    # ======================================================
    strict_instruction = f"""
YOU ARE A STRUCTURED DOCUMENT GENERATION ENGINE.

IMPORTANT RULES:
1. Follow ONLY the structure relevant to template: {template}
2. DO NOT randomly change formatting or headings
3. DO NOT merge or rename sections
4. ONLY use provided headings when available
5. If new headings exist, include them exactly as given
6. Maintain consistent markdown hierarchy (#, ##, ###)
7. Keep output clean and structured

DO NOT force irrelevant sections (like SRS sections in WBS).
"""

    # ======================================================
    # 🔥 FEEDBACK INJECTION (CORE FIX)
    # ======================================================
    feedback_block = ""
    if user_feedback:
        feedback_block = f"""

USER FEEDBACK (MUST BE APPLIED):
{user_feedback}

INSTRUCTIONS:
- Apply the feedback strictly
- If feedback refers to a specific section (e.g., 1.3), modify ONLY that section
- If feedback is general, improve the entire document accordingly
- Do NOT ignore feedback
"""

    # ======================================================
    # 🧠 FINAL INPUT TO MODEL
    # ======================================================
    final_input = strict_instruction + feedback_block + "\n\nDATA:\n" + cleaned_pm_data

    result = chain.invoke({
        "cleaned_pm_data": final_input,
        "pdf_headings": pdf_headings,
        "selected_headings": selected_headings
    })

    return result.content if hasattr(result, "content") else str(result)


# ==========================================================
# 🧠 SECTION PARSER (FOR DIFF + EDIT MODE)
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
# 🧠 NODE (UPDATED)
# ==========================================================
def create_docs_node(state):

    pm_data = state.get("pm_data", {})
    pdf_headings = state.get("pdf_headings", [])
    selected_headings = state.get("selected_headings", [])
    template = state.get("template", "")

    # 🔥 NEW: get feedback
    user_feedback = state.get("user_feedback", "")

    if not pm_data:
        return {
            "draft_doc": "⚠️ No PM data found",
            "sections": {}
        }

    cleaned_pm_data = str(pm_data)

    # ======================================================
    # 🚀 GENERATE DOCUMENT (WITH FEEDBACK)
    # ======================================================
    docs = generate_documentation(
        cleaned_pm_data,
        pdf_headings,
        selected_headings,
        template=template,
        user_feedback=user_feedback   # 🔥 PASS FEEDBACK
    )

    # ======================================================
    # 🧩 CONVERT TO STRUCTURED SECTIONS
    # ======================================================
    sections = convert_to_sections(docs)

    return {
        "draft_doc": docs,        # backward compatibility
        "sections": sections      # 🔥 structured editing support
    }
