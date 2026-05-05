import re
from langchain_google_genai import ChatGoogleGenerativeAI
from app.langsmith.load_prompt import load_prompt_from_langsmith
from langgraph.config import get_stream_writer

# ==========================================================
# 🧠 DOCUMENT GENERATION (NON-NODE HELPER)
# ==========================================================
async def generate_documentation(
    cleaned_pm_data: str,
    pdf_headings: list,
    selected_headings: list,
    template: str,
    user_feedback: str = ""
):

    prompt = load_prompt_from_langsmith("doc_gen_prompt")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        streaming=True
    )

    chain = prompt | llm

    strict_instruction = """
YOU ARE A STRICT DOCUMENT EDITOR.

RULES:
1. NEVER remove existing content
2. NEVER use placeholders like [To be added], TBD
3. NEVER reorder sections
4. ONLY edit relevant sections
5. PRESERVE structure exactly
6. Overview MUST always contain real content
"""

    feedback_block = ""

    if user_feedback:
        feedback_block = f"""
USER REQUEST:
{user_feedback}

RULES:
- modify only relevant sections
- do NOT rewrite full document
"""

    final_input = f"""
SYSTEM RULES:
{strict_instruction}

{feedback_block}

DOCUMENT:
{cleaned_pm_data}
"""

    full_output = ""

    async for chunk in chain.astream({
        "cleaned_pm_data": final_input,
        "pdf_headings": pdf_headings,
        "selected_headings": selected_headings
    }):
        if chunk and getattr(chunk, "content", None):
            full_output += chunk.content

    return full_output


# ==========================================================
# 🧠 SECTION PARSER
# ==========================================================
def convert_to_sections(text: str):

    pattern = r"(#{1,6}\s.*)"
    parts = re.split(pattern, text)

    sections = {}
    current_heading = "intro"
    buffer = ""

    for part in parts:
        if not part:
            continue

        if part.startswith("#"):
            if buffer:
                sections[current_heading] = buffer.strip()

            current_heading = part.strip()
            buffer = ""
        else:
            buffer += part

    if buffer:
        sections[current_heading] = buffer.strip()

    return sections


# ==========================================================
# 🧠 LANGGRAPH NODE (MAIN)
# ==========================================================
async def create_docs_node(state):
    write = get_stream_writer()  # ← LangGraph's built-in stream writer

    pm_data = state.get("pm_data", {})
    pdf_headings = state.get("pdf_headings", [])
    selected_headings = state.get("selected_headings", [])
    template = state.get("template", "")
    user_feedback = state.get("user_feedback", "")

    if not pm_data:
        return {"draft_doc": "⚠️ No PM data found", "sections": {}}

    cleaned_pm_data = state.get("draft_doc", "") or str(pm_data)

    prompt_template = load_prompt_from_langsmith("doc_gen_prompt")

    # ... build final_input as before ...

    prompt = prompt_template.format(
        cleaned_pm_data=final_input,
        pdf_headings=pdf_headings,
        selected_headings=selected_headings
    )

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", streaming=True)

    full_text = ""

    async for chunk in llm.astream(prompt):
        token = getattr(chunk, "content", "") or ""
        if not token:
            continue
        full_text += token
        write({"token": token})  # ← streams to frontend via custom stream

    sections = convert_to_sections(full_text)
    return {"draft_doc": full_text, "sections": sections}
