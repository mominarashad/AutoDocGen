from fastapi import APIRouter, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(
    tags=["Generated Documents"]
)

# -------------------------------------------------
# Get ALL generated documents for a user (latest first)
# -------------------------------------------------
@router.get("/all")
async def get_all_generated_docs(request: Request, user_id: str):

    db = request.app.state.db
    collection = db["generated_docs"]

    docs_cursor = collection.find({"user_id": user_id})

    docs = []
    async for doc in docs_cursor:
        docs.append({
            "id": str(doc.get("_id", "")),
            "project_id": doc.get("project_id"),
            "template_name": doc.get("template_name"),
            "generated_docs": doc.get("generated_docs", ""),

            
            "project_name": doc.get("workspace_name")
                          or doc.get("project_name")
                          or doc.get("board_name")
                          or "Unknown Project",

            "created_at": str(doc.get("created_at", "")),
            "source": doc.get("source", "trello"),
            "team_id": doc.get("team_id"),
        })

    return {
        "status": "success",
        "count": len(docs),
        "documents": docs
    }
# -------------------------------------------------
# Get documents for a SPECIFIC BOARD (all versions)
# -------------------------------------------------
@router.get("/by-board")
async def get_docs_by_board(
    request: Request,
    user_id: str,
    project_id: str
):
    db: AsyncIOMotorDatabase = request.app.state.db
    collection = db["generated_docs"]

    cursor = collection.find(
        {
            "user_id": user_id,
            "project_id": project_id
        }
    ).sort("version", -1)

    docs = []
    async for doc in cursor:
        docs.append({
            "id": str(doc["_id"]),
            "template_name": doc.get("template_name", "").strip(),
            "version": doc.get("version", 1),
            "board_name": doc.get("board_name", "Unknown Board").strip(),
            "created_at": doc.get("created_at"),
            "generated_docs": doc.get("generated_docs", ""),  # ✅ Include content here too
        })

    return {
        "status": "success",
        "count": len(docs),
        "documents": docs
    }

@router.get("/result")
async def get_result(user_id: str, project_id: str, template_name: str, request: Request):

    db = request.app.state.db

    doc = await db["generated_docs"].find_one(
        {
            "user_id": user_id,
            "project_id": project_id,
            "template_name": template_name
        },
        sort=[("version", -1)]
    )

    if not doc:
        return {"status": "not_found"}

    return {
        "status": "success",
        "generated_docs": doc["generated_docs"]
    }
