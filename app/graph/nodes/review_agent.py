from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')

async def review_document_node(state):
    draft = state.get("generated_docs", "")

    prompt = f"""
You are a senior project manager.

Critically review the document.

Return structured feedback in JSON:

{{
  "missing_sections": [],
  "improvements": [],
  "clarity_issues": [],
  "overall_score": "1-10"
}}

Document:
{draft}
"""

    result = await llm.ainvoke(prompt)

    return {
        "review_notes": result.content
    }
