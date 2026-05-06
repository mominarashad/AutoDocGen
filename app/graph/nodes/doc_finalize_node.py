import re

def remove_duplicate_sections(text: str) -> str:
    pattern = r"(#{1,6}\s.*)"
    parts = re.split(pattern, text)

    seen = set()
    result = []
    current_heading = None

    for part in parts:
        if part.startswith("#"):
            heading = part.strip()

            if heading in seen:
                current_heading = None
                continue

            seen.add(heading)
            current_heading = heading
            result.append(part)
        else:
            if current_heading:
                result.append(part)

    return "".join(result)


def finalize_doc_node(state):
    draft = state.get("draft_doc", "")
    if not draft:
        return {"final_doc": "⚠️ No document generated"}

    # ✅ Step 1: Remove old FINAL headers
    draft = re.sub(
        r"#{1,6}\s*FINAL DOCUMENT[^\n]*\n*",
        "",
        draft,
        flags=re.IGNORECASE
    ).strip()

    # ✅ Step 2: REMOVE DUPLICATE SECTIONS (🔥 HERE)
    draft = remove_duplicate_sections(draft)

    feedback = state.get("user_feedback", "")

    if feedback:
        final_doc = f"# FINAL DOCUMENT (IMPROVED)\n\n{draft}\n\n---\n\n## Feedback Applied:\n{feedback}"
    else:
        final_doc = f"# FINAL DOCUMENT\n\n{draft}"

    return {"final_doc": final_doc}
