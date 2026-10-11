"""FastAPI backend for the Campus Customs dashboard.

Run from this folder:  uvicorn main:app --reload --port 8000

This file is a thin layer. The agents live in team.py, and every shop fact or
database change goes through the MCP server (team.mcp_server). The only direct
file work here is the reset, which copies the original database over the working copy.
"""

import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import audit
import team
from config import PROJECT_ROOT

logger = logging.getLogger("campus_customs")

ORIGINAL_DB = PROJECT_ROOT / "data" / "campus_customs.db"  # never written to
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"

# Only one agent run (or reset) at a time. Agents handle shared cash, so we avoid races.
busy = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with team.mcp_server:  # one MCP server process for the whole API
        yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # the React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


async def mcp(tool: str, **args: Any) -> Any:
    """Call one MCP tool. This is the only way the API reads or changes shop data."""
    try:
        result = await team.mcp_server.direct_call_tool(tool, args)
    except Exception as exc:
        logger.error("MCP call %s failed: %s", tool, type(exc).__name__)
        raise HTTPException(502, detail={"error": "mcp_failure", "message": f"The shop data service failed on {tool}."})
    if isinstance(result, dict) and set(result) == {"result"}:
        return result["result"]  # list results come wrapped
    return result


# 1. Tickets ---------------------------------------------------------------------------------
@app.get("/tickets")
async def get_tickets():
    tickets = await mcp("list_tickets")
    accounting = await mcp("get_accounting_status")
    pending = accounting["pending_proposals"]
    return [
        {
            **t,
            "resolved": t["status"] == "resolved",
            "pending_payments": [p for p in pending if p["ticket_id"] == t["id"]],
        }
        for t in tickets
    ]


# 2. Run the agent team on a ticket -----------------------------------------------------------
@app.post("/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int = Path(ge=1)):
    ticket = await mcp("get_ticket", ticket_id=ticket_id)
    if not ticket.get("found"):
        raise HTTPException(404, detail={"error": "ticket_not_found", "message": f"No ticket {ticket_id}."})
    if ticket["status"] == "resolved":
        raise HTTPException(409, detail={"error": "ticket_resolved", "message": f"Ticket {ticket_id} is already resolved."})
    if busy.locked():
        raise HTTPException(409, detail={"error": "busy", "message": "Another ticket run or reset is in progress."})
    async with busy:
        try:
            decision = await team.run_ticket(ticket_id)
        except Exception as exc:
            logger.error("Agent run for ticket %s failed: %s", ticket_id, type(exc).__name__)
            raise HTTPException(502, detail={"error": "agent_failure", "message": team.safe_error(exc)})
    return decision.model_dump()


@app.post("/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: int = Path(ge=1)):
    """A human closes a ticket once nothing is waiting on a payment approval."""
    ticket = await mcp("get_ticket", ticket_id=ticket_id)
    if not ticket.get("found"):
        raise HTTPException(404, detail={"error": "ticket_not_found", "message": f"No ticket {ticket_id}."})
    if ticket["status"] == "resolved":
        raise HTTPException(409, detail={"error": "ticket_resolved", "message": f"Ticket {ticket_id} is already resolved."})
    if busy.locked():
        raise HTTPException(409, detail={"error": "busy", "message": "An agent run or reset is in progress; try again shortly."})
    accounting = await mcp("get_accounting_status")
    if any(p["ticket_id"] == ticket_id for p in accounting["pending_proposals"]):
        raise HTTPException(409, detail={"error": "payment_pending", "message": "A payment for this ticket still needs approval."})
    result = await mcp("update_ticket_status", ticket_id=ticket_id, status="resolved",
                       note="Marked resolved on the dashboard.", set_by="Human")
    if not result.get("ok"):
        raise HTTPException(422, detail={"error": "invalid", "message": result["error"]})
    audit.log_step(agent="human_approval", ticket_id=ticket_id, status="finished",
                   tool="update_ticket_status", summary="ticket marked resolved by a human")
    return result


@app.get("/drafts")
async def get_drafts(ticket_id: int | None = Query(None, ge=1)):
    """Customer message drafts, so a person can read and review them. Nothing here sends them."""
    drafts = await mcp("list_customer_drafts", **({"ticket_id": ticket_id} if ticket_id else {}))
    return [{**d, "sent": False} for d in drafts]


# 3. Recent agent activity --------------------------------------------------------------------
@app.get("/activity")
async def get_activity(
    limit: int = Query(40, ge=1, le=200),
    ticket_id: int | None = Query(None, ge=1),
):
    """steps = audit trail (tool calls, delegations); messages = what each agent said."""
    return {
        "running": busy.locked(),
        "steps": audit.read_recent(audit.AUDIT_PATH, limit, ticket_id),
        "messages": audit.read_recent(audit.MESSAGES_PATH, limit, ticket_id),
    }


# 4. Human approval of a payment or purchase --------------------------------------------------
class ApproveRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=80, description="Who clicked approve")


ERROR_STATUS = {"not_found": 404, "not_pending": 409, "insufficient_cash": 409, "invalid": 422}


@app.post("/payments/{proposal_id}/approve")
async def approve_payment(body: ApproveRequest, proposal_id: int = Path(ge=1)):
    """Executes a pending proposal. All checks and updates happen inside the MCP tool,
    in one transaction, so a repeated or invalid request changes nothing."""
    if busy.locked():
        raise HTTPException(409, detail={"error": "busy", "message": "An agent run or reset is in progress; try again shortly."})
    result = await mcp("execute_payment", proposal_id=proposal_id, approved_by=body.approved_by)
    if not result.get("ok"):
        code = result.get("code", "invalid")
        raise HTTPException(ERROR_STATUS.get(code, 422), detail={"error": code, "message": result["error"]})
    audit.log_step(
        agent="human_approval",
        ticket_id=result.get("ticket_id") or 0,
        status="finished",
        tool="execute_payment",
        summary=f"proposal {proposal_id} ({result['kind']} {result['ref_id']}) paid ${result['amount']:.2f}; "
        f"balance now ${result['new_balance']:.2f}",
    )
    return result


# 5. Cash balance -----------------------------------------------------------------------------
@app.get("/cash")
async def get_cash():
    accounting = await mcp("get_accounting_status")
    checking = next((a for a in accounting["cash_accounts"] if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, detail={"error": "account_not_found", "message": "No checking account."})
    return {
        "account": "checking",
        "balance": checking["balance"],
        "pending_proposed": checking["pending_proposed"],
        "available": checking["available"],
        "as_of": accounting["today"],
        "pending_proposals": accounting["pending_proposals"],
    }


# 6. Reset the working database ---------------------------------------------------------------
@app.post("/reset")
async def reset_database():
    """Restore data/campus_customs_new.db from the untouched original. The original is
    opened read-only, so it cannot be changed. The audit trail is kept."""
    if busy.locked():
        raise HTTPException(409, detail={"error": "busy", "message": "An agent run is in progress; try again shortly."})
    async with busy:
        if ORIGINAL_DB.resolve() == WORKING_DB.resolve():
            raise HTTPException(500, detail={"error": "bad_config", "message": "Original and working paths are the same."})
        try:
            src = sqlite3.connect(f"file:{ORIGINAL_DB.as_posix()}?mode=ro", uri=True)
            dst = sqlite3.connect(WORKING_DB)
            try:
                src.backup(dst)  # replaces everything in the working copy, including agent tables
            finally:
                dst.close()
                src.close()
        except sqlite3.Error as exc:
            logger.error("Reset failed: %s", type(exc).__name__)
            raise HTTPException(500, detail={"error": "reset_failed", "message": "Could not restore the working database."})
    audit.log_step(agent="system", ticket_id=0, status="finished", tool="reset", summary="working database restored from original")
    return {"ok": True, "message": "Working database restored from the original."}
