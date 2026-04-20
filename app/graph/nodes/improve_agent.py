from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')

async def improve_document_node(state):
    draft = state.get("generated_docs", "")
    review = state.get("review_notes", "")

    prompt = f"""
You are an expert technical writer.

Improve the document using the review feedback.

Original Document:
{draft}

Review Feedback:
{review}

Return a FINAL polished, structured, professional document.
Use proper headings, sections, clarity, and completeness.
"""

    result = await llm.ainvoke(prompt)

    return {
        "generated_docs": result.content
    }
