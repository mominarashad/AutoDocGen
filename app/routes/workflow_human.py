from fastapi import APIRouter, Request
from app.graph.document_graph import workflow, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
import os
from langgraph.types import Interrupt
router = APIRouter(prefix="/workflow")


# --------------------------------------
# 🚀 START WORKFLOW (WITH HUMAN LOOP)
# --------------------------------------
@router.post("/start")
async def start_workflow(request: Request, payload: dict):
    db = request.app.state.db

    input_state = build_state(payload, db)

    try:
        async for event in workflow.astream(input_state):

            # 🚨 HUMAN INTERRUPT
            if isinstance(event, Interrupt):
                return {
                    "status": "waiting_for_user",
                    "interrupt": event.value,
                    "state": event.state
                }

            final_state = event

        return {
            "status": "completed",
            "data": {
                "final_doc": final_state.get("final_doc", "")
            }
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
# --------------------------------------
# 🔁 RESUME WORKFLOW
# --------------------------------------
@router.post("/resume")
async def resume_workflow(request: Request, payload: dict):

    state = payload["state"]
    user_input = payload["user_input"]

    state["__interrupt__"] = [user_input]

    try:
        async for event in workflow.astream(state):

            if isinstance(event, Interrupt):
                return {
                    "status": "waiting_for_user",
                    "interrupt": event.value,
                    "state": event.state
                }

            final_state = event

        return {
            "status": "completed",
            "data": {
                "final_doc": final_state.get("final_doc", "")
            }
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    }
