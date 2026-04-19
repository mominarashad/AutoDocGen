from app.models.slack_model import get_slack_token
from app.services.slack_service import fetch_channel_messages, join_channel


async def run_slack_workflow(user_id: str, team_id: str, channel_id: str, db):
    """
    Clean Slack workflow:
    - get token
    - ensure bot in channel
    - fetch messages
    - retry once if needed
    """

    # =========================
    # TOKEN
    # =========================
    token = await get_slack_token(user_id, team_id, db)

    print("🧪 SLACK WORKFLOW START")
    print("USER:", user_id)
    print("TEAM:", team_id)
    print("CHANNEL:", channel_id)
    print("TOKEN EXISTS:", bool(token))

    if not token:
        return {
            "status": "error",
            "message": "Slack token not found"
        }

    # =========================
    # STEP 1: FETCH MESSAGES
    # =========================
    res = await fetch_channel_messages(token, channel_id)
    print("📥 FIRST FETCH RESPONSE:", res)

    # =========================
    # STEP 2: JOIN IF NEEDED
    # =========================
    if res.get("error") == "not_in_channel":

        print("⚠️ Bot not in channel → trying join")

        join_res = await join_channel(token, channel_id)
        print("🤝 JOIN RESPONSE:", join_res)

        if not join_res.get("ok"):
            return {
                "status": "error",
                "message": "Bot failed to join channel",
                "debug": join_res
            }

        # retry fetch
        res = await fetch_channel_messages(token, channel_id)
        print("📥 RETRY FETCH RESPONSE:", res)

    if not res.get("ok"):
        return {
            "status": "error",
            "message": res.get("error", "fetch failed"),
            "debug": res
        }

    messages = res.get("messages", [])

    print("📊 MESSAGE COUNT:", len(messages))

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
