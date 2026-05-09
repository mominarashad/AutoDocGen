from datetime import datetime
import secrets


async def create_workspace(owner_id: str, name: str, db) -> dict:
    workspace = {
        "owner_id": owner_id,
        "name": name,
        "invite_code": secrets.token_urlsafe(8),
        "members": [owner_id],
        "created_at": datetime.utcnow()
    }
    result = await db["workspaces"].insert_one(workspace)
    workspace["_id"] = str(result.inserted_id)
    return workspace


async def get_workspace_by_owner(owner_id: str, db) -> dict:
    return await db["workspaces"].find_one({"owner_id": owner_id})


async def get_workspace_by_member(user_id: str, db) -> dict:
    return await db["workspaces"].find_one({"members": user_id})


async def join_workspace_by_code(user_id: str, invite_code: str, db) -> tuple:
    workspace = await db["workspaces"].find_one({"invite_code": invite_code})

    if not workspace:
        return False, "Invalid invite code"

    if user_id in workspace["members"]:
        return False, "You are already a member of this workspace"

    if len(workspace["members"]) >= 5:
        return False, "Workspace is full (maximum 5 members)"

    # Check owner still has team plan
    owner_sub = await db["subscriptions"].find_one(
        {"user_id": workspace["owner_id"]}
    )
    if not owner_sub or owner_sub.get("plan") != "team":
        return False, "Workspace owner does not have an active Team plan"

    await db["workspaces"].update_one(
        {"invite_code": invite_code},
        {"$push": {"members": user_id}}
    )

    return True, "Successfully joined the workspace"


async def remove_member(owner_id: str, member_id: str, db) -> bool:
    workspace = await db["workspaces"].find_one({"owner_id": owner_id})

    if not workspace:
        return False

    if member_id == owner_id:
        return False

    if member_id not in workspace["members"]:
        return False

    await db["workspaces"].update_one(
        {"owner_id": owner_id},
        {"$pull": {"members": member_id}}
    )
    return True
