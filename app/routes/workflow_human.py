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
    source = payload.get("source") or "trello"
    team_id = payload.get("team_id")

    if not user_id or not project_id:
        return {"status": "error", "message": "Missing user_id or project_id"}

    pm_data = {}

    # ======================================================
    # 🔵 SLACK FLOW
    # ======================================================
    if source == "slack":
        if not team_id:
            return {"status": "error", "message": "team_id required"}

        from app.models.slack_model import get_slack_token
        from app.services.slack_service import fetch_channel_messages

        token = await get_slack_token(user_id, team_id, db)

        if not token:
            return {"status": "error", "message": "Slack not connected"}

        res = await fetch_channel_messages(token, project_id)

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

    # ======================================================
    # 🟢 TRELLO FLOW
    # ======================================================
    else:
        from app.models.user_token_model import get_user_token

        token = await get_user_token(user_id, db)

        pm_data = {
            "source": "trello",
            "board_id": project_id
        }

    # ======================================================
    # 🧠 BUILD STATE (IMPORTANT)
    # ======================================================
    input_state = WorkflowState(
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

    result = await workflow.ainvoke(input_state)

   final_doc = (
         result.get("final_doc")
         or result.get("improved_docs")
         or result.get("generated_docs")
         or ""
)

    if "__interrupt__" in result:
       return {
           "status": "waiting_for_user",
           "interrupt": result["__interrupt__"][0],
           "state": result
              }

    return {
        "status": "completed",
        "data": {
           "final_doc": final_doc   # ✅ ALWAYS RETURN THIS
                }
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
