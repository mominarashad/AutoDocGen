from app.graph.document_graph import workflow, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
from app.services.trello_service import get_board_name
from app.services.cleaner import clean_generated_doc
from app.services.slack_service import fetch_channel_messages, join_channel
from datetime import datetime
import re
import os


async def execute_workflow(user_id: str, project_id: str, data: dict = None, db=None):

    if db is None:
        raise RuntimeError("Database instance not provided")

    docs_collection = db["generated_docs"]

    # ==========================================================
    # INPUT SAFE PARSING
    # ==========================================================
    data = data or {}

    pdf_headings = data.get("pdf_headings", [])
    selected_headings = data.get("selected_headings", [])
    template_name = str(data.get("template", "")).strip()
    source = data.get("source") or "trello"

    if not template_name:
        return {"status": "error", "message": "Missing template name"}

    print("🔥 execute_workflow")
    print("user_id:", user_id)
    print("project_id:", project_id)
    print("template_name:", template_name)
    print("source:", source)

    pm_data = {}
    board_name = ""
    trello_token = None

    # ==========================================================
    # 🔵 SLACK FLOW
    # ==========================================================
    if source == "slack":
        print("✅ Slack flow triggered")

        team_id = data.get("team_id")

        if not team_id:
            return {
                "status": "error",
                "message": "team_id required for Slack"
            }

        # 🔑 GET SLACK TOKEN FROM DB
        slack_token = await get_slack_token(user_id, team_id, db)

        print("TOKEN EXISTS:", bool(slack_token))

        if not slack_token:
            return {
                "status": "error",
                "message": "Slack workspace not connected"
            }

        # 🚀 JOIN CHANNEL
        join_res = await join_channel(slack_token, project_id)
        print("🧪 JOIN RESPONSE:", join_res)

        # 📥 FETCH MESSAGES
        messages_res = await fetch_channel_messages(slack_token, project_id)
        print("🧪 FETCH RESPONSE:", messages_res)

        if not messages_res.get("ok"):
            return {
                "status": "error",
                "message": "Failed to fetch Slack messages",
                "details": messages_res
            }

        messages = messages_res.get("messages", [])

        print(f"🔥 Fetched {len(messages)} Slack messages")

        conversation = "\n".join(
            f"{m.get('user', 'unknown')}: {m.get('text', '')}"
            for m in messages if m.get("text")
        )

        pm_data = {
            "source": "slack",
            "team_id": team_id,
            "channel_id": project_id,
            "conversation": conversation
        }

        board_name = f"Slack Channel {project_id}"

    # ==========================================================
    # 🟢 TRELLO FLOW
    # ==========================================================
    elif source == "trello":

        trello_token = await get_user_token(user_id, db)

        if not trello_token:
            return {
                "status": "error",
                "message": "User not connected to Trello"
            }

        board_name = await get_board_name(user_id, project_id, db)

        pm_data = {
            "source": "trello",
            "board_id": project_id
        }

    # ==========================================================
    # ❌ INVALID SOURCE
    # ==========================================================
    else:
        return {
            "status": "error",
            "message": f"Invalid source: {source}"
        }

    # ==========================================================
    # 🧠 WORKFLOW STATE (SAFE + COMPLETE)
    # ==========================================================
    input_state = WorkflowState(
        project_id=project_id,
        project_name=board_name,

        # 🔥 SAFE TRELLO FIELDS (NO CRASH IN SLACK MODE)
        user_trello_key=os.getenv("TRELLO_API_KEY") if source == "trello" else "",
        user_trello_token=trello_token if source == "trello" else "",

        pm_data=pm_data,

        uploaded_pdf_bytes=b"",
        pdf_headings=pdf_headings,
        selected_headings=selected_headings,

        generated_docs="",
        feedback=data.get("feedback", "")
    )

    # ==========================================================
    # 🚀 RUN WORKFLOW
    # ==========================================================
    result = await workflow.ainvoke(input_state)

    final_doc = result.get("improved_docs") or result.get("generated_docs", "")
    formatted_doc = clean_generated_doc(str(final_doc), board_name)

    # ==========================================================
    # 🛡 SAFETY FALLBACK
    # ==========================================================
    if not formatted_doc.strip():
        formatted_doc = "No content generated."

    # ==========================================================
    # 🔁 MERGE WITH PREVIOUS VERSION
    # ==========================================================
    latest_entry = await docs_collection.find_one(
        {
            "user_id": user_id,
            "project_id": project_id,
            "template_name": template_name
        },
        sort=[("version", -1)]
    )

    if latest_entry:
        existing_doc = latest_entry.get("generated_docs", "")
        existing_headings = set(
            re.findall(r'##\s*(.+)', existing_doc, flags=re.IGNORECASE)
        )

        new_sections = re.findall(
            r'(##\s*.+?)(?=\n##|\Z)',
            formatted_doc,
            flags=re.DOTALL
        )

        content_to_add = []

        for section in new_sections:
            match = re.match(r'##\s*(.+)', section)
            if match:
                heading = match.group(1).strip()
                if heading not in existing_headings:
                    content_to_add.append(section.strip())

        if content_to_add:
            formatted_doc = (
                existing_doc.strip()
                + "\n\n---\n"
                + "\n\n".join(content_to_add)
            )
        else:
            formatted_doc = existing_doc

    # ==========================================================
    # 📦 VERSIONING
    # ==========================================================
    version_count = await docs_collection.count_documents({
        "user_id": user_id,
        "project_id": project_id,
        "template_name": template_name
    })

    version = version_count + 1

    # ==========================================================
    # 💾 SAVE TO DB
    # ==========================================================
    await docs_collection.insert_one({
        "user_id": user_id,
        "project_id": project_id,
        "template_name": template_name,
        "version": version,
        "generated_docs": formatted_doc,
        "board_name": board_name,
        "source": source,
        "team_id": data.get("team_id"),
        "created_at": datetime.utcnow()
    })

    # ==========================================================
    # RESPONSE
    # ==========================================================
    return {
        "status": "success",
        "template_name": template_name,
        "version": version,
        "generated_docs": formatted_doc
    }
