from langchain_google_genai import ChatGoogleGenerativeAI
from app.langsmith.load_prompt import load_prompt_from_langsmith  


# ==========================================================
# 🧠 DOCUMENT GENERATION CORE
# ==========================================================
def create_docs_node(state):
    print("🔥 [doc_draft] ENTER")

    pm_data = state.get("pm_data", {})
    pdf_headings = state.get("pdf_headings", [])
    selected_headings = state.get("selected_headings", [])
    feedback = state.get("user_feedback", "")

    if not pm_data:
        return {
            "draft_doc": "⚠️ PM data is empty. Please check source step."
        }

    # ======================================================
    # 🧠 ALWAYS BASE HEADINGS (source of truth)
    # ======================================================
    effective_headings = selected_headings or pdf_headings

    # ======================================================
    # ➕ OPTIONAL: user added new headings
    # ======================================================
    new_headings = state.get("new_headings", [])
    if new_headings:
        effective_headings = effective_headings + new_headings

    # ======================================================
    # 🧠 FEEDBACK HANDLING (OPTIONAL ENRICHMENT ONLY)
    # ======================================================
    cleaned_pm_data = str(pm_data)

    if feedback:
        cleaned_pm_data += f"\n\nUSER FEEDBACK:\n{feedback}"

    docs = generate_documentation(
        cleaned_pm_data,
        pdf_headings,
        effective_headings
    )

    return {
        "draft_doc": docs
    }
