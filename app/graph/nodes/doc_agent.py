from langchain_google_genai import ChatGoogleGenerativeAI
from app.langsmith.load_prompt import load_prompt_from_langsmith


# ==========================================================
# 🧠 LLM DOCUMENT GENERATION
# ==========================================================
def generate_documentation(cleaned_pm_data: str, pdf_headings: list, selected_headings: list):

    prompt = load_prompt_from_langsmith("doc_prompt_pdf_selected")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    chain = prompt | llm

    strict_instruction = """
YOU ARE A STRICT DOCUMENT FORMATTING ENGINE.

RULES (VERY IMPORTANT):
1. DO NOT change headings order
2. DO NOT remove any selected headings
3. DO NOT merge or rename sections
4. ONLY ADD content under provided headings
5. If user adds new headings, include them EXACTLY as provided
6. If no new headings are provided, use only selected_headings
7. Maintain same structure as input document
8. DO NOT rewrite document format or restructure content

OUTPUT MUST FOLLOW EXACTLY THE GIVEN HEADING STRUCTURE.
"""

    result = chain.invoke({
        "cleaned_pm_data": strict_instruction + "\n\nDATA:\n" + cleaned_pm_data,
        "pdf_headings": pdf_headings,
        "selected_headings": selected_headings
    })

    return result.content if hasattr(result, "content") else str(result)


# ==========================================================
# 🧠 NODE
# ==========================================================
def create_docs_node(state):

    pm_data = state.get("pm_data", {})
    pdf_headings = state.get("pdf_headings", [])
    selected_headings = state.get("selected_headings", [])

    if not pm_data:
        return {
            "draft_doc": "⚠️ No PM data found"
        }

    cleaned_pm_data = str(pm_data)

    docs = generate_documentation(
        cleaned_pm_data,
        pdf_headings,
        selected_headings
    )

    return {
        "draft_doc": docs
    }
