from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')

async def improve_document_node(state):
    draft = state.get("generated_docs", "")
    review = state.get("review_notes", "")

    prompt = f"""
You are an expert technical writer.

Rewrite the document using the review feedback.

RULES:
- Make it professional
- Add missing sections
- Fix clarity issues
- Improve structure
- Use proper headings

Original Document:
{draft}

Review Feedback:
{review}

Return FINAL polished document.
"""

    result = await llm.ainvoke(prompt)

    return {
        "improved_docs": result.content
    }
