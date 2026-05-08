from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/notifications")
async def get_notifications(user_id: str, request: Request):

    db = request.app.state.db

    notifications = []

    cursor = (
        db["notifications"]
        .find({"user_id": user_id})
        .sort("created_at", -1)
        .limit(50)
    )

    async for n in cursor:

        n["_id"] = str(n["_id"])

        notifications.append(n)

    return {
        "notifications": notifications
    }
