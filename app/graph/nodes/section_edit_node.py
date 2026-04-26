from langchain_google_genai import ChatGoogleGenerativeAI


def split_into_sections(doc: str):
    """
    Very simple heading splitter (assumes headings start with # or numbers)
    """
    sections = {}
    current_heading = None
    buffer = []

    for line in doc.split("\n"):
        if line.strip().startswith("#") or line.strip().startswith(tuple(str(i) for i in range(10))):
            if current_heading:
                sections[current_heading] = "\n".join(buffer).strip()
                buffer = []
            current_heading = line.strip()
        else:
            buffer.append(line)

    if current_heading:
        sections[current_heading] = "\n".join(buffer).strip()

    return sections


def rebuild_document(sections: dict):
    doc = []
    for heading, content in sections.items():
        doc.append(heading)
        doc.append(content)
        doc.append("")  # spacing
    return "\n".join(doc)


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

    # 🔥 Step 1: Split doc
    sections = split_into_sections(draft_doc)

    # 🔥 Step 2: Auto-pick section if not provided
    if not target_section:
        # naive match: pick first heading containing keyword
        for heading in sections.keys():
            if any(word.lower() in heading.lower() for word in instruction.split()):
                target_section = heading
                break

    if not target_section or target_section not in sections:
        print("❌ Target section not found")
        return state

    old_content = sections[target_section]

    # 🔥 Step 3: LLM edit
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    prompt = f"""
You are editing ONLY this section.

SECTION TITLE:
{target_section}

CURRENT CONTENT:
{old_content}

USER INSTRUCTION:
{instruction}

STRICT RULES:
- DO NOT modify other sections
- DO NOT change heading
- ONLY improve content inside this section
- KEEP formatting same
"""

    result = llm.invoke(prompt)

    new_content = result.content if hasattr(result, "content") else str(result)

    # 🔥 Step 4: Replace section
    sections[target_section] = new_content.strip()

    # 🔥 Step 5: Rebuild document
    updated_doc = rebuild_document(sections)

    print("✅ Section updated:", target_section)

    return {
        "draft_doc": updated_doc,

        # 🔥 CRITICAL: reset so loop doesn’t repeat infinitely
        "user_feedback": "",
        "new_headings": []
    }
