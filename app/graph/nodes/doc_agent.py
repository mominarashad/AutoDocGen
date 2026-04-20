from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from app.langsmith.load_prompt import load_prompt_from_langsmith
from tenacity import retry, stop_after_attempt, wait_exponential
import os

# =========================================================
# 🧠 MODELS (Gemini + Groq Hybrid)
# =========================================================

gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.3,
    api_key=os.getenv("GOOGLE_API_KEY")
)

groq_llm = ChatGroq(
    model="llama3-70b-8192",
    api_key=os.getenv("GROQ_API_KEY")
)

# =========================================================
# 🔥 RETRY WRAPPER (Gemini stability fix)
# =========================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def safe_invoke(chain, payload):
    return chain.invoke(payload)


# =========================================================
# 🧠 SMART LLM ROUTER
# =========================================================
def call_llm(prompt, mode="gemini"):
    """
    mode:
      - gemini → high quality
      - groq → fast/cheap
    """

    try:
        if mode == "groq":
            return groq_llm.invoke(prompt)

        return gemini_llm.invoke(prompt)

    except Exception as e:
        print("⚠️ Primary LLM failed, switching fallback:", e)

        if mode == "gemini":
            return groq_llm.invoke(prompt)

        raise e


# =========================================================
# 🧠 DOCUMENT GENERATION
# =========================================================
def generate_documentation(
    cleaned_pm_data: str,
    pdf_headings: list,
    selected_headings: list
):
    prompt = load_prompt_from_langsmith("doc_prompt_pdf_selected")

    chain_input = {
        "cleaned_pm_data": cleaned_pm_data,
        "pdf_headings": pdf_headings,
        "selected_headings": selected_headings,
    }

    # 🔥 Gemini for high-quality writing
    try:
        result = safe_invoke(
            prompt | gemini_llm,
            chain_input
        )
    except Exception as e:
        print("⚠️ Gemini failed → switching to Groq fallback:", e)

        result = safe_invoke(
            prompt | groq_llm,
            chain_input
        )

    return result.content if hasattr(result, "content") else str(result)


# =========================================================
# 🧹 FORMAT PM DATA
# =========================================================
def format_pm_data(pm_data: dict) -> str:
    source = pm_data.get("source")

    # -------------------------
    # 🔵 SLACK (LIMITED CONTEXT)
    # -------------------------
    if source == "slack":
        conversation = pm_data.get("conversation", "")

        # 🔥 IMPORTANT: prevent token explosion
        lines = conversation.split("\n")[-25:]

        return f"""
Project Source: Slack

Channel ID: {pm_data.get("channel_id")}
Team ID: {pm_data.get("team_id")}

Conversation:
{chr(10).join(lines)}
"""

    # -------------------------
    # 🟢 TRELLO
    # -------------------------
    cards = pm_data.get("cards", [])

    formatted_cards = "\n".join(
        [f"- {c.get('name')}: {c.get('desc')}" for c in cards]
    )

    return f"""
Project Source: Trello

Board ID: {pm_data.get("board_id")}

Tasks:
{formatted_cards}
"""


# =========================================================
# 🚀 LANGGRAPH NODE
# =========================================================
def create_docs_node(state):
    pm_data = state.get("pm_data", {})
    pdf_headings = state.get("pdf_headings", [])
    selected_headings = state.get("selected_headings", [])

    print("\n📝 [create_docs_node] PM data received:", pm_data)

    if not pm_data:
        return {
            "generated_docs": "⚠️ PM data is empty"
        }

    cleaned_pm_data = format_pm_data(pm_data)

    docs = generate_documentation(
        cleaned_pm_data,
        pdf_headings,
        selected_headings
    )

    return {"generated_docs": docs}
