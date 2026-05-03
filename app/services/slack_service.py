import httpx


async def join_channel(token: str, channel_id: str):
    async with httpx.AsyncClient() as client:
        return (await client.post(
            "https://slack.com/api/conversations.join",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": channel_id}
        )).json()


async def fetch_channel_messages(token: str, channel_id: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": f"Bearer {token}"},
            params={"channel": channel_id, "limit": 100}
        )
        data = res.json()

        # 🔥 SAME LOGIC AS YOUR WORKING WORKFLOW
        if not data.get("ok") and data.get("error") == "not_in_channel":

            join_res = await join_channel(token, channel_id)

            if not join_res.get("ok"):
                return {"ok": False, "messages": []}

            # retry after join
            res = await client.get(
                "https://slack.com/api/conversations.history",
                headers={"Authorization": f"Bearer {token}"},
                params={"channel": channel_id, "limit": 100}
            )
            data = res.json()

        if not data.get("ok"):
            return {"ok": False, "messages": []}

        return data


async def fetch_channels(token: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://slack.com/api/conversations.list",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "limit": 200,
                "types": "public_channel,private_channel"
            }
        )
        return res.json()

async def get_channel_name(token: str, channel_id: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://slack.com/api/conversations.info",
            headers={"Authorization": f"Bearer {token}"},
            params={"channel": channel_id}
        )

        data = res.json()

        if not data.get("ok"):
            return "Unknown Channel"

        return data["channel"]["name"]
