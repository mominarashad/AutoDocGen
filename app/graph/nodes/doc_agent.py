# app/graph/nodes/doc_agent.py

from langchain_google_genai import ChatGoogleGenerativeAI
from app.langsmith.load_prompt import load_prompt_from_langsmith  


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
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    chain = prompt | llm

    # Pass all variables expected by your LangSmith prompt
    result = chain.invoke(
        {
            "cleaned_pm_data": cleaned_pm_data,
            "pdf_headings": pdf_headings,
            "selected_headings": selected_headings,
        }
    )

    return result.content if hasattr(result, "content") else str(result)


def format_pm_data(pm_data: dict) -> str:
    if pm_data.get("source") == "slack":
        return f"""
Project Source: Slack

Channel ID: {pm_data.get("channel_id")}
Team ID: {pm_data.get("team_id")}

Conversation:
{pm_data.get("conversation")}
"""
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


def create_docs_node(state):
    """
    LangGraph node to generate documentation from pm_data.
    """
    pm_data = state.get("pm_data", {})
    pdf_headings = state.get("pdf_headings", [])
    selected_headings = state.get("selected_headings", [])

    print("\n📝 [create_docs_node] PM data received:")
    print(pm_data)

    if not pm_data:
        return {
            "generated_docs": "⚠️ PM data is empty. Please check the Trello fetch step."
        }

    # Convert pm_data dict to cleaned string (or real cleaning logic later)
    cleaned_pm_data = format_pm_data(pm_data)

    docs = generate_documentation(
        cleaned_pm_data,
        pdf_headings,
        selected_headings
    )

    return {"generated_docs": docs}
