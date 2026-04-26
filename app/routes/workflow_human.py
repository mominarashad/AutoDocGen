from fastapi import APIRouter, Request
from app.graph.document_graph import workflow, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
from app.services.slack_service import fetch_channel_messages
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
        final_doc="",
        user_feedback=""   # ✅ ADD THIS
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

    result = None  # ✅ important fallback

    async for event in workflow.astream(state, config=config):

        print("🔥 EVENT:", event)

        # 🔴 INTERRUPT DETECTED
        if isinstance(event, dict) and "__interrupt__" in event:
            interrupt = event["__interrupt__"][0]

            print("🧠 INTERRUPT VALUE:", interrupt.value)

            return {
                "status": "waiting_for_user",
                "interrupt": {
                    "id": getattr(interrupt, "id", None),
                    "value": {
                        "message": interrupt.value.get("message"),
                        "final_doc": interrupt.value.get("final_doc"),  # ✅ FIXED
                        "draft_doc": interrupt.value.get("draft_doc")   # fallback
                    }
                }
            }

        result = event  # keep latest state

    # ✅ completed without interrupt
    return {
        "status": "completed",
        "data": result
    }


# ------------------------------------------------------
# 🔁 RESUME WORKFLOW (🔥 FULLY FIXED)
# ------------------------------------------------------
@router.post("/resume")
async def resume_workflow(request: Request, payload: dict):

    db = request.app.state.db

    user_input = payload.get("user_input")
    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    template = payload.get("template")
    source = payload.get("source")
    team_id = payload.get("team_id")

    # 🔥 REBUILD STATE (NEW RUN)
    state = await build_state(payload, db)

    # 🔥 PASS USER FEEDBACK
    state["user_feedback"] = user_input

    config = {
        "configurable": {
            "thread_id": f"{user_id}_{project_id}_{template}"
        }
    }

    result = await workflow.ainvoke(
        state,
        config=config
    )

    final_doc = result.get("final_doc") or ""

    return {
        "status": "completed",
        "data": {
            "final_doc": final_doc
        }
    }
