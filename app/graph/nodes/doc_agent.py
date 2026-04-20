# app/graph/nodes/doc_agent.py

from langchain_google_genai import ChatGoogleGenerativeAI
from app.langsmith.load_prompt import load_prompt_from_langsmith
from tenacity import retry, stop_after_attempt, wait_exponential


# =========================================================
# ✅ GLOBAL LLM (reused across requests — IMPORTANT FIX)
# =========================================================
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",   # more stable than 2.5-flash
    temperature=0.3
)


# =========================================================
# 🔥 RETRY WRAPPER (handles Gemini 503 spikes)
# =========================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def safe_invoke(chain, payload):
    return chain.invoke(payload)


# =========================================================
# 🧠 DOCUMENT GENERATION
# =========================================================
def generate_documentation(
    cleaned_pm_data: str,
    pdf_headings: list,
    selected_headings: list
):
    """
    Generate clean, professional documentation from PM data
    using a prompt fetched from LangSmith Prompt Hub
    """

    prompt = load_prompt_from_langsmith("doc_prompt_pdf_selected")

    chain = prompt | llm

    result = safe_invoke(chain, {
        "cleaned_pm_data": cleaned_pm_data,
        "pdf_headings": pdf_headings,
        "selected_headings": selected_headings,
    })

    return result.content if hasattr(result, "content") else str(result)


# =========================================================
# 🧹 CLEAN + FORMAT PM DATA (Slack + Trello)
# =========================================================
def format_pm_data(pm_data: dict) -> str:
    source = pm_data.get("source")

    # -------------------------
    # 🔵 SLACK FORMAT
    # -------------------------
    if source == "slack":

        conversation = pm_data.get("conversation", "")

        # 🔥 IMPORTANT: limit size to prevent Gemini overload
        conversation = "\n".join(conversation.split("\n")[-30:])

        return f"""
Project Source: Slack

Channel ID: {pm_data.get("channel_id")}
Team ID: {pm_data.get("team_id")}

Conversation:
{conversation}
"""

    # -------------------------
    # 🟢 TRELLO FORMAT
    # -------------------------
    else:
        cards = pm_data.get("cards", [])

        formatted_cards = "\n".join(
            [
                f"- {c.get('name')}: {c.get('desc')}"
                for c in cards
            ]
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
    """
    LangGraph node to generate documentation from pm_data.
    """

    pm_data = state.get("pm_data", {})
    pdf_headings = state.get("pdf_headings", [])
    selected_headings = state.get("selected_headings", [])

    print("\n📝 [create_docs_node] PM data received:")
    print(pm_data)

    # -------------------------
    # ❌ SAFETY CHECK
    # -------------------------
    if not pm_data:
        return {
            "generated_docs": "⚠️ PM data is empty. Please check the input step."
        }

    # -------------------------
    # 🧹 CLEAN INPUT
    # -------------------------
    cleaned_pm_data = format_pm_data(pm_data)

    # -------------------------
    # 🧠 GENERATE DOC
    # -------------------------
    docs = generate_documentation(
        cleaned_pm_data,
        pdf_headings,
        selected_headings
    )

    return {"generated_docs": docs}
