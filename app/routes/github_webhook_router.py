from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/webhooks/github")
async def github_webhook(request: Request):

    payload = await request.json()

    event = request.headers.get("X-GitHub-Event")

    if event == "push":

        repo = payload["repository"]["full_name"]

        print(f"🔥 PUSH EVENT in {repo}")

        # -----------------------------
        # TRIGGER YOUR WORKFLOW HERE
        # -----------------------------

    elif event == "pull_request":

        action = payload["action"]

        print(f"🔀 PR EVENT: {action}")

    elif event == "release":

        print("🚀 RELEASE EVENT")

    return {"status": "received"}
