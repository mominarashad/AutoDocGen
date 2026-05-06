from fastapi import APIRouter, Request
from app.models.github_model import get_github_token, save_github_repo
from app.services.github_service import fetch_user_repos, fetch_repo_contents

router = APIRouter()


# =========================
# GET USER REPOS
# =========================
@router.get("/github/repos")
async def get_repos(user_id: str, request: Request):

    db = request.app.state.db

    token_doc = await get_github_token(db, user_id)

    if not token_doc:
        return {"error": "GitHub not connected"}

    repos = await fetch_user_repos(token_doc["access_token"])

    return {"repos": repos}


# =========================
# SELECT REPO
# =========================
@router.post("/github/select-repo")
async def select_repo(request: Request, payload: dict):

    db = request.app.state.db
    user_id = payload["user_id"]
    repo = payload["repo"]

    await save_github_repo(db, user_id, repo)

    return {"status": "repo saved"}


# =========================
# GET REPO CONTEXT (IMPORTANT)
# =========================
@router.get("/github/repo-context")
async def repo_context(user_id: str, request: Request):

    db = request.app.state.db

    token_doc = await get_github_token(db, user_id)
    repo_doc = await db["github_repos"].find_one({"user_id": user_id})

    if not token_doc or not repo_doc:
        return {"error": "missing data"}

    owner = repo_doc["repo_owner"]
    repo = repo_doc["repo_name"]

    access_token = token_doc["access_token"]

    # fetch root files
    contents = await fetch_repo_contents(access_token, owner, repo, "")

    return {
        "repo": repo,
        "files": contents
    }
