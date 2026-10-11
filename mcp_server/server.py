import calendar
import sys
from datetime import date, timedelta
from pathlib import Path

from fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ensure_agent_tables, get_connection

mcp = FastMCP("Campus Customs")


@mcp.tool()
def get_inventory_status(sku: str, size: str | None = None) -> dict:
    """Look up stock levels and pricing for a SKU, optionally one size.

    Used to check whether a product requested on a ticket (e.g. a customer
    order or a bulk discount request) is actually in stock, and what it
    costs vs. sells for.
    """
    con = get_connection()
    try:
        pricing_row = con.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?",
            (sku,),
        ).fetchone()

        if size:
            stock_rows = con.execute(
                "SELECT size, qty, location FROM inventory WHERE sku = ? AND size = ?",
                (sku, size),
            ).fetchall()
        else:
            stock_rows = con.execute(
                "SELECT size, qty, location FROM inventory WHERE sku = ?",
                (sku,),
            ).fetchall()

        if not stock_rows and pricing_row is None:
            return {"sku": sku, "found": False}

        return {
            "sku": sku,
            "found": True,
            "pricing": dict(pricing_row) if pricing_row else None,
            "stock": [dict(row) for row in stock_rows],
        }
    finally:
        con.close()


@mcp.tool()
def get_vendor_status(vendor_id: int | None = None) -> list[dict]:
    """List vendors with their restock lead time and unpaid-invoice status.

    A vendor with any open invoice should not receive new restock orders
    until that invoice is paid. Used to decide where (and when) inventory
    can be reordered from.
    """
    con = get_connection()
    try:
        if vendor_id is not None:
            vendors = con.execute(
                "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?",
                (vendor_id,),
            ).fetchall()
        else:
            vendors = con.execute(
                "SELECT id, name, specialty, lead_days FROM vendors"
            ).fetchall()

        results = []
        for vendor in vendors:
            open_invoices = con.execute(
                "SELECT id, amount, due_date, description FROM invoices "
                "WHERE vendor_id = ? AND status = 'open'",
                (vendor["id"],),
            ).fetchall()
            results.append(
                {
                    "vendor_id": vendor["id"],
                    "name": vendor["name"],
                    "specialty": vendor["specialty"],
                    "lead_days": vendor["lead_days"],
                    "has_unpaid_invoice": len(open_invoices) > 0,
                    "unpaid_amount": sum(inv["amount"] for inv in open_invoices),
                    "open_invoices": [dict(inv) for inv in open_invoices],
                }
            )
        return results
    finally:
        con.close()


@mcp.tool()
def get_facilities_status() -> dict:
    """Get the shop's current date, cash balance, and lease/rent status.

    Used to check whether rent is due or overdue (against the shop's
    `date_today`, not the real calendar date) and whether the cash account
    can cover a rent payment.
    """
    con = get_connection()
    try:
        today_row = con.execute("SELECT date_today FROM desk").fetchone()
        today = date.fromisoformat(today_row["date_today"])

        cash_row = con.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'"
        ).fetchone()

        leases = con.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases"
        ).fetchall()

        lease_list = []
        for lease in leases:
            next_due = date.fromisoformat(lease["next_due"])
            lease_list.append(
                {
                    **dict(lease),
                    "days_until_due": (next_due - today).days,
                    "is_due_or_overdue": next_due <= today,
                }
            )

        return {
            "today": today_row["date_today"],
            "cash_account": dict(cash_row) if cash_row else None,
            "leases": lease_list,
        }
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Tools added in Problem 5 (tickets, accounting, restock math, drafts)
# ---------------------------------------------------------------------------

TICKET_COLUMNS = (
    "id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes, created_at"
)
TICKET_STATUSES = ("resolved", "awaiting_approval", "needs_investigation")


def _today(con) -> str:
    return con.execute("SELECT date_today FROM desk").fetchone()["date_today"]


def _pending_total(con, account: str) -> float:
    row = con.execute(
        "SELECT COALESCE(SUM(amount), 0) AS t FROM payment_proposals "
        "WHERE account = ? AND status = 'pending_approval'",
        (account,),
    ).fetchone()
    return row["t"]


@mcp.tool()
def list_tickets() -> list[dict]:
    """List every ticket with all its fields, whatever its status (open, resolved, ...)."""
    con = get_connection()
    try:
        rows = con.execute(f"SELECT {TICKET_COLUMNS} FROM tickets ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


@mcp.tool()
def list_open_tickets() -> list[dict]:
    """List tickets that are still open (id, type, subject, status only)."""
    con = get_connection()
    try:
        rows = con.execute(
            "SELECT id, type, subject, status FROM tickets WHERE status = 'open' ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


@mcp.tool()
def get_ticket(ticket_id: int) -> dict:
    """Get one ticket with every field (sku, size, qty, lease_id, invoice_id, notes)."""
    con = get_connection()
    try:
        row = con.execute(
            f"SELECT {TICKET_COLUMNS} FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return {"found": True, **dict(row)} if row else {"found": False, "ticket_id": ticket_id}
    finally:
        con.close()


@mcp.tool()
def get_accounting_status(invoice_id: int | None = None, sku: str | None = None) -> dict:
    """Cash, invoices, margin and pending payments.

    Returns each cash account with `pending_proposed` (money already
    earmarked by proposals waiting for human approval) and `available`
    (balance minus pending). Also returns open invoices (with days overdue
    against desk.date_today), optionally one invoice, and the unit margin
    for a SKU. `recent_payments` lists what has actually been paid (newest first), with the ticket
    and the reason (item and quantity) recorded when the payment was proposed.
    No revenue is modelled, so `available` is all the cash there is.
    """
    con = get_connection()
    try:
        ensure_agent_tables(con)
        today = _today(con)
        today_d = date.fromisoformat(today)

        accounts = []
        for a in con.execute("SELECT name, balance, date FROM cash_accounts").fetchall():
            pending = _pending_total(con, a["name"])
            accounts.append(
                {**dict(a), "pending_proposed": pending, "available": a["balance"] - pending}
            )

        if invoice_id is not None:
            inv_rows = con.execute(
                "SELECT id, vendor_id, amount, due_date, status, description FROM invoices WHERE id = ?",
                (invoice_id,),
            ).fetchall()
        else:
            inv_rows = con.execute(
                "SELECT id, vendor_id, amount, due_date, status, description FROM invoices "
                "WHERE status = 'open'"
            ).fetchall()
        invoices = []
        for r in inv_rows:
            d = dict(r)
            d["days_overdue"] = max((today_d - date.fromisoformat(r["due_date"])).days, 0)
            invoices.append(d)

        result = {
            "today": today,
            "cash_accounts": accounts,
            "invoices": invoices,
            "pending_proposals": [
                dict(r)
                for r in con.execute(
                    "SELECT id, kind, ref_id, amount, account, ticket_id FROM payment_proposals "
                    "WHERE status = 'pending_approval'"
                ).fetchall()
            ],
            # What has really been paid (the payments table), newest first. A proposal that is
            # no longer pending and shows up here was approved and executed.
            "recent_payments": [
                dict(r)
                for r in con.execute(
                    "SELECT p.id, p.kind, p.ref_id, p.amount, p.account, p.paid_at, "
                    "  (SELECT q.ticket_id FROM payment_proposals q WHERE q.status = 'executed' "
                    "     AND q.kind = p.kind AND q.ref_id = p.ref_id AND q.amount = p.amount "
                    "     ORDER BY q.id DESC LIMIT 1) AS ticket_id, "
                    "  (SELECT q.reason FROM payment_proposals q WHERE q.status = 'executed' "
                    "     AND q.kind = p.kind AND q.ref_id = p.ref_id AND q.amount = p.amount "
                    "     ORDER BY q.id DESC LIMIT 1) AS reason "
                    "FROM payments p ORDER BY p.id DESC LIMIT 10"
                ).fetchall()
            ],
        }
        if sku:
            p = con.execute(
                "SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
            ).fetchone()
            if p:
                margin = p["list_price"] - p["unit_cost"]
                result["margin"] = {
                    "sku": sku,
                    "unit_cost": p["unit_cost"],
                    "list_price": p["list_price"],
                    "unit_margin": margin,
                    "margin_pct": round(100 * margin / p["list_price"], 1),
                }
            else:
                result["margin"] = {"sku": sku, "found": False}
        return result
    finally:
        con.close()


@mcp.tool()
def estimate_restock(vendor_id: int, sku: str, qty: int) -> dict:
    """Restock math for ordering `qty` of `sku` from a vendor.

    Gives the earliest arrival date (desk.date_today + vendor lead_days),
    the estimated cost (unit_cost x qty) and whether the vendor is
    restricted because of an open (unpaid) invoice. If `restricted` is
    true no order may be placed with that vendor.
    """
    con = get_connection()
    try:
        vendor = con.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,)
        ).fetchone()
        price = con.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if vendor is None or price is None or qty <= 0:
            return {"ok": False, "error": "unknown vendor or sku, or qty not positive"}
        open_inv = con.execute(
            "SELECT id, amount FROM invoices WHERE vendor_id = ? AND status = 'open'",
            (vendor_id,),
        ).fetchall()
        today = date.fromisoformat(_today(con))
        return {
            "ok": True,
            "vendor_id": vendor_id,
            "vendor_name": vendor["name"],
            "sku": sku,
            "qty": qty,
            "estimated_cost": round(price["unit_cost"] * qty, 2),
            "lead_days": vendor["lead_days"],
            "earliest_arrival_if_ordered_today": (
                today + timedelta(days=vendor["lead_days"])
            ).isoformat(),
            "restricted": len(open_inv) > 0,
            "open_invoice_ids": [r["id"] for r in open_inv],
        }
    finally:
        con.close()


@mcp.tool()
def propose_payment(
    kind: str,
    ref_id: int,
    amount: float,
    reason: str,
    ticket_id: int | None = None,
    account: str = "checking",
) -> dict:
    """Prepare a payment for HUMAN approval. This never moves money.

    kind: 'invoice' (ref_id = invoice id, amount must equal the invoice),
    'rent' (ref_id = lease id, amount must equal monthly_rent) or
    'purchase_order' (ref_id = vendor id; refused if that vendor has an
    open invoice). Refused if the amount exceeds the account's available
    cash (balance minus other pending proposals), so no account can go
    negative. The payments table and balances are NOT touched here.
    """
    con = get_connection()
    try:
        ensure_agent_tables(con)
        # Take the write lock now so two proposals can't both pass the cash check.
        con.execute("BEGIN IMMEDIATE")
        if kind not in ("invoice", "rent", "purchase_order"):
            return {"ok": False, "error": "kind must be invoice, rent or purchase_order"}
        if amount <= 0:
            return {"ok": False, "error": "amount must be positive"}
        acct = con.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()
        if acct is None:
            return {"ok": False, "error": f"unknown account {account}"}

        if kind == "invoice":
            inv = con.execute(
                "SELECT amount, status FROM invoices WHERE id = ?", (ref_id,)
            ).fetchone()
            if inv is None or inv["status"] != "open":
                return {"ok": False, "error": "invoice not found or not open"}
            if abs(inv["amount"] - amount) > 0.005:
                return {"ok": False, "error": f"amount must equal invoice amount {inv['amount']}"}
        elif kind == "rent":
            lease = con.execute(
                "SELECT monthly_rent FROM leases WHERE id = ?", (ref_id,)
            ).fetchone()
            if lease is None:
                return {"ok": False, "error": "lease not found"}
            if abs(lease["monthly_rent"] - amount) > 0.005:
                return {
                    "ok": False,
                    "error": f"amount must equal monthly rent {lease['monthly_rent']}",
                }
        else:
            if con.execute("SELECT 1 FROM vendors WHERE id = ?", (ref_id,)).fetchone() is None:
                return {"ok": False, "error": "vendor not found"}
            if con.execute(
                "SELECT 1 FROM invoices WHERE vendor_id = ? AND status = 'open'", (ref_id,)
            ).fetchone():
                return {"ok": False, "error": "vendor has an unpaid invoice; no orders allowed"}

        if con.execute(
            "SELECT 1 FROM payment_proposals WHERE kind = ? AND ref_id = ? "
            "AND status = 'pending_approval'",
            (kind, ref_id),
        ).fetchone():
            return {"ok": False, "error": "a pending proposal already exists for this item"}

        available = acct["balance"] - _pending_total(con, account)
        if amount > available + 1e-9:
            return {
                "ok": False,
                "error": "insufficient available cash; would make the account negative",
                "available": available,
                "amount": amount,
            }
        cur = con.execute(
            "INSERT INTO payment_proposals "
            "(kind, ref_id, amount, account, reason, ticket_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, account, reason[:300], ticket_id, _today(con)),
        )
        con.commit()
        return {
            "ok": True,
            "proposal_id": cur.lastrowid,
            "status": "pending_approval",
            "kind": kind,
            "ref_id": ref_id,
            "amount": amount,
            "account": account,
            "available_after_if_approved": available - amount,
            "note": "Human approval is required before this is executed.",
        }
    finally:
        con.close()


def _add_one_month(iso: str) -> str:
    d = date.fromisoformat(iso)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day)).isoformat()


@mcp.tool()
def execute_payment(proposal_id: int, approved_by: str) -> dict:
    """Execute ONE pending payment proposal after a human approved it.

    FOR THE BACKEND'S APPROVAL ROUTE ONLY. Agents are not given this tool.
    Everything happens in a single transaction that is rolled back on any
    problem: the proposal must be pending (so a repeat does nothing), the
    invoice/lease/vendor must still be valid, and the account balance must
    cover the amount (so it can never go negative). On success it writes
    one `payments` row, lowers the balance, marks an invoice 'paid', moves a
    lease's next_due forward one month, and marks the proposal 'executed'.
    Failures return ok=false with a `code`: not_found, not_pending, invalid
    or insufficient_cash.
    """
    approver = (approved_by or "").strip()
    if not approver:
        return {"ok": False, "code": "invalid", "error": "approved_by is required"}
    con = get_connection()
    try:
        ensure_agent_tables(con)
        con.execute("BEGIN IMMEDIATE")  # one writer at a time; blocks a double click
        prop = con.execute(
            "SELECT id, kind, ref_id, amount, account, status, ticket_id "
            "FROM payment_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()
        if prop is None:
            return {"ok": False, "code": "not_found", "error": f"proposal {proposal_id} not found"}
        if prop["status"] != "pending_approval":
            return {
                "ok": False,
                "code": "not_pending",
                "error": f"proposal {proposal_id} is already {prop['status']}; nothing was changed",
            }

        kind, ref_id, account = prop["kind"], prop["ref_id"], prop["account"]
        amount = round(prop["amount"], 2)

        if kind == "invoice":
            inv = con.execute(
                "SELECT amount, status FROM invoices WHERE id = ?", (ref_id,)
            ).fetchone()
            if inv is None or inv["status"] != "open":
                return {"ok": False, "code": "invalid", "error": "invoice is not open any more"}
            if abs(inv["amount"] - amount) > 0.005:
                return {"ok": False, "code": "invalid", "error": "invoice amount has changed"}
        elif kind == "rent":
            lease = con.execute(
                "SELECT monthly_rent, next_due FROM leases WHERE id = ?", (ref_id,)
            ).fetchone()
            if lease is None or abs(lease["monthly_rent"] - amount) > 0.005:
                return {"ok": False, "code": "invalid", "error": "lease missing or rent changed"}
        elif kind == "purchase_order":
            if con.execute(
                "SELECT 1 FROM invoices WHERE vendor_id = ? AND status = 'open'", (ref_id,)
            ).fetchone():
                return {
                    "ok": False,
                    "code": "invalid",
                    "error": "vendor has an unpaid invoice; no orders allowed",
                }
        else:
            return {"ok": False, "code": "invalid", "error": "unknown payment kind"}

        acct = con.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()
        if acct is None:
            return {"ok": False, "code": "invalid", "error": f"unknown account {account}"}
        if amount <= 0 or amount > acct["balance"] + 1e-9:
            return {
                "ok": False,
                "code": "insufficient_cash",
                "error": "balance does not cover this payment; nothing was changed",
                "balance": acct["balance"],
                "amount": amount,
            }

        today = _today(con)
        new_balance = round(acct["balance"] - amount, 2)
        cur = con.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, account, today, approver[:80]),
        )
        con.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
            (new_balance, today, account),
        )
        if kind == "invoice":
            con.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        elif kind == "rent":
            con.execute(
                "UPDATE leases SET next_due = ? WHERE id = ?",
                (_add_one_month(lease["next_due"]), ref_id),
            )
        con.execute(
            "UPDATE payment_proposals SET status = 'executed' WHERE id = ?", (proposal_id,)
        )
        con.commit()
        return {
            "ok": True,
            "payment_id": cur.lastrowid,
            "proposal_id": proposal_id,
            "ticket_id": prop["ticket_id"],
            "kind": kind,
            "ref_id": ref_id,
            "amount": amount,
            "account": account,
            "new_balance": new_balance,
            "approved_by": approver[:80],
            "paid_at": today,
        }
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@mcp.tool()
def save_customer_draft(ticket_id: int, subject: str, body: str) -> dict:
    """Save a customer message as a DRAFT for dashboard review. Nothing is sent."""
    con = get_connection()
    try:
        ensure_agent_tables(con)
        if con.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return {"ok": False, "error": "ticket not found"}
        if not subject.strip() or not body.strip():
            return {"ok": False, "error": "subject and body are required"}
        cur = con.execute(
            "INSERT INTO customer_drafts (ticket_id, subject, body, created_at) "
            "VALUES (?, ?, ?, ?)",
            (ticket_id, subject.strip(), body.strip(), _today(con)),
        )
        con.commit()
        return {"ok": True, "draft_id": cur.lastrowid, "status": "draft", "sent": False}
    finally:
        con.close()


@mcp.tool()
def list_customer_drafts(ticket_id: int | None = None) -> list[dict]:
    """List saved customer message drafts (oldest first), optionally for one ticket.

    FOR THE BACKEND ONLY (the dashboard shows these so a person can review them).
    Agents are not given this tool. Drafts are never sent. Reads `customer_drafts`.
    """
    con = get_connection()
    try:
        ensure_agent_tables(con)
        query = "SELECT id, ticket_id, subject, body, status, created_at FROM customer_drafts"
        if ticket_id is None:
            rows = con.execute(query + " ORDER BY id").fetchall()
        else:
            rows = con.execute(query + " WHERE ticket_id = ? ORDER BY id", (ticket_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


@mcp.tool()
def update_ticket_status(ticket_id: int, status: str, note: str, set_by: str = "Boss") -> dict:
    """Set a ticket's outcome. status: resolved, awaiting_approval or needs_investigation.

    `set_by` labels the note; leave it as "Boss" (the dashboard passes "Human")."""
    con = get_connection()
    try:
        if status not in TICKET_STATUSES:
            return {"ok": False, "error": f"status must be one of {TICKET_STATUSES}"}
        row = con.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"ok": False, "error": "ticket not found"}
        previous = row["notes"] or ""
        if set_by == "Boss":
            # Earlier Boss notes go stale (they said "pending" after the payment was made), so
            # keep the original ticket text and any human notes, and replace the old Boss note.
            previous = "\n".join(line for line in previous.split("\n") if not line.startswith("[Boss] "))
        notes = (previous + f"\n[{set_by[:20]}] " + note[:300]).strip()
        con.execute(
            "UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes, ticket_id)
        )
        con.commit()
        return {"ok": True, "ticket_id": ticket_id, "status": status}
    finally:
        con.close()


if __name__ == "__main__":
    mcp.run()
