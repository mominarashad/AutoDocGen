from fastapi import APIRouter, Request, HTTPException
from langgraph.types import Command
from app.graph.document_graph import workflow, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
from app.services.slack_service import fetch_channel_messages, get_channel_name
from app.services.doc_storage_service import save_generated_doc
from app.services.trello_service import get_board_name
import os
import re  # ✅ ADDED

router = APIRouter(prefix="/workflow")


# ======================================================
# 🧠 BUILD STATE
# ======================================================
async def build_state(payload: dict, db):

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    source = payload.get("source")
    team_id = payload.get("team_id")

    template = payload.get("template", "").strip()
    pdf_headings = payload.get("pdf_headings", [])
    selected_headings = payload.get("selected_headings", [])

    if not user_id or not project_id:
        raise ValueError("Missing user_id or project_id")

    if not template:
        raise ValueError("Template is required")

    pm_data = {}
    project_name = None

    # ---------------- SLACK ----------------
    if source == "slack":

        slack_token = await get_slack_token(user_id, team_id, db)
        if not slack_token:
            raise ValueError("Slack not connected")

        res = await fetch_channel_messages(slack_token, project_id)
        messages = res.get("messages", [])

        conversation = "\n".join(
            f"{m.get('user', 'unknown')}: {m.get('text', '')}"
            for m in messages if m.get("text")
        )

        channel_name = await get_channel_name(slack_token, project_id)

        pm_data = {
            "source": "slack",
            "team_id": team_id,
            "channel_id": project_id,
            "conversation": conversation
        }

        project_name = channel_name

    # ---------------- TRELLO ----------------
    else:
        token = await get_user_token(user_id, db)
        if not token:
            raise ValueError("Trello not connected")

        board_name = await get_board_name(user_id, project_id, db)

        pm_data = {
            "source": "trello",
            "board_id": project_id
        }

        project_name = board_name

    return WorkflowState(
        project_id=project_id,
        user_id=user_id,
        template=template,
        project_name=project_name,
        pm_data=pm_data,
        pdf_headings=pdf_headings,
        selected_headings=selected_headings,
        draft_doc="",
        final_doc="",
        user_feedback="",
        user_trello_key=os.getenv("TRELLO_API_KEY", ""),
        user_trello_token=os.getenv("TRELLO_TOKEN", "")
    )


# ======================================================
# 🔁 MERGE FUNCTION (🔥 CORE FIX)
# ======================================================
async def merge_with_previous(db, user_id, project_id, template, new_doc):

    collection = db["generated_docs"]

    latest = await collection.find_one(
        {
            "user_id": user_id,
            "project_id": project_id,
            "template_name": template
        },
        sort=[("version", -1)]
    )

    if not latest:
        return new_doc

    existing = latest.get("generated_docs", "")

    existing_heads = set(re.findall(r'##\s*(.+)', existing))
    new_sections = re.findall(r'(##\s*.+?)(?=\n##|\Z)', new_doc, flags=re.DOTALL)

    additions = []

    for sec in new_sections:
        match = re.match(r'##\s*(.+)', sec)
        if match:
            heading = match.group(1).strip()
            if heading not in existing_heads:
                additions.append(sec.strip())

    if additions:
        return existing.strip() + "\n\n---\n\n" + "\n\n".join(additions)

    return existing


# ======================================================
# 🚀 START WORKFLOW
# ======================================================
@router.post("/start")
async def start_workflow(request: Request, payload: dict):

    db = request.app.state.db
    state = await build_state(payload, db)

    config = {
        "configurable": {
            "thread_id": f"{state['user_id']}_{state['project_id']}_{state['template']}"
        }
    }

    final_result = None

    async for event in workflow.astream(state, config=config):
        if isinstance(event, dict) and "__interrupt__" in event:
            return {
                "status": "waiting_for_user",
                "interrupt": event["__interrupt__"][0]
            }
        final_result = event

    final_doc = final_result.get("final_doc") or final_result.get("draft_doc", "")

    if isinstance(final_doc, dict):
        final_doc = final_doc.get("content", "")

    # 🔥 MERGE FIX APPLIED
    merged_doc = await merge_with_previous(
        db,
        state["user_id"],
        state["project_id"],
        state["template"],
        final_doc
    )

    await save_generated_doc(
        db=db,
        user_id=state["user_id"],
        project_id=state["project_id"],
        template_name=state["template"],
        content=merged_doc,  # ✅ FIXED
        source=state["pm_data"].get("source", "trello"),
        team_id=state["pm_data"].get("team_id"),
        workspace_name=state.get("project_name")
    )

    return {
        "status": "completed",
        "data": {"final_doc": merged_doc}
    }


# ======================================================
# 🧠 INTENT CLASSIFIER
# ======================================================
def classify_user_intent(feedback: str):
    text = feedback.lower()

    if "add:" in text:
        return "new_heading"
    if "update" in text or "in section" in text:
        return "edit_section"
    if "improve" in text or "expand" in text or "detail" in text:
        return "refine"

    return "refine"


# ======================================================
# 🔁 RESUME WORKFLOW
# ======================================================
@router.post("/resume")
async def resume_workflow(request: Request, payload: dict):

    db = request.app.state.db

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    template = payload.get("template")

    user_input = payload.get("user_input", "")
    is_final = payload.get("is_final", False)

    if is_final:
        user_input = ""

    config = {
        "configurable": {
            "thread_id": f"{user_id}_{project_id}_{template}"
        }
    }

    intent = classify_user_intent(user_input)

    result = await workflow.ainvoke(
        Command(resume={
            "user_feedback": user_input,
            "intent": intent,
            "new_headings": payload.get("new_headings", []),
            "is_final": is_final
        }),
        config=config
    )

    final_doc = result.get("final_doc", "")

    # 🔥 MERGE FIX APPLIED
    merged_doc = await merge_with_previous(
        db,
        user_id,
        project_id,
        template,
        final_doc
    )

    project_name = result.get("project_name") or project_id

    await save_generated_doc(
        db=db,
        user_id=user_id,
        project_id=project_id,
        template_name=template,
        content=merged_doc,  # ✅ FIXED
        source=payload.get("source", "trello"),
        team_id=payload.get("team_id"),
        is_final=is_final,
        workspace_name=project_name
    )

    return {
        "status": "completed",
        "data": {"final_doc": merged_doc}
    }
