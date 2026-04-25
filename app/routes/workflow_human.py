from fastapi import APIRouter, Request
from app.graph.document_graph import workflow, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
from langgraph.types import Command
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

    if not source:
        source = "trello" if payload.get("board_id") else "slack"

    if not user_id or not project_id:
        raise ValueError("Missing user_id or project_id")

    pm_data = {}
    token = None

    # ---------------- SLACK ----------------
    if source == "slack":
        slack_token = await get_slack_token(user_id, team_id, db)

        if not slack_token:
            raise ValueError("Slack not connected")

        from app.services.slack_service import fetch_channel_messages

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
        project_name="",
        user_trello_key=os.getenv("TRELLO_API_KEY") if source == "trello" else "",
        user_trello_token=token if source == "trello" else "",
        pm_data=pm_data,
        uploaded_pdf_bytes=b"",
        pdf_headings=[],
        selected_headings=[],
        generated_docs="",
        feedback=""
    )


# ------------------------------------------------------
# 🚀 START WORKFLOW (FIXED INTERRUPT HANDLING)
# ------------------------------------------------------
@router.post("/start")
async def start_workflow(request: Request, payload: dict):

    db = request.app.state.db

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    template = payload.get("template")

    input_state = await build_state(payload, db)

    config = {
        "configurable": {
            "thread_id": f"{user_id}_{project_id}_{template}"
        }
    }

    # ✅ FIX: proper LangGraph streaming pattern
    async for event in workflow.astream(input_state, config=config):

        # 🔥 FIXED SAFE CHECK (important)
        if isinstance(event, dict) and "__interrupt__" in event:

            interrupt = event["__interrupt__"][0]

            return {
                "status": "waiting_for_user",
                "interrupt": {
                    "value": interrupt.value,
                    "id": getattr(interrupt, "id", None)
                },
                "state": input_state
            }

    return {
        "status": "completed",
        "data": {
            "final_doc": input_state.get("generated_docs", "")
        }
    }


# ------------------------------------------------------
# 🔁 RESUME WORKFLOW (CORRECT HITL PATTERN)
# ------------------------------------------------------
@router.post("/resume")
async def resume_workflow(request: Request, payload: dict):

    state = payload.get("state")
    user_input = payload.get("user_input")

    if not state:
        return {"status": "error", "message": "Missing state"}

    user_id = state.get("user_id")
    project_id = state.get("project_id")
    template = state.get("template")

    if not user_id or not project_id or not template:
        return {"status": "error", "message": "Invalid state keys"}

    config = {
        "configurable": {
            "thread_id": f"{user_id}_{project_id}_{template}"
        }
    }

    # ✅ FIX: correct HITL resume pattern (LangGraph standard)
    result = await workflow.ainvoke(
        Command(resume=user_input),
        config=config
    )

    return {
        "status": "completed",
        "data": {
            "final_doc": result.get("final_doc", "")
        }
    }
