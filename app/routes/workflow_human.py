from fastapi import APIRouter, Request
from app.graph.document_graph import workflow, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
from langgraph.types import Interrupt
import os

router = APIRouter(prefix="/workflow")


# ------------------------------------------------------
# 🧠 BUILD STATE (REPLACEMENT FOR MISSING FUNCTION)
# ------------------------------------------------------
def build_state(payload: dict, db):

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    source = payload.get("source") or "trello"
    team_id = payload.get("team_id")

    if not user_id or not project_id:
        raise ValueError("Missing user_id or project_id")

    pm_data = {}
    token = ""

    # ---------------- SLACK ----------------
    if source == "slack":
        from app.services.slack_service import fetch_channel_messages

        token = None  # slack token is not reused as trello token

        slack_token = None
        import asyncio
        slack_token = asyncio.run(get_slack_token(user_id, team_id, db))

        if not slack_token:
            raise ValueError("Slack not connected")

        res = asyncio.run(fetch_channel_messages(slack_token, project_id))
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
        token = asyncio.run(get_user_token(user_id, db))

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
# 🚀 START WORKFLOW (WITH HUMAN LOOP)
# ------------------------------------------------------
@router.post("/start")
async def start_workflow(request: Request, payload: dict):
    db = request.app.state.db

    input_state = build_state(payload, db)

    try:
        result = await workflow.ainvoke(input_state)

        return {
            "status": "completed",
            "data": {
                "final_doc": result.get("final_doc", "")
            }
        }

    except Exception as e:
        # THIS is where interrupt comes
        if "interrupt" in str(e).lower():
            return {
                "status": "waiting_for_user",
                "interrupt": {
                    "draft": input_state.get("draft_doc", "")
                },
                "state": input_state
            }

        return {"status": "error", "message": str(e)}
# ------------------------------------------------------
# 🔁 RESUME WORKFLOW
# ------------------------------------------------------
@router.post("/resume")
async def resume_workflow(request: Request, payload: dict):

    state = payload.get("state")
    user_input = payload.get("user_input")

    if not state:
        return {"status": "error", "message": "Missing state"}

    state["reviewed_doc"] = user_input

    try:
        result = await workflow.ainvoke(state)

        return {
            "status": "completed",
            "data": {
                "final_doc": result.get("final_doc", "")
            }
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
