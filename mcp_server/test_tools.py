"""Check the MCP tools and business rules against the real working database.

Run from the project root:  python mcp_server/test_tools.py
It resets data/campus_customs_new.db from the original first, then calls every tool
over the MCP protocol and compares results with direct SQL.
"""

import asyncio
import json
import shutil
import sqlite3
from pathlib import Path

from fastmcp import Client

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "campus_customs_new.db"
CFG = json.loads((ROOT / ".mcp.json").read_text())


def sql_write(q, *a):
    con = sqlite3.connect(DB)
    try:
        con.execute(q, a)
        con.commit()
    finally:
        con.close()


def sql(q, *a):
    con = sqlite3.connect(DB)
    try:
        return con.execute(q, a).fetchall()
    finally:
        con.close()


async def main():
    shutil.copyfile(ROOT / "data" / "campus_customs.db", DB)
    results = []

    def check(name, ok):
        results.append((name, ok))
        print(("PASS " if ok else "FAIL ") + name)

    async with Client(CFG) as c:
        async def call(tool, **args):
            r = await c.call_tool(tool, args, raise_on_error=False)
            return r.data if r.data is not None else r.structured_content

        tools = {t.name for t in await c.list_tools()}
        check("13 tools exposed", len(tools) == 13)

        t = await call("get_ticket", ticket_id=101)
        row = sql("select type, sku, size, qty, invoice_id from tickets where id=101")[0]
        check("get_ticket matches DB", (t["type"], t["sku"], t["size"], t["qty"], t["invoice_id"]) == row)
        check("get_ticket unknown id", (await call("get_ticket", ticket_id=999))["found"] is False)
        check("list_tickets returns all 3", [x["id"] for x in await call("list_tickets")] == [101, 102, 103])
        check("list_open_tickets", [x["id"] for x in await call("list_open_tickets")] == [101, 102, 103])

        a = await call("get_accounting_status", sku="CC-HOOD-NAVY")
        check("cash matches DB", a["cash_accounts"][0]["balance"] == sql("select balance from cash_accounts")[0][0])
        check("invoice 501 is 3 days overdue", a["invoices"][0]["days_overdue"] == 3)
        check("hoodie margin 36 / 62.1%", a["margin"]["unit_margin"] == 36 and a["margin"]["margin_pct"] == 62.1)

        e = await call("estimate_restock", vendor_id=1, sku="CC-TEE-WHITE", qty=10)
        check("vendor 1 restricted, 5 days, arrives 2026-09-05",
              e["restricted"] and e["earliest_arrival_if_ordered_today"] == "2026-09-05" and e["estimated_cost"] == 80)
        e2 = await call("estimate_restock", vendor_id=2, sku="CC-MUG-CREST", qty=10)
        check("vendor 2 not restricted", e2["restricted"] is False and e2["estimated_cost"] == 35)

        # propose_payment rules
        r = await call("propose_payment", kind="purchase_order", ref_id=1, amount=80, reason="t")
        check("PO to vendor with unpaid invoice refused", r["ok"] is False)
        r = await call("propose_payment", kind="invoice", ref_id=501, amount=100, reason="t")
        check("wrong invoice amount refused", r["ok"] is False)
        r = await call("propose_payment", kind="invoice", ref_id=501, amount=840, reason="t", ticket_id=101)
        check("invoice 501 proposal ok", r["ok"] and r["available_after_if_approved"] == 2560)
        r = await call("propose_payment", kind="rent", ref_id=1, amount=2400, reason="t", ticket_id=102)
        check("rent proposal ok (3240 <= 3400)", r["ok"] and r["available_after_if_approved"] == 160)
        r = await call("propose_payment", kind="purchase_order", ref_id=2, amount=200, reason="t")
        check("over-cash proposal refused (would go negative)", r["ok"] is False and r["available"] == 160)
        r = await call("propose_payment", kind="rent", ref_id=1, amount=2400, reason="t")
        check("duplicate proposal refused", r["ok"] is False)

        check("balance and payments untouched", sql("select balance from cash_accounts")[0][0] == 3400
              and sql("select count(*) from payments")[0][0] == 0)
        check("2 proposals stored pending",
              sql("select count(*) from payment_proposals where status='pending_approval'")[0][0] == 2)

        d = await call("save_customer_draft", ticket_id=101, subject="s", body="b")
        check("draft saved, not sent", d["ok"] and d["sent"] is False
              and sql("select status from customer_drafts")[0][0] == "draft")
        dl = await call("list_customer_drafts", ticket_id=101)
        check("list_customer_drafts returns the draft with its text, status draft",
              len(dl) == 1 and dl[0]["body"] == "b" and dl[0]["subject"] == "s" and dl[0]["status"] == "draft")
        check("list_customer_drafts for a ticket with none is empty", await call("list_customer_drafts", ticket_id=102) == [])
        check("draft for unknown ticket refused", (await call("save_customer_draft", ticket_id=999, subject="s", body="b"))["ok"] is False)
        check("bad ticket status refused", (await call("update_ticket_status", ticket_id=101, status="done", note="x"))["ok"] is False)
        u = await call("update_ticket_status", ticket_id=101, status="awaiting_approval", note="x")
        await call("update_ticket_status", ticket_id=101, status="awaiting_approval", note="second boss note")
        notes = sql("select notes from tickets where id=101")[0][0]
        check("only the latest [Boss] note is kept; original ticket text stays",
              notes == "Needs a tee in size S.\n[Boss] second boss note")
        await call("update_ticket_status", ticket_id=101, status="awaiting_approval", note="human note", set_by="Human")
        await call("update_ticket_status", ticket_id=101, status="awaiting_approval", note="third boss note")
        notes = sql("select notes from tickets where id=101")[0][0]
        check("set_by labels the note, and a human note survives later Boss notes",
              notes == "Needs a tee in size S.\n[Human] human note\n[Boss] third boss note")
        check("ticket status updated", u["ok"] and sql("select status from tickets where id=101")[0][0] == "awaiting_approval")

        # execute_payment: the money-moving tool (proposals 1 = invoice 501, 2 = rent)
        r = await call("execute_payment", proposal_id=1, approved_by="")
        check("execute without approver refused", r["ok"] is False and r["code"] == "invalid")
        r = await call("execute_payment", proposal_id=99, approved_by="tester")
        check("execute unknown proposal -> not_found", r["code"] == "not_found")
        sql_write("insert into payment_proposals (kind, ref_id, amount, account, status, created_at) "
                  "values ('rent', 1, 2400, 'checking', 'pending_approval', 'x')")  # proposal 3: duplicate rent
        sql_write("insert into payment_proposals (kind, ref_id, amount, account, status, created_at) "
                  "values ('purchase_order', 1, 80, 'checking', 'pending_approval', 'x')")  # proposal 4: vendor 1
        r = await call("execute_payment", proposal_id=4, approved_by="tester")
        check("PO to vendor with open invoice refused at execution", r["ok"] is False and r["code"] == "invalid")
        sql_write("insert into payment_proposals (kind, ref_id, amount, account, status, created_at) "
                  "values ('purchase_order', 2, 9999, 'checking', 'pending_approval', 'x')")  # proposal 5: too big
        r = await call("execute_payment", proposal_id=5, approved_by="tester")
        check("over-balance payment refused at execution", r["ok"] is False and r["code"] == "insufficient_cash")
        check("failed executions changed nothing", sql("select balance from cash_accounts")[0][0] == 3400
              and sql("select count(*) from payments")[0][0] == 0
              and sql("select status from invoices where id=501")[0][0] == "open")

        r = await call("execute_payment", proposal_id=1, approved_by="tester")
        check("invoice 501 payment executes", r["ok"] and r["new_balance"] == 2560 and r["ticket_id"] == 101)
        rp = (await call("get_accounting_status"))["recent_payments"]
        check("recent_payments shows the payment with its ticket and reason",
              len(rp) == 1 and rp[0]["amount"] == 840.0 and rp[0]["ticket_id"] == 101 and rp[0]["reason"] == "t")
        check("payment row, balance, invoice and proposal updated",
              sql("select kind, ref_id, amount, approved_by, paid_at from payments") == [("invoice", 501, 840.0, "tester", "2026-08-31")]
              and sql("select balance from cash_accounts")[0][0] == 2560
              and sql("select status from invoices where id=501")[0][0] == "paid"
              and sql("select status from payment_proposals where id=1")[0][0] == "executed")
        r = await call("execute_payment", proposal_id=1, approved_by="tester")
        check("repeat execution refused (not_pending), no second payment",
              r["code"] == "not_pending" and sql("select count(*) from payments")[0][0] == 1
              and sql("select balance from cash_accounts")[0][0] == 2560)
        e3 = await call("estimate_restock", vendor_id=1, sku="CC-TEE-WHITE", qty=10)
        check("vendor 1 no longer restricted after invoice paid", e3["restricted"] is False)
        r = await call("execute_payment", proposal_id=2, approved_by="tester")
        check("rent executes; balance 160; next_due moves to 2026-10-02",
              r["ok"] and r["new_balance"] == 160 and sql("select next_due from leases")[0][0] == "2026-10-02")
        r = await call("execute_payment", proposal_id=3, approved_by="tester")
        check("rent for 2400 refused when only 160 left", r["code"] == "insufficient_cash"
              and sql("select balance from cash_accounts")[0][0] == 160)

    original = sqlite3.connect(ROOT / "data" / "campus_customs.db")
    check("original DB untouched", original.execute("select status from tickets where id=101").fetchone()[0] == "open"
          and original.execute("select count(*) from sqlite_master where name='payment_proposals'").fetchone()[0] == 0)
    shutil.copyfile(ROOT / "data" / "campus_customs.db", DB)  # leave a clean working copy
    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed", failed or "")


asyncio.run(main())
