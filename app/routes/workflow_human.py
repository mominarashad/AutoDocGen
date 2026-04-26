from fastapi import APIRouter, Request
from langgraph.types import Command
from app.graph.document_graph import workflow, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
from app.services.slack_service import fetch_channel_messages

import os

router = APIRouter(prefix="/workflow")


# ======================================================
# 🧠 BUILD STATE (ONLY FOR START)
# ======================================================
async def build_state(payload: dict, db):

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    source = payload.get("source")
    team_id = payload.get("team_id")

    # ✅ NEW FIELDS
    template = payload.get("template", "").strip()
    pdf_headings = payload.get("pdf_headings", [])
    selected_headings = payload.get("selected_headings", [])

    if not user_id or not project_id:
        raise ValueError("Missing user_id or project_id")

    if not template:
        raise ValueError("Template is required")

    pm_data = {}

    # ---------------- SLACK ----------------
    if source == "slack":
        slack_token = await get_slack_token(user_id, team_id, db)

        if not slack_token:
            raise ValueError("Slack not connected")

        res = await fetch_channel_messages(slack_token, project_id)
        messages = res.get("messages", [])

        conversation = "\n".join(
            f"{m.get('user')}: {m.get('text')}"
            for m in messages if m.get("text")
        )

        pm_data = {
            "source": "slack",
            "team_id": team_id,
            "channel_id": project_id,
            "conversation": conversation
        }

    # ---------------- TRELLO ----------------
    else:
        token = await get_user_token(user_id, db)

        if not token:
            raise ValueError("Trello not connected")

        pm_data = {
            "source": "trello",
            "board_id": project_id
        }

    #  RETURN FULL STATE INCLUDING HEADINGS + TEMPLATE
    return WorkflowState(
        project_id=project_id,
        user_id=user_id,
        template=template,

        pm_data=pm_data,

        pdf_headings=pdf_headings,
        selected_headings=selected_headings,

        draft_doc="",
        final_doc="",
        user_feedback=""
    )

# ======================================================
# 🚀 START WORKFLOW (FIRST GENERATION)
# ======================================================
@router.post("/start")
async def start_workflow(request: Request, payload: dict):

    db = request.app.state.db

    # ✅ BASIC VALIDATION (IMPORTANT)
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

    result = None

    async for event in workflow.astream(state, config=config):

        if isinstance(event, dict) and "__interrupt__" in event:
            interrupt = event["__interrupt__"][0]

            return {
                "status": "waiting_for_user",
                "interrupt": {
                    "id": getattr(interrupt, "id", None),
                    "value": {
                        "message": interrupt.value.get("message"),
                        "draft_doc": interrupt.value.get("draft_doc"),
                        "final_doc": interrupt.value.get("final_doc")
                    }
                }
            }

        result = event

    return {
    "status": "completed",
    "data": {
        "final_doc": result.get("final_doc") or result.get("draft_doc", "")
    }
}
# ======================================================
# 🔁 RESUME WORKFLOW (FIXED - NO REBUILD STATE)
# ======================================================


@router.post("/resume")
async def resume_workflow(request: Request, payload: dict):

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    template = payload.get("template")
    user_input = payload.get("user_input")

    config = {
        "configurable": {
            "thread_id": f"{user_id}_{project_id}_{template}"
        }
    }

    result = await workflow.ainvoke(
        Command(update={
            "user_feedback": user_input
        }),
        config=config
    )

    return {
        "status": "completed",
        "data": {
            "final_doc": result.get("final_doc", "")
        }
    }
