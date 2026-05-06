import httpx
from app.models.slack_model import get_slack_token


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
        data = res.json()
        print("🔥 SLACK RESPONSE:", data)
        return data



