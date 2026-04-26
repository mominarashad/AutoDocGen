from langchain_google_genai import ChatGoogleGenerativeAI

def edit_section_node(state):

    sections = state.get("sections", {})
    target_section = state.get("target_section")   # e.g. "1. Introduction"
    instruction = state.get("user_feedback", "")

    if not target_section or target_section not in sections:
        return state

    old_content = sections[target_section]

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    prompt = f"""
You are editing ONLY this section.

SECTION TITLE:
{target_section}

CURRENT CONTENT:
{old_content}

USER INSTRUCTION:
{instruction}

RULES:
- DO NOT change other sections
- ONLY rewrite this section
- Keep formatting consistent
"""

    result = llm.invoke(prompt)

    sections[target_section] = result.content if hasattr(result, "content") else str(result)

    return {
        "sections": sections
    }
