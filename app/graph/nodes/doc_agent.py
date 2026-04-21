from app.services.llm_router import call_llm
from app.langsmith.load_prompt import load_prompt_from_langsmith

# =========================================================
# 🧠 DOCUMENT GENERATION
# =========================================================
def generate_documentation(cleaned_pm_data, pdf_headings, selected_headings):
    prompt_template = load_prompt_from_langsmith("doc_prompt_pdf_selected")

    prompt = prompt_template.format(
        cleaned_pm_data=cleaned_pm_data,
        pdf_headings=pdf_headings,
        selected_headings=selected_headings,
    )

    result = call_llm(prompt, mode="gemini")

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
