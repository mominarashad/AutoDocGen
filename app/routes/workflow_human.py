from fastapi import APIRouter, Request
from langgraph.types import Command
from app.graph.document_graph import workflow, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
from app.services.slack_service import fetch_channel_messages
from app.services.doc_storage_service import save_generated_doc  
import os

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
    conversation = ""
    project_name = template or "Project"

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

        pm_data = {
            "source": "slack",
            "team_id": team_id,
            "channel_id": project_id,
            "conversation": conversation
        }

        project_name = f"Slack Project {project_id}"

    # ---------------- TRELLO ----------------
    else:
        token = await get_user_token(user_id, db)

        if not token:
            raise ValueError("Trello not connected")

        pm_data = {
            "source": "trello",
            "board_id": project_id
        }

        project_name = f"Trello Project {project_id}"

    return WorkflowState(
        project_id=project_id,
        user_id=user_id,
        template=template,

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
# 🚀 START WORKFLOW
# ======================================================
@router.post("/start")
async def start_workflow(request: Request, payload: dict):

    db = request.app.state.db

    if not payload.get("template"):
        return {"status": "error", "message": "Template selection required"}

    if not payload.get("selected_headings"):
        return {"status": "error", "message": "Please select at least one heading"}

    state = await build_state(payload, db)

    config = {
        "configurable": {
            "thread_id": f"{state['user_id']}_{state['project_id']}_{state['template']}"
        }
    }

    result = await workflow.ainvoke(state, config=config)

    final_doc = result.get("final_doc") or result.get("draft_doc", "")

    if isinstance(final_doc, dict):
        final_doc = final_doc.get("content", "")

    await save_generated_doc(
    db=db,
    user_id=state["user_id"],
    project_id=state["project_id"],
    template_name=state["template"],
    content=final_doc,   # ✅ FIXED
    source=state["pm_data"].get("source"),
    team_id=state["pm_data"].get("team_id"),
)

    return {
        "status": "completed",
        "data": {
            "final_doc": final_doc
        }
    }


# ======================================================
# 🧠 INTENT CLASSIFIER
# ======================================================
def classify_user_intent(feedback: str):
    text = feedback.lower()

    if "add:" in text or "new heading" in text:
        return "new_heading"

    if "in section" in text or "in heading" in text or "update" in text:
        return "edit_section"

    return "regenerate"


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
            "new_headings": payload.get("new_headings", [])
        }),
        config=config
    )

    final_doc = result.get("final_doc", "")

    # ======================================================
    # ✅ SAVE UPDATED VERSION (VERSIONING SUPPORT)
    # ======================================================
    await save_generated_doc(
        db=db,
        user_id=user_id,
        project_id=project_id,
        template_name=template,
        content=final_doc,
        source="update",
        team_id=None,
        board_name=project_id
    )

    return {
        "status": "completed",
        "data": {
            "final_doc": final_doc
        }
    }
