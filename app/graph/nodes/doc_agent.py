from langchain_google_genai import ChatGoogleGenerativeAI
from app.langsmith.load_prompt import load_prompt_from_langsmith
import re


# ==========================================================
# 🧠 LLM DOCUMENT GENERATION
# ==========================================================
def generate_documentation(
    cleaned_pm_data: str,
    pdf_headings: list,
    selected_headings: list,
    template: str
):

    prompt = load_prompt_from_langsmith("doc_prompt_pdf_selected")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    chain = prompt | llm

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

    result = chain.invoke({
        "cleaned_pm_data": strict_instruction + "\n\nDATA:\n" + cleaned_pm_data,
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
# 🧠 NODE
# ==========================================================
def create_docs_node(state):

    pm_data = state.get("pm_data", {})
    pdf_headings = state.get("pdf_headings", [])
    selected_headings = state.get("selected_headings", [])
    template = state.get("template", "")

    if not pm_data:
        return {
            "draft_doc": "⚠️ No PM data found",
            "sections": {}
        }

    cleaned_pm_data = str(pm_data)

    # ======================================================
    # GENERATE DOCUMENT
    # ======================================================
    docs = generate_documentation(
        cleaned_pm_data,
        pdf_headings,
        selected_headings,
        template=template
    )

    # ======================================================
    # CONVERT TO STRUCTURED SECTIONS
    # ======================================================
    sections = convert_to_sections(docs)

    return {
        "draft_doc": docs,        # backward compatibility
        "sections": sections      # 🔥 NEW (for smart editing)
    }
