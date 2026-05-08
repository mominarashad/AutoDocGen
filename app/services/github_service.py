#github_service.py
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
    print("WEBHOOK TARGET URL:", url)

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

async def create_github_webhook(token, owner, repo, webhook_url, secret):

    # 🔥 DEBUG (TEMP - keep until fixed)
    print("CREATE WEBHOOK FOR:", owner, repo)

    url = f"{GITHUB_API}/repos/{owner}/{repo}/hooks"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "name": "web",
        "active": True,
        "events": ["push", "pull_request", "release"],
        "config": {
            "url": webhook_url,
            "content_type": "json",
            "secret": secret
        }
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=payload, headers=headers)

    # 🔥 IMPORTANT DEBUG
    if res.status_code not in [200, 201]:
        print("❌ GitHub Webhook Error:", res.status_code, res.text)
        raise Exception(f"Webhook creation failed: {res.text}")

    return res.json()

async def get_existing_webhooks(token, owner, repo):

    url = f"{GITHUB_API}/repos/{owner}/{repo}/hooks"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception(f"Failed to fetch webhooks: {res.text}")

    return res.json()
