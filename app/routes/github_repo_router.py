from fastapi import APIRouter, Request
from app.models.github_model import get_github_token, save_github_repo,save_github_webhook
from app.services.github_service import fetch_user_repos,create_github_webhook
from app.services.github_code_service import fetch_repo_tree, fetch_file
import os

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
# SELECT REPO (FIXED)
# =========================
@router.post("/github/select-repo")
async def select_repo(request: Request, payload: dict):

    db = request.app.state.db

    user_id = payload.get("user_id")
    repo = payload.get("repo")

    if not isinstance(repo, dict):
        return {"error": "Invalid repo format"}

    # -----------------------------
    # SAVE REPO
    # -----------------------------
    await save_github_repo(db, user_id, repo)

    # -----------------------------
    # GET TOKEN
    # -----------------------------
    token_doc = await get_github_token(db, user_id)

    if not token_doc:
        return {"error": "GitHub token missing"}

    token = token_doc["access_token"]

    owner = repo["owner"]["login"]
    repo_name = repo["name"]

    # -----------------------------
    # WEBHOOK SETTINGS
    # -----------------------------
    webhook_url = os.getenv("GITHUB_WEBHOOK_URL")
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")

    # -----------------------------
    # CREATE WEBHOOK
    # -----------------------------
    webhook = await create_github_webhook(
        token=token,
        owner=owner,
        repo=repo_name,
        webhook_url=webhook_url,
        secret=webhook_secret
    )

    # -----------------------------
    # SAVE WEBHOOK
    # -----------------------------
    await save_github_webhook(
        db=db,
        user_id=user_id,
        repo_id=repo["id"],
        webhook_data=webhook
    )

    return {
        "status": "repo_saved",
        "webhook_created": True,
        "webhook_id": webhook["id"]
    }


# =========================
# CODE CONTEXT (FOR LLM)
# =========================
@router.get("/github/repo-code-context")
async def get_repo_code_context(user_id: str, request: Request):

    db = request.app.state.db

    token_doc = await get_github_token(db, user_id)
    repo_doc = await db["github_repos"].find_one({"user_id": user_id})

    if not token_doc or not repo_doc:
        return {"error": "missing data"}

    token = token_doc["access_token"]
    owner = repo_doc["repo_owner"]
    repo = repo_doc["repo_name"]

    tree = await fetch_repo_tree(token, owner, repo)

    if not tree or "tree" not in tree:
        return {"error": "Could not fetch repo tree"}

    files = []

    allowed_ext = [".py", ".js", ".ts", ".java", ".go", ".md"]

    for item in tree["tree"]:

        if item["type"] != "blob":
            continue

        if not any(item["path"].endswith(ext) for ext in allowed_ext):
            continue

        if "node_modules" in item["path"]:
            continue

        try:
            content = await fetch_file(token, owner, repo, item["path"])

            files.append({
                "path": item["path"],
                "content": content[:6000]  # trim for LLM
            })

        except:
            continue

        if len(files) >= 25:
            break

    return {
        "repo": f"{owner}/{repo}",
        "files": files
    }
