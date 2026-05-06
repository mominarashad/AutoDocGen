from app.models.slack_model import get_slack_token
from app.services.slack_service import fetch_channel_messages, join_channel


async def run_slack_workflow(user_id: str, team_id: str, channel_id: str, db):

    token = await get_slack_token(user_id, team_id, db)

    print("🧪 SLACK WORKFLOW START")
    print("USER:", user_id)
    print("TEAM:", team_id)
    print("CHANNEL:", channel_id)

    if not token:
        return {
            "status": "error",
            "message": "Slack token not found"
        }

    # Step 1: Fetch messages
    res = await fetch_channel_messages(token, channel_id)

    # Step 2: Join if not in channel
    if res.get("error") == "not_in_channel":
        join_res = await join_channel(token, channel_id)

        if not join_res.get("ok"):
            return {
                "status": "error",
                "message": "Bot failed to join channel",
                "debug": join_res
            }

        res = await fetch_channel_messages(token, channel_id)

    # Step 3: Final validation
    if not res.get("ok"):
        return {
            "status": "error",
            "message": res.get("error", "fetch failed"),
            "debug": res
        }

    messages = res.get("messages", [])

    conversation = "\n".join(
        f"{m.get('user', 'unknown')}: {m.get('text', '')}"
        for m in messages if m.get("text")
    )

    return {
        "status": "success",
        "source": "slack",
        "channel_id": channel_id,
        "conversation": conversation,
        "messages": messages
    }
