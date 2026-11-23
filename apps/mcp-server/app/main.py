from __future__ import annotations

import json
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.tools import TOOL_SCHEMAS, call_tool

app = FastAPI(title="RasenLoop MCP Tool Server", version="0.1.0")


def _check_auth(authorization: str | None) -> None:
    expected = os.environ.get("MCP_AUTH_TOKEN", "mcp-dev-token")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid MCP token")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tools")
def list_tools(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_auth(authorization)
    return {"tools": TOOL_SCHEMAS}


@app.post("/tools/{tool_name}")
async def invoke_tool(
    tool_name: str,
    request: Request,
    authorization: str | None = Header(default=None),
    x_chaos: str | None = Header(default=None),
) -> Any:
    _check_auth(authorization)
    body = await request.json()
    if x_chaos:
        body = {**body, "_chaos": x_chaos}
    return call_tool(tool_name, body)


@app.post("/mcp")
async def mcp_jsonrpc(
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Minimal MCP JSON-RPC surface for initialize / tools/list / tools/call."""
    _check_auth(authorization)
    payload = await request.json()
    method = payload.get("method")
    req_id = payload.get("id")
    params = payload.get("params") or {}

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "rasenloop-mcp", "version": "0.1.0"},
        }
    elif method == "tools/list":
        result = {"tools": TOOL_SCHEMAS}
    elif method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            data = call_tool(name, arguments)
            result = {"content": [{"type": "text", "text": json.dumps(data)}], "isError": False}
        except HTTPException as exc:
            result = {
                "content": [{"type": "text", "text": json.dumps(exc.detail)}],
                "isError": True,
            }
    elif method == "notifications/initialized":
        return JSONResponse({"jsonrpc": "2.0", "result": {}})
    else:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        )

    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result})
