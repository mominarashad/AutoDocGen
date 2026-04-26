import re
from langchain_google_genai import ChatGoogleGenerativeAI


# ==========================================================
# 🧩 SPLIT DOCUMENT INTO SECTIONS (FIXED)
# ==========================================================
def split_into_sections(doc: str):
    sections = {}
    current_heading = None
    buffer = []

    for line in doc.split("\n"):
        line_strip = line.strip()

        if re.match(r"^#+\s*\d+(\.\d+)*", line_strip):
            if current_heading:
                sections[current_heading] = "\n".join(buffer).strip()
                buffer = []

            current_heading = line_strip
        else:
            buffer.append(line)

    if current_heading:
        sections[current_heading] = "\n".join(buffer).strip()

    return sections


# ==========================================================
# 🎯 FIND BEST SECTION
# ==========================================================
def find_best_section(sections, instruction):
    instruction = instruction.lower()

    for heading in sections.keys():
        if any(word in heading.lower() for word in instruction.split()):
            return heading

    return None


# ==========================================================
# 🧩 REBUILD DOCUMENT (ORDER SAFE)
# ==========================================================
def rebuild_document(original_doc: str, updated_sections: dict):
    output = []
    current_heading = None

    for line in original_doc.split("\n"):
        line_strip = line.strip()

        if line_strip in updated_sections:
            current_heading = line_strip
            output.append(line_strip)
            output.append(updated_sections[line_strip])
        else:
            if not current_heading:
                output.append(line)

    return "\n".join(output)


# ==========================================================
# ✏️ EDIT SECTION NODE (FINAL FIXED)
# ==========================================================
def edit_section_node(state):
    print("\n🔥 [edit_section] ENTER")

    draft_doc = state.get("draft_doc", "")
    instruction = state.get("user_feedback", "")
    target_section = state.get("target_section")

    if not draft_doc:
        print("❌ No draft_doc found")
        return state

    if not instruction:
        print("⚠️ No feedback → skipping edit")
        return state

    # 🔹 Split document
    sections = split_into_sections(draft_doc)

    # 🔹 Auto-detect section
    if not target_section:
        target_section = find_best_section(sections, instruction)

    if not target_section or target_section not in sections:
        print("❌ Target section not found")
        return state

    old_content = sections[target_section]

    # 🔹 LLM (STRICT MODE)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    prompt = f"""
You are a STRICT document editor.

TASK:
- Modify ONLY the given section

RULES:
1. DO NOT create new sections
2. DO NOT duplicate headings
3. DO NOT modify other sections
4. If instruction says "add", append missing info
5. If instruction says "update/fix", modify content
6. RETURN ONLY section content (NO heading)

SECTION:
{old_content}

USER INSTRUCTION:
{instruction}
"""

    result = llm.invoke(prompt)

    new_content = result.content if hasattr(result, "content") else str(result)

    # 🔹 Update section
    sections[target_section] = new_content.strip()

    # 🔹 Rebuild document safely
    updated_doc = rebuild_document(draft_doc, sections)

    print("✅ Section updated:", target_section)

    return {
        "draft_doc": updated_doc,

        # keep required state
        "pm_data": state.get("pm_data"),
        "pdf_headings": state.get("pdf_headings"),
        "selected_headings": state.get("selected_headings"),

        # clear after use
        "user_feedback": "",
        "new_headings": []
    }
