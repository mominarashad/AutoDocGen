from fastapi import APIRouter, Request
from langgraph.types import Command
from app.graph.document_graph import workflow, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
from app.services.slack_service import fetch_channel_messages
from datetime import datetime
from langgraph.types import Interrupt
import os

router = APIRouter(prefix="/workflow")


# ------------------------------------------------------
# 🧠 BUILD STATE
# ------------------------------------------------------
async def build_state(payload: dict, db):

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    source = payload.get("source")
    team_id = payload.get("team_id")
    template = payload.get("template", "")

    if not user_id or not project_id:
        raise ValueError("Missing user_id or project_id")

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

    return WorkflowState(
        project_id=project_id,
        user_id=user_id,
        template=template,
        pm_data=pm_data,
        draft_doc="",
        reviewed_doc="",
        final_doc=""
    )


# ------------------------------------------------------
# 🚀 START WORKFLOW
# ------------------------------------------------------


@router.post("/start")
async def start_workflow(request: Request, payload: dict):

    db = request.app.state.db
    state = await build_state(payload, db)

    config = {
        "configurable": {
            "thread_id": f"{state['user_id']}_{state['project_id']}_{state['template']}"
        }
    }

    result = await workflow.ainvoke(state, config=config)

    # ==================================================
    # 🔥 CHECK IF INTERRUPT EXISTS IN RESULT
    # ==================================================
    if isinstance(result, dict) and result.get("__interrupt__"):
        interrupt = result["__interrupt__"][0]

        return {
            "status": "waiting_for_user",
            "interrupt": {
                "value": interrupt.value,
                "id": getattr(interrupt, "id", None)
            }
        }

    return {
        "status": "completed",
        "result": result
    }
# ------------------------------------------------------
# 🔁 RESUME WORKFLOW
# ------------------------------------------------------
@router.post("/resume")
async def resume_workflow(request: Request, payload: dict):

    user_input = payload.get("user_input")
    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    template = payload.get("template")

    config = {
        "configurable": {
            "thread_id": f"{user_id}_{project_id}_{template}"
        }
    }

    result = await workflow.ainvoke(
        Command(resume=user_input),
        config=config
    )

    final_doc = result.get("final_doc") or ""

    return {
        "status": "completed",
        "data": {
            "final_doc": final_doc
        }
    }
