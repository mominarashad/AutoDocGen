import re
from langchain_google_genai import ChatGoogleGenerativeAI
from app.langsmith.load_prompt import load_prompt_from_langsmith
from langgraph.config import get_stream_writer


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
    write = get_stream_writer()

    pm_data = state.get("pm_data", {})
    pdf_headings = state.get("pdf_headings", [])
    selected_headings = state.get("selected_headings", [])
    template = state.get("template", "")
    user_feedback = state.get("user_feedback", "")

    if not pm_data:
        return {"draft_doc": "⚠️ No PM data found", "sections": {}}

    def deduplicate_text(text: str) -> str:
        paragraphs = re.split(r'\n{2,}', text)
        seen = []
        result = []
        for p in paragraphs:
            normalized = re.sub(r'\s+', ' ', p.strip())
            if normalized and normalized not in seen:
                seen.append(normalized)
                result.append(p.strip())
        return '\n\n'.join(result)

    raw_pm = str(pm_data)
    print("=" * 60)
    print("🔍 [doc_agent] RAW PM DATA LENGTH:", len(raw_pm))
    print("🔍 [doc_agent] RAW PM DATA PREVIEW:\n", raw_pm[:500])
    print("=" * 60)

    cleaned_pm_data = deduplicate_text(raw_pm)

    print("🔍 [doc_agent] CLEANED PM DATA LENGTH:", len(cleaned_pm_data))
    print("🔍 [doc_agent] CLEANED PM DATA PREVIEW:\n", cleaned_pm_data[:500])
    print("=" * 60)

    prompt_template = load_prompt_from_langsmith("doc_gen_prompt")

    strict_instruction = """
YOU ARE A STRICT DOCUMENT EDITOR.
RULES:
1. If a section already exists → UPDATE it, DO NOT duplicate it
2. NEVER create duplicate headings
3. Each heading must appear ONLY ONCE
4. Replace content inside sections instead of appending
5. Keep structure same but overwrite section content when needed
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
SYSTEM:
{strict_instruction}
{feedback_block}
DOCUMENT:
{cleaned_pm_data}
"""

    prompt = prompt_template.format(
        cleaned_pm_data=final_input,
        pdf_headings=pdf_headings,
        selected_headings=selected_headings
    )

    print("🔍 [doc_agent] PROMPT LENGTH:", len(prompt))
    print("🔍 [doc_agent] PROMPT PREVIEW:\n", prompt[:800])
    print("=" * 60)

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", streaming=True)

    full_text = ""

    async for chunk in llm.astream(prompt):
        token = getattr(chunk, "content", "") or ""
        if not token:
            continue
        full_text += token
        write({"token": token})

    print("🔍 [doc_agent] LLM OUTPUT LENGTH:", len(full_text))
    print("🔍 [doc_agent] LLM OUTPUT PREVIEW:\n", full_text[:500])
    print("=" * 60)

    sections = convert_to_sections(full_text)
    return {"draft_doc": full_text, "sections": sections}
