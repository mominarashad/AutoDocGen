import os
import re
import motor.motor_asyncio
import uvicorn
import httpx

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from datetime import datetime  # ✅ added

# ------------------ Load ENV ------------------
load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "Doc_Gen")
PORT = int(os.getenv("PORT", 8080))
BASE_URL = os.getenv("BASE_URL")

TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_CALLBACK_URL = os.getenv("TRELLO_CALLBACK_URL") or f"{BASE_URL}/pm"

SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI not set")

# ------------------ App ------------------
app = FastAPI()

# ------------------ CORS ------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://autodocgen-production.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Routers ------------------
from app.routes import auth as auth_router
from app.routes import user as user_router
from app.routes import templates as templates_router
from app.routes import generated_docs as generated_docs_router
from app.routes.trello_webhook import router as trello_webhook_router

# Slack routers
from app.routes.slack_auth import router as slack_auth_router
from app.routes.slack_channels import router as slack_channels_router
from app.routes.slack_messages import router as slack_messages_router

app.include_router(auth_router.router, prefix="/auth")
app.include_router(user_router.router, prefix="/api")
app.include_router(templates_router.router, prefix="/templates")
app.include_router(generated_docs_router.router, prefix="/generated-docs")

app.include_router(trello_webhook_router)

# Slack routes
app.include_router(slack_auth_router, prefix="/slack/auth")
app.include_router(slack_channels_router, prefix="/api")
app.include_router(slack_messages_router, prefix="/api")

# ------------------ Services ------------------
from app.services.trello_service import connect_to_trello
from app.models.user_token_model import (
    get_all_user_tokens,
    get_user_token,
    save_user_token
)

from app.services.workflow_service import execute_workflow
from app.services.slack_service import fetch_channels

# ------------------ MongoDB Startup ------------------
@app.on_event("startup")
async def startup():

    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    app.state.mongo_client = client
    app.state.db = client[DB_NAME]
    db = app.state.db

    print("✅ MongoDB connected")

    await db["notifications"].create_index(
        "action_id",
        unique=True,
        sparse=True
    )

    await db["slack_connections"].create_index(
        [("user_id", 1), ("team_id", 1)],
        unique=True
    )

    users = await get_all_user_tokens(db)

    if not users:
        print("⚠️ No users with Trello tokens found")
        return

    if getattr(app.state, "webhooks_registered", False):
        return
    app.state.webhooks_registered = True

    async with httpx.AsyncClient(timeout=20) as client_http:

        for user in users:
            token = user.get("trello_token")
            user_id = user.get("user_id")

            if not token:
                continue

            try:
                res = await client_http.get(
                    "https://api.trello.com/1/members/me/boards",
                    params={
                        "key": TRELLO_API_KEY,
                        "token": token,
                        "fields": "id,name"
                    }
                )
                res.raise_for_status()
                boards = res.json()
            except Exception as e:
                print(f"❌ Failed boards for user {user_id}: {e}")
                continue

            for board in boards:
                await db["board_user_map"].update_one(
                    {"board_id": board["id"]},
                    {"$set": {
                        "user_id": user_id,
                        "board_name": board["name"]
                    }},
                    upsert=True
                )

# ------------------ Shutdown ------------------
@app.on_event("shutdown")
async def shutdown():
    app.state.mongo_client.close()

# ------------------ Trello ------------------
@app.get("/trello/connect")
def trello_connect(request: Request):
    user_id = request.query_params.get("user_id")
    return connect_to_trello(user_id)

@app.get("/trello/callback")
def trello_callback():
    return RedirectResponse(f"{FRONTEND_URL}/boards")

@app.post("/trello/save_token")
async def trello_save_token(request: Request):
    data = await request.json()
    db = app.state.db

    await save_user_token(
        data["user_id"],
        data["trello_token"],
        db
    )

    return {"status": "success"}

# ------------------ Boards ------------------
@app.get("/trello/boards_with_headings")
async def boards_with_headings(user_id: str):
    db = app.state.db

    token = await get_user_token(user_id, db)
    if not token:
        return {"status": "error", "boards": []}

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            "https://api.trello.com/1/members/me/boards",
            params={
                "key": TRELLO_API_KEY,
                "token": token,
                "fields": "id,name,desc"
            }
        )
        boards = res.json()

    docs = await db["generated_docs"].find({"user_id": user_id}).to_list(None)
    doc_map = {d["project_id"]: d for d in docs}

    result = []

    for b in boards:
        raw = doc_map.get(b["id"], {}).get("generated_docs", "")
        headings = re.findall(r"##\s*(.+)", raw)

        result.append({
            "id": b["id"],
            "name": b["name"],
            "desc": b.get("desc", ""),
            "has_generated_doc": b["id"] in doc_map,
            "previous_headings": headings
        })

    return {"status": "success", "boards": result}

# ------------------ Slack Channels ------------------
@app.get("/slack/channels_with_headings")
async def channels_with_headings(user_id: str, team_id: str):
    db = app.state.db

    from app.models.slack_model import get_slack_token

    token = await get_slack_token(user_id, team_id, db)

    if not token:
        return {"status": "error", "channels": []}

    data = await fetch_channels(token)

    if not data.get("ok"):
        return {"status": "error", "channels": []}

    channels = data.get("channels", [])

    docs = await db["generated_docs"].find({"user_id": user_id}).to_list(None)
    doc_map = {d["project_id"]: d for d in docs}

    result = []

    for ch in channels:
        channel_id = ch["id"]

        raw = doc_map.get(channel_id, {}).get("generated_docs", "")
        headings = re.findall(r"##\s*(.+)", raw)

        result.append({
            "id": channel_id,
            "name": ch["name"],
            "topic": ch.get("topic", {}).get("value", ""),
            "has_generated_doc": channel_id in doc_map,
            "previous_headings": headings,
            "template_key": "default_slack_template",
            "template_name": "Slack Default Template"
        })

    return {"status": "success", "channels": result}

# ------------------ Workflow ------------------
@app.post("/workflow/run")
async def run_workflow(request: Request):
    data = await request.json()

    if not all(k in data for k in ("user_id", "project_id", "template")):
        raise HTTPException(status_code=400, detail="Missing required fields")

    return await execute_workflow(
        data["user_id"],
        data["project_id"],
        data,
        db=request.app.state.db
    )

# ------------------ Improve with Feedback ------------------
@app.post("/workflow/improve-with-feedback")
async def improve_with_feedback(request: Request):
    data = await request.json()
    db = request.app.state.db

    user_id = data.get("user_id")
    project_id = data.get("project_id")
    template_name = data.get("template_name")
    feedback = data.get("feedback")

    if not all([user_id, project_id, template_name, feedback]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    doc = await db["generated_docs"].find_one(
        {
            "user_id": user_id,
            "project_id": project_id,
            "template_name": template_name
        },
        sort=[("version", -1)]
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')

    prompt = f"""
Improve the document based on user feedback.

DOCUMENT:
{doc.get("generated_docs", "")}

FEEDBACK:
{feedback}

Return improved document only.
"""

    result = await llm.ainvoke(prompt)
    improved_doc = result.content if hasattr(result, "content") else str(result)

    new_version = (doc.get("version") or 1) + 1

    await db["generated_docs"].insert_one({
        "user_id": user_id,
        "project_id": project_id,
        "template_name": template_name,
        "version": new_version,
        "generated_docs": improved_doc,
        "board_name": doc.get("board_name", "Unknown"),
        "created_at": datetime.utcnow()
    })

    return {
        "status": "success",
        "version": new_version,
        "generated_docs": improved_doc
    }

# ------------------ Generated Doc ------------------
@app.get("/workflow/generated")
async def get_generated_doc(user_id: str, project_id: str, template_name: str):
    db = app.state.db

    doc = await db["generated_docs"].find_one({
        "user_id": user_id,
        "project_id": project_id,
        "template_name": template_name
    })

    if not doc:
        return await execute_workflow(
            user_id,
            project_id,
            {"template": template_name},
            db=db
        )

    return {
        "status": "success",
        "template_name": template_name,
        "generated_docs": doc.get("generated_docs", ""),
        "board_name": doc.get("board_name", "Unknown Board")
    }

# ------------------ Run ------------------
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
