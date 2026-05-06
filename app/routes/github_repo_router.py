from fastapi import APIRouter, Request
from app.models.github_model import get_github_token, save_github_repo
from app.services.github_service import fetch_user_repos

router = APIRouter()


@router.get("/github/repos")
async def get_repos(user_id: str, request: Request):

    token_doc = await get_github_token(request.app.state.db, user_id)

    if not token_doc:
        return {"error": "GitHub not connected"}

    repos = await fetch_user_repos(token_doc["access_token"])

    return {"repos": repos}


@router.post("/github/select-repo")
async def select_repo(request: Request, payload: dict):

    db = request.app.state.db
    user_id = payload["user_id"]
    repo = payload["repo"]

    await save_github_repo(db, user_id, repo)

    return {"status": "saved"}
