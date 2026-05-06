from datetime import datetime

def get_github_token_collection(db):
    return db["github_tokens"]


def get_github_repo_collection(db):
    return db["github_repos"]


async def save_github_token(db, user_id, token_data):
    col = get_github_token_collection(db)

    await col.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "access_token": token_data["access_token"],
                "scope": token_data.get("scope"),
                "token_type": token_data.get("token_type"),
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )


async def get_github_token(db, user_id):
    col = get_github_token_collection(db)
    return await col.find_one({"user_id": user_id})


async def save_github_repo(db, user_id, repo):

    # 🔥 safety guard
    if not isinstance(repo, dict):
        raise ValueError("Repo must be a dictionary")

    owner = repo.get("owner", {})
    if isinstance(owner, str):
        owner = {"login": owner}

    col = get_github_repo_collection(db)

    await col.update_one(
        {"user_id": user_id, "repo_id": repo.get("id")},
        {
            "$set": {
                "repo_id": repo.get("id"),
                "repo_name": repo.get("name"),
                "repo_full_name": repo.get("full_name"),
                "repo_owner": owner.get("login"),
                "default_branch": repo.get("default_branch", "main"),
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )

async def get_user_repos(db, user_id):
    col = get_github_repo_collection(db)

    repos = []
    cursor = col.find({"user_id": user_id})

    async for r in cursor:
        repos.append(r)

    return repos
