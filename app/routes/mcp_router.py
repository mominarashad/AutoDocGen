from fastapi import APIRouter, Request
import json
import httpx

router = APIRouter(prefix="/mcp", tags=["MCP"])

BACKEND_URL = "https://autodocgen-production-f5de.up.railway.app"


# ======================================================
# MCP MANIFEST — tells clients what tools exist
# ======================================================
@router.get("/manifest")
async def get_manifest():
    return {
        "name": "autodocgen",
        "version": "1.0.0",
        "description": "AI-powered document generation from Trello, Slack and GitHub",
        "tools": [
            {
                "name": "generate_doc_from_trello",
                "description": "Generate professional document from a Trello board",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "board_id": {"type": "string"},
                        "template": {
                            "type": "string",
                            "enum": [
                                "srs",
                                "sprintreport",
                                "wbs",
                                "testcase",
                                "readme",
                                "usermanual",
                                "api"
                            ]
                        },
                        "headings": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["user_id", "board_id", "template"]
                }
            },
            {
                "name": "generate_doc_from_slack",
                "description": "Generate professional document from a Slack channel",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "channel_id": {"type": "string"},
                        "team_id": {"type": "string"},
                        "template": {"type": "string"},
                        "headings": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": [
                        "user_id",
                        "channel_id",
                        "team_id",
                        "template"
                    ]
                }
            },
            {
                "name": "generate_doc_from_github",
                "description": "Generate professional document from a GitHub repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "repo_owner": {"type": "string"},
                        "repo_name": {"type": "string"},
                        "template": {"type": "string"},
                        "headings": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": [
                        "user_id",
                        "repo_owner",
                        "repo_name",
                        "template"
                    ]
                }
            },
            {
                "name": "get_generated_documents",
                "description": "Get all previously generated documents for a user",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "get_subscription_status",
                "description": "Check subscription plan and document usage",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "list_templates",
                "description": "List all available document templates",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
    }


# ======================================================
# HELPER — STREAM DOCUMENT GENERATION
# ======================================================
async def stream_document_generation(client, payload):
    final_doc = ""

    async with client.stream(
        "POST",
        f"{BACKEND_URL}/workflow/start-stream",
        json=payload
    ) as res:

        async for line in res.aiter_lines():

            if not line:
                continue

            if line.startswith("data:"):
                try:
                    event = json.loads(line[5:].strip())

                    if event.get("type") == "done":
                        final_doc = event.get("data", "")

                    elif event.get("type") == "interrupt":
                        val = event.get("data", {}).get("value", {})
                        final_doc = val.get("final_doc", "")

                except Exception:
                    continue

    return final_doc or "Document generation failed"


# ======================================================
# MCP TOOL EXECUTOR — single endpoint for all tools
# ======================================================
@router.post("/execute")
async def execute_tool(request: Request, payload: dict):

    tool_name = payload.get("tool")
    arguments = payload.get("arguments", {})

    async with httpx.AsyncClient(timeout=120) as client:

        # ==================================================
        # GENERATE FROM TRELLO
        # ==================================================
        if tool_name == "generate_doc_from_trello":

            user_id = arguments["user_id"]
            board_id = arguments["board_id"]
            template = arguments["template"]
            headings = arguments.get("headings", [])

            final_doc = await stream_document_generation(
                client,
                {
                    "user_id": user_id,
                    "project_id": board_id,
                    "template": template,
                    "source": "trello",
                    "selected_headings": headings,
                    "pdf_headings": headings
                }
            )

            return {"result": final_doc}

        # ==================================================
        # GENERATE FROM SLACK
        # ==================================================
        elif tool_name == "generate_doc_from_slack":

            user_id = arguments["user_id"]
            channel_id = arguments["channel_id"]
            team_id = arguments["team_id"]
            template = arguments["template"]
            headings = arguments.get("headings", [])

            final_doc = await stream_document_generation(
                client,
                {
                    "user_id": user_id,
                    "project_id": channel_id,
                    "template": template,
                    "source": "slack",
                    "team_id": team_id,
                    "selected_headings": headings,
                    "pdf_headings": headings
                }
            )

            return {"result": final_doc}

        # ==================================================
        # GENERATE FROM GITHUB
        # ==================================================
        elif tool_name == "generate_doc_from_github":

            user_id = arguments["user_id"]
            repo_owner = arguments["repo_owner"]
            repo_name = arguments["repo_name"]
            template = arguments["template"]
            headings = arguments.get("headings", [])

            final_doc = await stream_document_generation(
                client,
                {
                    "user_id": user_id,
                    "project_id": f"{repo_owner}/{repo_name}",
                    "template": template,
                    "source": "github",
                    "selected_headings": headings,
                    "pdf_headings": headings
                }
            )

            return {"result": final_doc}

        # ==================================================
        # GET GENERATED DOCUMENTS
        # ==================================================
        elif tool_name == "get_generated_documents":

            user_id = arguments["user_id"]

            res = await client.get(
                f"{BACKEND_URL}/generated-docs/all",
                params={"user_id": user_id}
            )

            docs = res.json().get("documents", [])

            if not docs:
                return {"result": "No documents found"}

            summary = "\n\n".join([
                (
                    f"Template: {d.get('template_name', 'N/A')} | "
                    f"Project: {d.get('project_name', 'N/A')} | "
                    f"Version: {d.get('version', 'N/A')} | "
                    f"Source: {d.get('source', 'N/A')}"
                )
                for d in docs
            ])

            return {"result": summary}

        # ==================================================
        # SUBSCRIPTION STATUS
        # ==================================================
        elif tool_name == "get_subscription_status":

            user_id = arguments["user_id"]

            res = await client.get(
                f"{BACKEND_URL}/subscription/status",
                params={"user_id": user_id}
            )

            data = res.json()

            result = (
                f"Plan: {data.get('plan', 'free').upper()}\n"
                f"Docs Used: {data.get('docs_used', 0)}\n"
                f"Limit: "
                f"{'Unlimited' if data.get('unlimited') else data.get('docs_limit')}\n"
                f"Period End: {data.get('period_end', 'N/A')}"
            )

            return {"result": result}

        # ==================================================
        # LIST TEMPLATES
        # ==================================================
        elif tool_name == "list_templates":

            return {
                "result": (
                    "Available templates:\n"
                    "• srs — Software Requirements Specification\n"
                    "• sprintreport — Sprint Report\n"
                    "• wbs — Work Breakdown Structure\n"
                    "• testcase — Test Case Document\n"
                    "• readme — README File\n"
                    "• usermanual — User Manual\n"
                    "• api — API Documentation"
                )
            }

        # ==================================================
        # UNKNOWN TOOL
        # ==================================================
        else:
            return {
                "error": f"Unknown tool: {tool_name}"
            }
