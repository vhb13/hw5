# Campus Customs: multi-agent shop operations

A team of five AI agents (Boss, Inventory, Accounting, Facilities and Customer Service) that works through a campus shop's tickets. The agents read and change the shop database only through an MCP server. A FastAPI backend runs the agents, and a React dashboard lets a person watch them, approve payments and read the customer drafts.

Rules the system enforces: no payment happens without a human approving it on the dashboard, cash can never go negative, vendors with an unpaid invoice cannot be ordered from, the shop's date is `desk.date_today` (2026-08-31), and customer messages stay as drafts (nothing is ever sent). All five agents use `gpt-6-luna` through Portkey.

## What you need

- Python 3.10 or newer (tested with 3.14) and Node.js with npm (tested with Node 24)
- A Portkey API key (the agents call the model through Portkey)

## Setup from a clean clone

Run these from the repository root.

1. Create a virtual environment and install the Python packages:

   ```
   python -m venv .venv
   ```

   Activate it (Windows PowerShell: `.venv\Scripts\Activate.ps1`, Windows cmd: `.venv\Scripts\activate.bat`, macOS or Linux: `source .venv/bin/activate`), then:

   ```
   pip install -r requirements.txt
   ```

2. Add your key. Copy `.env.example` to `.env` in the repository root and put your real Portkey key in it:

   ```
   cp .env.example .env
   ```

   (On Windows PowerShell use `Copy-Item .env.example .env`.) The file `.env` is in `.gitignore`, so it is never committed. `.env.example` only has a placeholder. Without a key the backend will not start.

3. Install the dashboard packages:

   ```
   cd frontend
   npm install
   cd ..
   ```

## The databases

- `data/campus_customs.db` is the original database. Nothing in the project writes to it.
- `data/campus_customs_new.db` is the working copy. The MCP server and the backend read and write only this file. The copy in this repository is left in the state the recorded run ended in (tickets 101 and 102 resolved, checking balance $152.00).

To get a clean working copy, copy the original over it. Use the reset script (it works on every system):

```
python mcp_server/reset_db.py
```

It is the same as `cp data/campus_customs.db data/campus_customs_new.db` (macOS or Linux) or `Copy-Item data\campus_customs.db data\campus_customs_new.db -Force` (Windows PowerShell). After a reset the checking balance is $3,400.00 and tickets 101, 102 and 103 are open. The dashboard's "Reset test data" button (and `POST /reset`) does the same thing while the backend is running, so use it only when no agent run is in progress.

## Running the project

You need two terminals, both with the virtual environment active.

**MCP server.** You normally do not start it yourself: the backend starts it automatically (it reads `.mcp.json`, which runs `python mcp_server/server.py` over stdio, so it has no port). To run it by hand, from the repository root:

```
python mcp_server/server.py
```

It waits for an MCP client and looks idle. The same `.mcp.json` lets an MCP-aware tool such as Claude Code connect to it from the repository root.

**FastAPI backend (port 8000).** From the `backend` folder:

```
cd backend
python -m uvicorn main:app --port 8000
```

You can add `--reload` (`uvicorn main:app --reload --port 8000`). The first start takes about 20 seconds because it starts the MCP server. Check it at http://localhost:8000/cash.

**React/Vite dashboard (port 5173).** In a second terminal, from the `frontend` folder:

```
cd frontend
npm run dev
```

Open http://localhost:5173. The dashboard talks to the backend at http://localhost:8000, and the backend allows requests from http://localhost:5173 and http://127.0.0.1:5173 (CORS). The dev server uses port 5173 strictly, so if something else is using that port it will stop instead of picking another one.

## Running all three tickets from a clean state

1. Reset the working database (see above) so checking is $3,400.00 and all three tickets are open.
2. Start the backend and the dashboard.
3. In the dashboard type your name in "Approving as". Select a ticket and press "Run agent team". When a payment is waiting, review it and press Approve and then Confirm. Run the ticket again after an approval so the agents can confirm it, then press "Mark resolved" if the Boss has not already resolved it.
4. Do the same for tickets 101, 102 and 103.

The agents prepare payments only; the money moves when you confirm the approval. You can also run the agents without the dashboard with `python backend/run_ticket.py 101 102 103` (it prints each decision but cannot approve payments).

## What is in the repository

| Path | What it is |
|---|---|
| `data/` | The original database and the working copy |
| `mcp_server/` | The MCP server (13 tools), its database helper, the reset script, its tests and `README.md` listing every tool |
| `backend/` | The FastAPI app (`main.py`), the five agents (`team.py`), shared types (`models.py`), settings (`config.py`), the audit trail writer (`audit.py`) and `prompts/` with one prompt file per agent |
| `frontend/` | The React + Vite + TypeScript dashboard |
| `output/` | `harness.md` (full documentation), `design.md`, `desk_tickets.html` (Expected vs Actual, Cash and Reflection), `resolved_tickets.json`, `resolved_board.html` with real dashboard screenshots, `audit_trail.json` (append-only), `agent_messages.json`, `mcp_smoke.json`, `screenshots/` and `github_url.txt` |
| `AI_prompts.md` | The prompts used for each problem |
| `requirements.txt`, `.env.example`, `.mcp.json`, `.gitignore` | Dependencies, the key template, the MCP connection and the ignore rules |

`output/harness.md` documents the database tables, every MCP tool, the five agents, the API routes, the dashboard, the safety rules, the three ticket outcomes and the cash reconciliation.

## Tests

These reset the working database, so run `python mcp_server/reset_db.py` or restore it afterwards if you want to keep a particular state.

- `python mcp_server/test_tools.py` checks every MCP tool and the payment rules against SQL.
- `python backend/test_agents.py` checks that all five agents use `gpt-6-luna` through Portkey. It makes real model calls.
- `python backend/test_api.py` tests the routes against a running backend. It makes real model calls.
- `frontend/e2e.mjs` drives the dashboard in Microsoft Edge with Playwright. It needs `npm install` and Edge.

Some of these tests were written before later changes to the agent prompts, so the model-based ones may need small updates.

## Notes

- The shop has no revenue. Agents never assume new cash will arrive.
- A paid purchase order is treated as "order placed". There is no vendor or delivery system, so nothing is sent to a vendor and stock does not change.
- Customer drafts can be read on the dashboard, but nothing sends them.
