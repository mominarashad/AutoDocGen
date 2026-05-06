from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from app.graph.document_graph import workflow, workflow_fresh, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
from app.services.slack_service import get_channel_name, run_slack_workflow
from app.services.doc_storage_service import save_generated_doc
from app.services.trello_service import get_board_name
import os
import json

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
    project_name = None

    # ================= SLACK =================
    if source == "slack":
        slack_token = await get_slack_token(user_id, team_id, db)
        if not slack_token:
            raise ValueError("Slack not connected")

        slack_result = await run_slack_workflow(
            user_id=user_id,
            team_id=team_id,
            channel_id=project_id,
            db=db
        )
        if slack_result.get("status") != "success":
            raise ValueError("Slack fetch failed")

        conversation = slack_result.get("conversation", "")
        channel_name = await get_channel_name(slack_token, project_id)

        pm_data = {
            "source": "slack",
            "team_id": team_id,
            "channel_id": project_id,
            "conversation": conversation
        }
        project_name = channel_name

    # ================= TRELLO =================
    else:
        token = await get_user_token(user_id, db)
        if not token:
            raise ValueError("Trello not connected")

        board_name = await get_board_name(user_id, project_id, db)
        pm_data = {
            "source": "trello",
            "board_id": project_id
        }
        project_name = board_name

    return WorkflowState(
        project_id=project_id,
        user_id=user_id,
        template=template,
        project_name=project_name,
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
# 🚀 STREAMING ENDPOINT — workflow_fresh (no checkpoint)
# ======================================================
@router.post("/start-stream")
async def start_workflow_stream(request: Request, payload: dict):

    db = request.app.state.db
    state = await build_state(payload, db)

    config = {
        "configurable": {
            "thread_id": f"{state['user_id']}_{state['project_id']}_{state['template']}"
        }
    }

    async def event_generator():

        final_doc = ""
        project_name = state.get("project_name") or state["project_id"]

        async for event in workflow_fresh.astream(
            state,
            config=config,
            stream_mode=["updates", "custom"]
        ):

            # ======================================================
            # CUSTOM TOKEN STREAM
            # ======================================================
            if isinstance(event, tuple) and event[0] == "custom":
                token = event[1].get("token")
                if token:
                    yield "data: " + json.dumps({
                        "type": "token",
                        "data": token
                    }) + "\n\n"
                continue

            # ======================================================
            # UPDATES MODE
            # ======================================================
            if isinstance(event, tuple) and event[0] == "updates":
                node_events = event[1]

                # INTERRUPT
                if isinstance(node_events, dict) and "__interrupt__" in node_events:
                    interrupt_data = node_events["__interrupt__"][0]
                    yield "data: " + json.dumps({
                        "type": "interrupt",
                        "data": {
                            "value": getattr(interrupt_data, "value", str(interrupt_data)),
                            "resumable": getattr(interrupt_data, "resumable", True),
                            "ns": getattr(interrupt_data, "ns", None),
                            "when": getattr(interrupt_data, "when", "during"),
                        }
                    }) + "\n\n"
                    return

                # NODE OUTPUT
                for node_name, node_output in node_events.items():
                    if not isinstance(node_output, dict):
                        continue
                    if node_output.get("draft_doc"):
                        yield "data: " + json.dumps({
                            "type": "token",
                            "data": node_output["draft_doc"]
                        }) + "\n\n"
                    if node_output.get("final_doc"):
                        final_doc = node_output["final_doc"]

        if isinstance(final_doc, dict):
            final_doc = final_doc.get("content", "")

        await save_generated_doc(
            db=db,
            user_id=state["user_id"],
            project_id=state["project_id"],
            template_name=state["template"],
            content=final_doc,
            source=state["pm_data"].get("source", "trello"),
            team_id=state["pm_data"].get("team_id"),
            workspace_name=project_name
        )

        yield "data: " + json.dumps({
            "type": "done",
            "data": final_doc
        }) + "\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ======================================================
# 🚀 NON-STREAM ENDPOINT
# ======================================================
@router.post("/start")
async def start_workflow(request: Request, payload: dict):

    db = request.app.state.db
    state = await build_state(payload, db)

    config = {
        "configurable": {
            "thread_id": f"{state['user_id']}_{state['project_id']}_{state['template']}"
        }
    }

    final_result = None

    async for event in workflow.astream(state, config=config):
        if isinstance(event, dict) and "__interrupt__" in event:
            interrupt_data = event["__interrupt__"][0]
            return {
                "status": "waiting_for_user",
                "interrupt": {
                    "value": getattr(interrupt_data, "va
