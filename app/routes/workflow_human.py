from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from app.graph.document_graph import workflow, WorkflowState
from app.models.user_token_model import get_user_token
from app.models.slack_model import get_slack_token
from app.services.slack_service import get_channel_name, run_slack_workflow
from app.services.doc_storage_service import save_generated_doc
from app.services.trello_service import get_board_name
import os
import json

router = APIRouter(prefix="/workflow")


# ======================================================
# 🧠 BUILD STATE (UNCHANGED)
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
# 🚀 NEW STREAMING ENDPOINT (FINAL FIX)
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

        async for event in workflow.astream(state, config=config):

            # ================= INTERRUPT =================
            if "__interrupt__" in event:
                yield json.dumps({
                    "type": "interrupt",
                    "data": event["__interrupt__"][0]
                }) + "\n"
                return

            # ================= STREAM TOKENS =================
            if "__stream__" in event:
                yield json.dumps({
                    "type": "token",
                    "data": event["__stream__"]
                }) + "\n"

            # ================= CAPTURE FINAL =================
            if "final_doc" in event or "draft_doc" in event:
                final_doc = event.get("final_doc") or event.get("draft_doc", "")

        # ================= SAVE AFTER STREAM =================
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

        # ================= FINAL EVENT =================
        yield json.dumps({
            "type": "done",
            "data": final_doc
        }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/json")


# ======================================================
# 🚀 EXISTING START (UNCHANGED SAFE FALLBACK)
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

        if "__interrupt__" in event:
            return {
                "status": "waiting_for_user",
                "interrupt": event["__interrupt__"][0]
            }

        final_result = event

    final_doc = final_result.get("final_doc") or final_result.get("draft_doc", "")

    if isinstance(final_doc, dict):
        final_doc = final_doc.get("content", "")

    project_name = state.get("project_name") or state["project_id"]

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

    return {
        "status": "completed",
        "data": {"final_doc": final_doc}
    }


# ======================================================
# 🧠 INTENT CLASSIFIER (UNCHANGED)
# ======================================================
def classify_user_intent(feedback: str):
    text = feedback.lower()

    if "add:" in text:
        return "new_heading"
    if "update" in text or "in section" in text:
        return "edit_section"
    if "improve" in text or "expand" in text or "detail" in text:
        return "refine"

    return "refine"


# ======================================================
# 🔁 RESUME WORKFLOW (UNCHANGED)
# ======================================================
@router.post("/resume")
async def resume_workflow(request: Request, payload: dict):

    db = request.app.state.db

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    template = payload.get("template")

    user_input = payload.get("user_input", "")
    is_final = payload.get("is_final", False)

    if is_final:
        user_input = ""

    config = {
        "configurable": {
            "thread_id": f"{user_id}_{project_id}_{template}"
        }
    }

    intent = classify_user_intent(user_input)

    result = await workflow.ainvoke(
        Command(resume={
            "user_feedback": user_input,
            "intent": intent,
            "new_headings": payload.get("new_headings", []),
            "is_final": is_final
        }),
        config=config
    )

    final_doc = result.get("final_doc", "")
    project_name = result.get("project_name") or project_id

    await save_generated_doc(
        db=db,
        user_id=user_id,
        project_id=project_id,
        template_name=template,
        content=final_doc,
        source=payload.get("source", "trello"),
        team_id=payload.get("team_id"),
        is_final=is_final,
        workspace_name=project_name
    )

    return {
        "status": "completed",
        "data": {"final_doc": final_doc}
    }
