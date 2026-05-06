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


async def fetch_repo_contents(access_token: str, owner: str, repo: str, path=""):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json"
    }

    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"

    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)

    return res.json()
