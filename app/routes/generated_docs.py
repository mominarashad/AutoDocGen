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

@router.get("/versions")
async def get_versions(request: Request, user_id: str, project_id: str, template_name: str):

    db = request.app.state.db

    cursor = db["generated_docs"].find({
        "user_id": user_id,
        "project_id": project_id,
        "template_name": template_name
    }).sort("version", -1)

    versions = []

    async for doc in cursor:
        versions.append({
            "version": doc["version"],
            "content": doc.get("generated_docs", ""),  # ✅ FULL DOCUMENT FIX
            "created_at": doc.get("created_at"),
            "is_latest": doc.get("is_latest", False)
        })

    return {"versions": versions}

@router.get("/latest")
async def get_latest(request: Request, user_id: str, project_id: str, template_name: str):

    db = request.app.state.db

    doc = await db["generated_docs"].find_one(
        {
            "user_id": user_id,
            "project_id": project_id,
            "template_name": template_name,
            "is_latest": True
        }
    )

    if not doc:
        return {"status": "not_found"}

    return {
        "status": "success",
        "version": doc.get("version"),
        "content": doc.get("generated_docs")
    }

@router.post("/restore")
async def restore_version(request: Request, payload: dict):

    db = request.app.state.db

    user_id = payload["user_id"]
    project_id = payload["project_id"]
    template_name = payload["template_name"]
    version = payload["version"]

    collection = db["generated_docs"]

    # 1. find selected version
    old_doc = await collection.find_one({
        "user_id": user_id,
        "project_id": project_id,
        "template_name": template_name,
        "version": version
    })

    if not old_doc:
        return {"status": "not_found"}

    # 2. unset old latest
    await collection.update_many(
        {
            "user_id": user_id,
            "project_id": project_id,
            "template_name": template_name
        },
        {"$set": {"is_latest": False}}
    )

    # 3. create NEW latest version (promotion)
    new_version = await collection.count_documents({
        "user_id": user_id,
        "project_id": project_id,
        "template_name": template_name
    }) + 1

    new_doc = {
        **old_doc,
        "_id": None,
        "version": new_version,
        "is_latest": True
    }

    await collection.insert_one(new_doc)

    return {
        "status": "restored",
        "new_version": new_version
    }
