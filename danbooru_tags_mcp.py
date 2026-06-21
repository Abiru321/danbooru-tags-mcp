"""
Danbooru tag-lookup MCP server.

Exposes one tool, `search_tags`, that queries Danbooru's public tag API so an
LLM (e.g. Grok) emits tags that actually exist instead of inventing them.

Run:   python danbooru_tags_mcp.py
Serves Streamable HTTP at http://127.0.0.1:8000/mcp
"""
import os
import httpx
from mcp.server.fastmcp import FastMCP

# Render (and most hosts) require binding 0.0.0.0 and listening on the port
# they assign via the PORT env var. Locally there's no PORT set, so it falls
# back to 8000.
mcp = FastMCP(
    "danbooru-tags",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
)

BASE = "https://danbooru.donmai.us"
CATEGORY = {0: "general", 1: "artist", 3: "copyright", 4: "character", 5: "meta"}


@mcp.tool()
async def search_tags(query: str, limit: int = 10) -> list[dict]:
    """Look up real Danbooru tags matching a partial name, ordered by how many
    posts use them. Call this before writing tags so the prompt is grounded in
    tags that actually exist. Returns name, post_count, and category for each.

    Args:
        query: Partial tag text, e.g. "blue_ey" or "cherry".
        limit: Max tags to return (1-50).
    """
    limit = max(1, min(limit, 50))
    params = {
        "search[name_matches]": f"*{query}*",  # f"{query}*" for prefix-only
        "search[order]": "count",
        "limit": limit,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{BASE}/tags.json",
            params=params,
            headers={"User-Agent": "grok-tag-connector/0.1"},
        )
        r.raise_for_status()
        data = r.json()
    return [
        {
            "name": t["name"],
            "post_count": t["post_count"],
            "category": CATEGORY.get(t["category"], "unknown"),
        }
        for t in data
    ]


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
