from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')

async def review_document_node(state):
    draft = state.get("generated_docs", "")

    prompt = f"""
You are a senior project manager.

Review the following document and identify:
- Missing details
- Weak explanations
- Poor structure
- Ambiguities

Document:
{draft}

Return a structured critique.
"""

    result = await llm.ainvoke(prompt)

    return {
        "review_notes": result.content
    }
