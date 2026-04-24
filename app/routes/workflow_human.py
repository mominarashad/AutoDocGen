from fastapi import APIRouter, Request
from app.graph.document_graph import workflow, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
import os

router = APIRouter(prefix="/workflow")


# --------------------------------------
# 🚀 START WORKFLOW (WITH HUMAN LOOP)
# --------------------------------------
@router.post("/start")
async def start_workflow(request: Request, payload: dict):
    db = request.app.state.db

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    source = payload.get("source", "trello")
    team_id = payload.get("team_id")

    # =====================================
    # 🔥 BUILD pm_data CORRECTLY
    # =====================================
    pm_data = {
        "source": source
    }

    trello_token = None

    if source == "slack":
        pm_data.update({
            "team_id": team_id,
            "channel_id": project_id
        })

    elif source == "trello":
        trello_token = await get_user_token(user_id, db)

    # =====================================
    # 🧠 BUILD STATE
    # =====================================
    input_state = WorkflowState(
        project_id=project_id,
        project_name="",
        user_trello_key=os.getenv("TRELLO_API_KEY"),
        user_trello_token=trello_token,
        pm_data=pm_data,
        uploaded_pdf_bytes=b"",
        pdf_headings=payload.get("pdf_headings", []),
        selected_headings=payload.get("selected_headings", []),
        generated_docs="",
        feedback=""
    )

    # =====================================
    # 🚀 RUN WORKFLOW
    # =====================================
    result = await workflow.ainvoke(input_state)

    # =====================================
    # ⏸ HUMAN INTERRUPT HANDLING
    # =====================================
    if "__interrupt__" in result:
        return {
            "status": "waiting_for_user",
            "interrupt": result["__interrupt__"][0],
            "state": result
        }

    return {
        "status": "completed",
        "data": result
    }


# --------------------------------------
# 🔁 RESUME WORKFLOW
# --------------------------------------
@router.post("/resume")
async def resume_workflow(request: Request, payload: dict):
    state = payload["state"]
    user_input = payload["user_input"]

    # 🔥 inject human response
    state["__interrupt__"] = [user_input]

    result = await workflow.ainvoke(state)

    if "__interrupt__" in result:
        return {
            "status": "waiting_for_user",
            "interrupt": result["__interrupt__"][0],
            "state": result
        }

    return {
        "status": "completed",
        "data": result
    }
