from langchain_google_genai import ChatGoogleGenerativeAI
from app.langsmith.load_prompt import load_prompt_from_langsmith  


# ==========================================================
# 🧠 DOCUMENT GENERATION CORE
# ==========================================================
def generate_documentation(cleaned_pm_data: str, pdf_headings: list, selected_headings: list):
    """
    Generate clean, professional documentation from PM data
    using LangSmith prompt + Gemini model
    """

    prompt = load_prompt_from_langsmith("doc_prompt_pdf_selected")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    chain = prompt | llm

    result = chain.invoke({
        "cleaned_pm_data": cleaned_pm_data,
        "pdf_headings": pdf_headings,
        "selected_headings": selected_headings
    })

    return result.content if hasattr(result, "content") else str(result)


# ==========================================================
# 🚀 LANGGRAPH NODE (FIXED STATE CONTRACT)
# ==========================================================
def create_docs_node(state):
    """
    Generates draft documentation and stores it in correct state key.
    """

    pm_data = state.get("pm_data", {})
    pdf_headings = state.get("pdf_headings", [])
    selected_headings = state.get("selected_headings", [])

    print("\n📝 [create_docs_node] PM data received:")
    print(pm_data)

    if not pm_data:
        return {
            "draft_doc": "⚠️ PM data is empty. Please check Trello/Slack fetch step."
        }

    cleaned_pm_data = str(pm_data)

    docs = generate_documentation(
        cleaned_pm_data,
        pdf_headings,
        selected_headings
    )

    # ======================================================
    # 🔴 IMPORTANT FIX: MATCH NEXT NODE EXPECTATIONS
    # ======================================================
    return {
        "draft_doc": docs
    }
