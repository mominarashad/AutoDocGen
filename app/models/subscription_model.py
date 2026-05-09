from datetime import datetime, timedelta
from enum import Enum


class PlanType(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    TEAM = "team"


PLAN_LIMITS = {
    PlanType.FREE:    {"docs": 10,   "monthly": False, "price": 0},
    PlanType.STARTER: {"docs": 50,   "monthly": True,  "price": 9},
    PlanType.PRO:     {"docs": -1,   "monthly": True,  "price": 29},  # -1 = unlimited
    PlanType.TEAM:    {"docs": -1,   "monthly": True,  "price": 49},
}


async def get_user_subscription(user_id: str, db) -> dict:
    sub = await db["subscriptions"].find_one({"user_id": user_id})

    if not sub:
        # Auto-create free plan on first check
        sub = {
            "user_id": user_id,
            "plan": PlanType.FREE,
            "docs_used": 0,
            "period_start": datetime.utcnow(),
            "period_end": None,
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        await db["subscriptions"].insert_one(sub)

    return sub


async def can_generate_doc(user_id: str, db) -> tuple[bool, str]:
    """
    Returns (allowed: bool, reason: str)
    """
    sub = await get_user_subscription(user_id, db)
    plan = sub.get("plan", PlanType.FREE)
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS[PlanType.FREE])

    # Unlimited plan
    if limit["docs"] == -1:
        return True, "ok"

    # Reset monthly counter if period expired
    if limit["monthly"] and sub.get("period_end"):
        if datetime.utcnow() > sub["period_end"]:
            await db["subscriptions"].update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "docs_used": 0,
                        "period_start": datetime.utcnow(),
                        "period_end": datetime.utcnow() + timedelta(days=30)
                    }
                }
            )
            return True, "ok"

    docs_used = sub.get("docs_used", 0)

    if docs_used >= limit["docs"]:
        return False, f"Limit reached. You've used {docs_used}/{limit['docs']} docs on the {plan} plan. Upgrade to generate more."

    return True, "ok"


async def increment_doc_count(user_id: str, db):
    await db["subscriptions"].update_one(
        {"user_id": user_id},
        {"$inc": {"docs_used": 1}}
    )


async def upgrade_plan(user_id: str, new_plan: str, db):
    limit = PLAN_LIMITS.get(new_plan, PLAN_LIMITS[PlanType.FREE])

    update = {
        "plan": new_plan,
        "docs_used": 0,
        "period_start": datetime.utcnow(),
        "is_active": True
    }

    if limit["monthly"]:
        update["period_end"] = datetime.utcnow() + timedelta(days=30)

    await db["subscriptions"].update_one(
        {"user_id": user_id},
        {"$set": update},
        upsert=True
    )
