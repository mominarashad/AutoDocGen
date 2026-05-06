import httpx

GITHUB_API = "https://api.github.com"


async def fetch_user_repos(access_token: str):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json"
    }

    async with httpx.AsyncClient() as client:
        res = await client.get(f"{GITHUB_API}/user/repos", headers=headers)

    return res.json()


# =========================
# RECURSIVE FILE FETCH (IMPORTANT)
# =========================
async def fetch_repo_contents(access_token: str, owner: str, repo: str, path=""):

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json"
    }

    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"

    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)

    data = res.json()

    result = []

    for item in data:

        # folder → recurse
        if item["type"] == "dir":
            sub = await fetch_repo_contents(
                access_token,
                owner,
                repo,
                item["path"]
            )
            result.extend(sub)

        # file → include content
        elif item["type"] == "file":
            result.append({
                "path": item["path"],
                "url": item["html_url"]
            })

    return result
