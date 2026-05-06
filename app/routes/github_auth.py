from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import os
import httpx

router = APIRouter(prefix="/github")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL")

# -------------------------
# STEP 1: CONNECT
# -------------------------
@router.get("/auth/connect")
async def github_connect(user_id: str):
    redirect_uri = f"{FRONTEND_URL}/github/callback"

    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=repo"
        f"&state={user_id}"
    )

    return RedirectResponse(url)


# -------------------------
# STEP 2: CALLBACK
# -------------------------
@router.get("/auth/callback")
async def github_callback(code: str, state: str, request: Request):

    token_url = "https://github.com/login/oauth/access_token"

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            token_url,
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
        )

    access_token = token_res.json().get("access_token")

    db = request.app.state.db

    await db.github_tokens.update_one(
        {"user_id": state},
        {"$set": {"access_token": access_token}},
        upsert=True
    )

    return RedirectResponse(f"{FRONTEND_URL}/github/repositories")
