from fastapi import APIRouter, Request
from app.graph.document_graph import workflow, WorkflowState

router = APIRouter(prefix="/workflow")

# --------------------------------------
# 🚀 START WORKFLOW (PAUSE SUPPORT)
# --------------------------------------
@router.post("/start")
async def start_workflow(request: Request, payload: dict):
    db = request.app.state.db

    input_state = WorkflowState(
        project_id=payload["project_id"],
        project_name="",
        user_trello_key="",
        user_trello_token="",
        pm_data={},
        uploaded_pdf_bytes=b"",
        pdf_headings=[],
        selected_headings=[],
        generated_docs="",
        feedback=""
    )

    result = await workflow.ainvoke(input_state)

    # 🔥 HANDLE INTERRUPT
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
