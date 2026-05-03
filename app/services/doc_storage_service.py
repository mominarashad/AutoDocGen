from datetime import datetime


async def save_generated_doc(
    db,
    user_id: str,
    project_id: str,
    template_name: str,
    content: str,
    source: str = "trello",
    team_id: str = None,
    is_final: bool = False,
    workspace_name: str = None   
):
    collection = db["generated_docs"]

    # ======================================================
    # 🔢 GET NEXT VERSION
    # ======================================================
    last_doc = await collection.find_one(
        {
            "user_id": user_id,
            "project_id": project_id,
            "template_name": template_name
        },
        sort=[("version", -1)]
    )

    next_version = 1
    if last_doc:
        next_version = last_doc.get("version", 1) + 1

    # ======================================================
    # 💾 SAVE DOCUMENT
    # ======================================================
    await collection.insert_one({
    "user_id": user_id,
    "project_id": project_id,
    "template_name": template_name,
    "generated_docs": content,
    "version": next_version,
    "source": source,
    "team_id": team_id,

    "workspace_name": workspace_name or project_id,

    "created_at": datetime.utcnow()
})

    print(f"✅ Document saved (v{next_version})")

def split_into_sections(doc: str):
    import re

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
