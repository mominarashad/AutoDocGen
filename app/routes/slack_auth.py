import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
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

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    url = (
        "https://slack.com/oauth/v2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&scope=channels:read,channels:history,channels:join,chat:write,users:read,team:read"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={user_id}"
        f"&response_type=code"
    )

    return RedirectResponse(url, status_code=302)


# =========================
# STEP 2: CALLBACK
# =========================
@router.get("/callback")
async def slack_callback(code: str, state: str, db=Depends(get_db)):

    if not code or not state:
        raise HTTPException(status_code=400, detail="Invalid Slack callback")

    user_id = state

    async with httpx.AsyncClient(timeout=20) as client:
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
        raise HTTPException(status_code=400, detail=data)

    team_id = data["team"]["id"]
    access_token = data.get("access_token") or data.get("authed_user", {}).get("access_token")

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
    return RedirectResponse(
        f"{FRONTEND_URL}/slack?team_id={team_id}",
        status_code=302
    )
