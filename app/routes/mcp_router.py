from mcp.server.fastmcp import FastMCP
import httpx
import json

mcp = FastMCP("autodocgen")

BACKEND_URL = "https://autodocgen-production-f5de.up.railway.app"


async def stream_document_generation(payload):
    final_doc = ""

    async with httpx.AsyncClient(timeout=120) as client:

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


@mcp.tool()
async def list_templates():

    return [
        "srs",
        "sprintreport",
        "wbs",
        "testcase",
        "readme",
        "usermanual",
        "api"
    ]


@mcp.tool()
async def generate_doc_from_trello(
    user_id: str,
    board_id: str,
    template: str
):

    return await stream_document_generation({
        "user_id": user_id,
        "project_id": board_id,
        "template": template,
        "source": "trello"
    })


app = mcp.sse_app()
