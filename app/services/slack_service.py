import httpx


async def join_channel(token: str, channel_id: str):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://slack.com/api/conversations.join",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": channel_id}
        )
    return res.json()


async def fetch_channel_messages(token: str, channel_id: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": f"Bearer {token}"},
            params={"channel": channel_id, "limit": 100}
        )
        return res.json()


async def run_slack_workflow(user_id, team_id, channel_id, db):

    token = await get_slack_token(user_id, team_id, db)

    if not token:
        return {"status": "error", "message": "No token"}

    res = await fetch_channel_messages(token, channel_id)

    if res.get("error") == "not_in_channel":

        join_res = await join_channel(token, channel_id)

        if not join_res.get("ok"):
            return {"status": "error", "message": "join failed"}

        res = await fetch_channel_messages(token, channel_id)

    if not res.get("ok"):
        return {"status": "error", "message": res.get("error")}

    messages = res.get("messages", [])

    conversation = "\n".join(
        f"{m.get('user','unknown')}: {m.get('text','')}"
        for m in messages if m.get("text")
    )

    return {
        "status": "success",
        "conversation": conversation,
        "messages": messages
    }
