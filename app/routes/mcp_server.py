from mcp.server.fastmcp import FastMCP
import httpx
import json

mcp = FastMCP("autodocgen")

BASE_URL = "https://autodocgen-production-f5de.up.railway.app"


# ---------------------------
# helper calling your API
# ---------------------------
async def call_backend(tool, arguments):
    async with httpx.AsyncClient(timeout=120) as client:
        res = await client.post(
            f"{BASE_URL}/mcp/execute",
            json={
                "tool": tool,
                "arguments": arguments
            }
        )
        return res.json().get("result")


# ---------------------------
# MCP TOOLS
# ---------------------------
@mcp.tool()
async def generate_doc_from_trello(user_id: str, board_id: str, template: str, headings: list[str] = []):
    return await call_backend("generate_doc_from_trello", locals())


@mcp.tool()
async def generate_doc_from_slack(user_id: str, channel_id: str, team_id: str, template: str, headings: list[str] = []):
    return await call_backend("generate_doc_from_slack", locals())


@mcp.tool()
async def generate_doc_from_github(user_id: str, repo_owner: str, repo_name: str, template: str, headings: list[str] = []):
    return await call_backend("generate_doc_from_github", locals())


@mcp.tool()
async def get_generated_documents(user_id: str):
    return await call_backend("get_generated_documents", locals())


@mcp.tool()
async def get_subscription_status(user_id: str):
    return await call_backend("get_subscription_status", locals())


@mcp.tool()
async def list_templates():
    return await call_backend("list_templates", {})


# ---------------------------
# IMPORTANT: SSE APP FOR RAILWAY
# ---------------------------
app = mcp.sse_app()
