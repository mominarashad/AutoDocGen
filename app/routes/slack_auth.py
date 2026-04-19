import os
import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from app.db import get_db
from datetime import datetime

router = APIRouter()

CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")


# =========================
# STEP 1: INSTALL APP
# =========================
@router.get("/connect")
def slack_connect(user_id: str):
    url = (
        "https://slack.com/oauth/v2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&scope=channels:read,channels:history,channels:join,chat:write,users:read,team:read"
        f"&user_scope="
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={user_id}"
    )
    return RedirectResponse(url)


# =========================
# STEP 2: CALLBACK
# =========================
@router.get("/callback")
async def slack_callback(code: str, state: str, db=Depends(get_db)):

    user_id = state

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
            }
        )

    data = res.json()

    if not data.get("ok"):
        return {"status": "error", "message": data}

    team_id = data["team"]["id"]
    access_token = data["access_token"]

    await db["slack_connections"].update_one(
        {"user_id": user_id, "team_id": team_id},
        {
            "$set": {
                "user_id": user_id,
                "team_id": team_id,
                "access_token": access_token,
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )

    return RedirectResponse(f"{FRONTEND_URL}/slack?team_id={team_id}")
