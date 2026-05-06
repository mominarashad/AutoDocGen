import os
import httpx
from fastapi import APIRouter, Request
from app.models.github_model import save_github_token

router = APIRouter()

CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")


@router.get("/github/connect")
async def github_connect(user_id: str):

    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&scope=repo read:user"
        f"&redirect_uri={REDIRECT_URI}?user_id={user_id}"
    )

    return {"auth_url": url}


@router.get("/github/callback")
async def github_callback(request: Request, code: str, user_id: str):

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI
            }
        )

    token_data = res.json()

    await save_github_token(request.app.state.db, user_id, token_data)

    return {"status": "success"}
