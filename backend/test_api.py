"""Test the live API (uvicorn must be running on port 8000, see harness.md).

Run:  .venv\\Scripts\\python backend\\test_api.py
Runs two tickets with the real agents (gpt-6-luna via Portkey), so it uses tokens.
It starts and ends with a reset, so the working database finishes clean.
"""

import asyncio
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
ROOT = Path(__file__).resolve().parent.parent
ORIG, WORK = ROOT / "data" / "campus_customs.db", ROOT / "data" / "campus_customs_new.db"
results = []
all_bodies = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


def db(q):
    con = sqlite3.connect(WORK)
    try:
        return con.execute(q).fetchall()
    finally:
        con.close()


async def main():
    orig_hash = md5(ORIG)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    async with httpx.AsyncClient(base_url=BASE, timeout=300) as c:
        async def req(method, url, **kw):
            r = await c.request(method, url, **kw)
            all_bodies.append(r.text)
            return r

        # 6. reset
        r = await req("POST", "/reset")
        check("reset ok", r.status_code == 200)
        check("working DB identical to original after reset", md5(WORK) == orig_hash or
              db("select count(*) from tickets where status='open'") == [(3,)])
        check("original DB unchanged by reset", md5(ORIG) == orig_hash)

        # 1. tickets
        r = await req("GET", "/tickets")
        t = r.json()
        check("GET /tickets returns 101-103, all open and not resolved",
              r.status_code == 200 and [x["id"] for x in t] == [101, 102, 103]
              and all(x["status"] == "open" and x["resolved"] is False for x in t))

        # 5. cash
        r = await req("GET", "/cash")
        check("GET /cash = checking 3400", r.json()["balance"] == 3400 == db("select balance from cash_accounts")[0][0])

        # errors
        r = await req("POST", "/tickets/999/run")
        check("run unknown ticket -> 404", r.status_code == 404 and r.json()["detail"]["error"] == "ticket_not_found")
        r = await req("POST", "/tickets/0/run")
        check("run ticket 0 -> 422", r.status_code == 422)
        r = await req("POST", "/tickets/abc/run")
        check("run non-numeric ticket -> 422", r.status_code == 422)
        r = await req("POST", "/payments/999/approve", json={"approved_by": "Vy"})
        check("approve unknown proposal -> 404", r.status_code == 404)
        r = await req("POST", "/payments/1/approve", json={})
        check("approve without approver -> 422", r.status_code == 422)
        r = await req("GET", "/activity?limit=0")
        check("activity bad limit -> 422", r.status_code == 422)

        # 2. run ticket 101 (live agents). Meanwhile other routes must answer, and a second run is refused.
        run101 = asyncio.create_task(req("POST", "/tickets/101/run"))
        await asyncio.sleep(3)
        r = await req("GET", "/activity")
        check("activity answers during a run and says running", r.status_code == 200 and r.json()["running"] is True)
        r = await req("POST", "/tickets/102/run")
        check("second run during a run -> 409 busy", r.status_code == 409 and r.json()["detail"]["error"] == "busy")
        r = await req("POST", "/reset")
        check("reset during a run -> 409", r.status_code == 409)
        r101 = await run101
        d = r101.json()
        check("run 101 -> 200 with outcome needs_human_approval",
              r101.status_code == 200 and d["outcome"] == "needs_human_approval", str(d.get("outcome")))
        r = await req("POST", "/tickets/102/run")
        d2 = r.json()
        check("run 102 -> 200 needs_human_approval, no Inventory/Customer Service call",
              r.status_code == 200 and d2["outcome"] == "needs_human_approval"
              and "inventory" not in d2["agents_consulted"] and "customer_service" not in d2["agents_consulted"],
              str(d2.get("agents_consulted")))

        # 3. activity
        a = (await req("GET", "/activity?limit=100&ticket_id=101")).json()
        check("activity has steps with tools", any(s["tool"] == "get_inventory_status" for s in a["steps"]))
        check("activity has agent messages with tools_used",
              any(m["agent"] == "boss" and m["tools_used"] for m in a["messages"])
              and any(m["agent"] == "inventory" for m in a["messages"]))
        new_msgs = [m for m in a["messages"] if m["time"] >= started]  # older runs predate the name scrub
        check("customer name not in this run's messages",
              len(new_msgs) >= 3 and "Zaman" not in str(new_msgs) and "Tauhid" not in str(new_msgs))

        # tickets after the runs
        t = {x["id"]: x for x in (await req("GET", "/tickets")).json()}
        check("tickets now awaiting_approval with pending payments listed",
              t[101]["status"] == "awaiting_approval" and t[102]["status"] == "awaiting_approval"
              and t[101]["pending_payments"] and t[102]["pending_payments"] and not t[101]["resolved"])

        # 4. approval
        cash = (await req("GET", "/cash")).json()
        check("cash shows 2 pending proposals, balance untouched",
              cash["balance"] == 3400 and len(cash["pending_proposals"]) == 2 and cash["available"] == 160)
        inv = next(p for p in cash["pending_proposals"] if p["kind"] == "invoice")
        rent = next(p for p in cash["pending_proposals"] if p["kind"] == "rent")
        r = await req("POST", "/tickets/101/resolve")
        check("resolve refused while a payment is pending -> 409", r.status_code == 409 and r.json()["detail"]["error"] == "payment_pending")
        r = await req("POST", "/tickets/999/resolve")
        check("resolve unknown ticket -> 404", r.status_code == 404)
        a1, a2 = await asyncio.gather(
            req("POST", f"/payments/{inv['id']}/approve", json={"approved_by": "Vy"}),
            req("POST", f"/payments/{inv['id']}/approve", json={"approved_by": "Vy"}),
        )
        codes = sorted([a1.status_code, a2.status_code])
        check("two simultaneous approvals: exactly one 200 and one 409", codes == [200, 409], str(codes))
        check("invoice paid once: balance 2560, one payments row, invoice paid",
              db("select balance from cash_accounts")[0][0] == 2560 and db("select count(*) from payments")[0][0] == 1
              and db("select status from invoices where id=501")[0][0] == "paid")
        r = await req("POST", f"/payments/{inv['id']}/approve", json={"approved_by": "Vy"})
        check("repeat approval -> 409 not_pending", r.status_code == 409 and r.json()["detail"]["error"] == "not_pending")
        r = await req("POST", f"/payments/{rent['id']}/approve", json={"approved_by": "Vy"})
        check("rent approval -> 200, balance 160", r.status_code == 200 and r.json()["new_balance"] == 160)
        check("cash route shows 160, nothing pending",
              (await req("GET", "/cash")).json()["balance"] == 160 and (await req("GET", "/cash")).json()["pending_proposals"] == [])
        check("payments table has 2 rows with approver", db("select count(*), min(approved_by) from payments") == [(2, "Vy")])
        check("balance never negative", db("select balance from cash_accounts")[0][0] >= 0)

        r = await req("POST", "/tickets/101/resolve")
        check("resolve after payment -> 200 and ticket shows resolved",
              r.status_code == 200 and db("select status from tickets where id=101") == [("resolved",)])
        r = await req("POST", "/tickets/101/resolve")
        check("resolve twice -> 409", r.status_code == 409)
        r = await req("POST", "/tickets/101/run")
        check("running a resolved ticket -> 409", r.status_code == 409 and r.json()["detail"]["error"] == "ticket_resolved")
        t = {x["id"]: x for x in (await req("GET", "/tickets")).json()}
        check("GET /tickets reports resolved true for 101, false for 102", t[101]["resolved"] is True and t[102]["resolved"] is False)

        # 6. reset restores everything
        r = await req("POST", "/reset")
        check("reset after work -> 200", r.status_code == 200)
        check("balance back to 3400, payments empty, tickets open again, invoice open",
              db("select balance from cash_accounts") == [(3400.0,)] and db("select count(*) from payments") == [(0,)]
              and db("select count(*) from tickets where status='open'") == [(3,)]
              and db("select status from invoices where id=501") == [("open",)])
        check("original DB still byte-identical", md5(ORIG) == orig_hash)
        load_dotenv(ROOT.parent / ".env")  # the real key, so we can search for it
        key = os.environ.get("PORTKEY_API_KEY", "")
        check("the real API key and the key header never appear in any response body",
              len(key) > 10 and not any(key in b or "x-portkey" in b.lower() for b in all_bodies))
    print(f"\n{sum(results)}/{len(results)} passed")


asyncio.run(main())
