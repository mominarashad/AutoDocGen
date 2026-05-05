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
    # ❗ STEP 1: REMOVE OLD "LATEST"
    # ======================================================
    await collection.update_many(
        {
            "user_id": user_id,
            "project_id": project_id,
            "template_name": template_name
        },
        {"$set": {"is_latest": False}}
    )

    # ======================================================
    # 💾 STEP 2: INSERT NEW DOCUMENT AS LATEST
    # ======================================================
    await collection.insert_one({
        "user_id": user_id,
        "project_id": project_id,
        "template_name": template_name,
        "generated_docs": content,
        "version": next_version,
        "source": source,
        "team_id": team_id,
        "workspace_name": workspace_name if workspace_name else "Unknown Project",
        "created_at": datetime.utcnow(),

        # 🔥🔥🔥 CRITICAL FIELD
        "is_latest": True
    })

    print(f"✅ Document saved (v{next_version}) as latest")

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
