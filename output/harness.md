# Campus Customs — Database Harness

Running notes on how the shop's data is organized. We add to this file as we go
through each problem — don't overwrite earlier sections, just add new ones below.

Database file: `data/campus_customs.db` (original, never modified).
Working copy: `data/campus_customs_new.db` (same tables/data, this is what the
MCP server and backend will read/write once we get to the later problems).

## Problem 2: The tables, and why each one matters to the agent

### `desk`
Fields: `date_today`, `notes`
One row only. `date_today` is the shop's "today" (currently `2026-08-31`) —
the agent should always use this instead of the real calendar date, so that
"is this overdue?" checks work the same way every time we re-run the test
database. `notes` is just a free-text scratchpad, currently empty.

### `cash_accounts`
Fields: `name`, `balance`, `date`
One row: the `checking` account, balance $3,400 as of `2026-08-31`. This is
the only source of money in the system — there's no revenue table, so every
payment the agent approves has to come out of this balance, and it must
never go negative.

### `inventory`
Fields: `sku`, `name`, `size`, `qty`, `location`
One row per SKU + size combination (10 rows total: hoodie in 4 sizes, tee in
4 sizes, one hat size, one mug size). This is what the Inventory agent checks
to see if a product is in stock. Right now `CC-TEE-WHITE` size S is at 0, and
`CC-MUG-CREST` is also at 0 — those are the shortages the agent will need to
notice and act on.

### `pricing`
Fields: `sku`, `unit_cost`, `list_price`
One row per SKU (not per size — price is the same across sizes). `unit_cost`
is what the shop pays to acquire/produce it, `list_price` is what it sells
for. The Accounting agent needs both numbers to judge whether a discount
request (like the bulk hoodie ticket) still leaves a healthy margin.

### `vendors`
Fields: `id`, `name`, `specialty`, `lead_days`
One row per vendor (3 total). `lead_days` is how long a restock order takes
to arrive — the Inventory agent uses this to estimate a restocking date. The
vendor `id` here is what `invoices.vendor_id` points to, which is how the
agent checks "does this vendor have an unpaid invoice?" before ordering from
them.

### `invoices`
Fields: `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`
Bills the shop owes to vendors. One open invoice right now: #501, $840 owed
to vendor 1 (Bulldog Print Co), due `2026-08-28` — already overdue relative
to `desk.date_today` (`2026-08-31`). The rule "don't order from a vendor with
an outstanding unpaid invoice" is checked by looking here.

### `leases`
Fields: `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
One row: the Chapel Street shop lease, $2,400/month rent, next due
`2026-09-02`. The Facilities agent watches `next_due` against `desk.date_today`
to know when rent needs to be paid.

### `payments`
Fields: `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`
Empty right now (0 rows) — this is the ledger that gets a new row every time
the agent actually executes a payment (rent, invoice, etc.), after a human
approves it. `kind`/`ref_id` is how a payment links back to what it paid for
(e.g. `kind='invoice', ref_id=501`), and `approved_by` records who signed off,
since payments always need human approval before they happen.

### `tickets`
Fields: `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`,
`invoice_id`, `status`, `notes`, `created_at`
The actual work items the Boss agent reads and delegates. Not every field is
used by every ticket — a ticket only fills in the columns relevant to its
`type` (e.g. a rent ticket uses `lease_id` and leaves `sku`/`size`/`qty`
blank). `status` starts as `open` and should change as the agent resolves it.

## How the 3 open tickets connect to the other tables

**Ticket 101 — customer_order (Tauhid Zaman wants a Bulldog tee, size S, qty 1)**
- Points to `invoice_id = 501`.
- `inventory`: `CC-TEE-WHITE` / size S has **qty 0** — out of stock.
- `invoices` #501 is for vendor 1, "Rush reprint CC-TEE-WHITE S", $840, open,
  due `2026-08-28` (already overdue) — this is literally the unpaid bill for
  restocking the exact item this customer is asking for.
- `vendors` #1 is Bulldog Print Co, the apparel reprint vendor, 5-day lead
  time — the vendor you'd normally reorder from, except they have that open
  invoice.
- **The chain:** customer wants a tee → it's out of stock → the obvious
  restock vendor already has an unpaid invoice → by the business rule, the
  agent can't place a new order with them → Accounting has to get invoice
  501 paid (human-approved, out of the $3,400 cash balance) before Inventory
  can place the restock order, which then takes 5 more days to arrive. This
  ticket can't be fully resolved by Inventory alone — it needs Accounting too.

**Ticket 102 — rent_notice (Elm City Properties, rent due in 2 days)**
- Points to `lease_id = 1`.
- `leases` #1 is the Chapel Street shop, $2,400/month, `next_due = 2026-09-02`
  — 2 days after `desk.date_today` (2026-08-31), matching the ticket's notes.
- **The chain:** Facilities checks the lease, confirms rent is really due
  soon, and asks Accounting to prepare a $2,400 payment from `checking`
  ($3,400 balance — enough to cover it, but worth noting the invoice-501
  payment above would also draw from the same account). Needs human approval
  before it's paid, then a row gets added to `payments`.

**Ticket 103 — price_override (Yale AI Club wants 20 hoodies, size M, bulk discount)**
- `inventory`: `CC-HOOD-NAVY` size M has qty 8 — not enough to fill an order
  of 20 as-is (shortfall of 12).
- `pricing`: `CC-HOOD-NAVY` costs $22, lists for $58 — Accounting uses this
  margin to judge how much of a discount is affordable.
- No vendor/invoice linked yet, but if Inventory decides to restock hoodies
  to cover the shortfall, the same vendor-with-unpaid-invoice check would
  apply (hoodies aren't tied to vendor 1 in the data, so this one is likely
  more about Accounting approving a price override than Inventory ordering
  stock — but the qty-8-vs-20 shortfall is the first thing the agent should
  flag).
- **The chain:** Customer Service drafts a response to Yale AI Club, Boss
  coordinates between Inventory (can we even fill 20?) and Accounting (what
  discount still keeps a margin), and any price override is a decision the
  Boss makes, informed by both.

## Problem 3: The MCP server and its first 3 tools

Added `mcp_server/` (FastMCP, not yet run/connected — just built for now).
It reads from `data/campus_customs_new.db` (never the original). Agents will
call these tools later instead of touching the database directly. Full
details are in `mcp_server/README.md`; short version:

- **`get_inventory_status(sku, size=None)`** — stock + pricing for a SKU.
  Confirmed it correctly reports `CC-TEE-WHITE` size S at qty 0 (ticket 101)
  and `CC-HOOD-NAVY` size M at qty 8 with cost $22 / list $58 (ticket 103,
  margin check for the discount ask).
- **`get_vendor_status(vendor_id=None)`** — vendor lead times + unpaid
  invoice flag. Confirmed vendor 1 (Bulldog Print Co) shows
  `has_unpaid_invoice: True`, $840 owed — this is what should stop Inventory
  from placing a new restock order with them for ticket 101 until Accounting
  pays invoice 501.
- **`get_facilities_status()`** — today's date, cash balance, and lease
  due-date math. Confirmed it reports the Chapel Street lease as due in 2
  days (not yet overdue) and checking balance $3,400 — what Facilities/
  Accounting need to evaluate ticket 102.

Only 3 tools for now by design — more will be added once the agents
(problem 5) make it clearer what else they need (e.g. nothing yet
updates/writes to the database, this first batch is read-only lookups).

## Problem 4: Connecting the MCP server and testing each tool

**How it's connected.** `.mcp.json` at the project root registers the server
as `campus-customs`. It runs `python mcp_server/server.py` over stdio, and the
server reads `data/campus_customs_new.db` (never the original). Claude Code
picks up `.mcp.json` when it starts in this folder and asks you to approve the
project server the first time. Restart or reload the session after adding it.

**How to start it manually.** From the project root, run
`python mcp_server/server.py`. It waits for an MCP client on
stdio, so it looks idle. Needs `pip install -r requirements.txt` (the one at the repository root).

**How each tool was tested.** Claude Code called each tool itself through the
connected `campus-customs` server (tool names `mcp__campus-customs__...`).
`output/mcp_smoke.json` holds the prompt, tool name, arguments, and verbatim
output for each call. Every output was checked against
`data/campus_customs_new.db`, and all three match:
- `get_inventory_status`: CC-TEE-WHITE size S, qty 0, cost $8, list $28.
- `get_vendor_status`: vendor 1 Bulldog Print Co, 5 lead days, invoice 501
  ($840) open.
- `get_facilities_status`: today 2026-08-31, checking $3,400, rent $2,400 due
  2026-09-02 (2 days).

## Problem 5: The five-agent team

Code is in `backend/`: `team.py` (agents and delegation), `models.py` (shared
types), `config.py` (model, Portkey, limits), `audit.py` (audit trail),
`run_ticket.py` (run tickets from the command line), and `prompts/` (one
prompt file per agent). Run: `.venv\Scripts\python backend\run_ticket.py 101 102 103`.

### The agents
| Agent | Responsibility | MCP tools it can use |
|---|---|---|
| Boss | Reads the ticket, finds the main issue, asks the most relevant specialist first, delegates follow-ups only when needed, checks for contradictions or gaps, decides the outcome (`resolved`, `needs_human_approval`, `needs_investigation`) and records it | `get_ticket`, `list_open_tickets`, `update_ticket_status` |
| Inventory | Stock, shortages, restocking, vendor lead times, flags vendors with unpaid invoices, asks Accounting before recommending a purchase | `get_ticket`, `get_inventory_status`, `get_vendor_status`, `estimate_restock` |
| Accounting | Cash, invoices, margins; checks available cash; prepares payments for human approval | `get_ticket`, `get_accounting_status`, `get_vendor_status`, `propose_payment` |
| Facilities | Lease, rent, overdue checks against `desk.date_today`; asks Accounting for payments, Inventory for stock or delivery effects | `get_ticket`, `get_facilities_status` |
| Customer Service | Turns confirmed facts into friendly draft messages | `get_ticket`, `get_inventory_status`, `save_customer_draft` |

Each agent only sees its own tools (the MCP toolset is filtered per agent). Every
agent also has `ask_specialist`, which is how agents ask each other for help.

### MCP tools and the tables they use
| Tool | Tables |
|---|---|
| `get_inventory_status` | `inventory`, `pricing` |
| `get_vendor_status` | `vendors`, `invoices` |
| `get_facilities_status` | `desk`, `cash_accounts`, `leases` |
| `list_open_tickets` | `tickets` |
| `get_ticket` | `tickets` |
| `get_accounting_status` | `cash_accounts`, `invoices`, `desk`, `pricing`, `payment_proposals` |
| `estimate_restock` | `vendors`, `pricing`, `invoices`, `desk` |
| `propose_payment` (writes) | writes `payment_proposals`; reads `invoices`, `leases`, `vendors`, `cash_accounts` |
| `save_customer_draft` (writes) | writes `customer_drafts`; reads `tickets` |
| `update_ticket_status` (writes) | writes `tickets` |

`payment_proposals` and `customer_drafts` are two new tables created in the
working copy only (`data/campus_customs_new.db`). The original database is not
changed. All shop facts and changes go through the MCP server. The backend has
no direct database access.

### Delegation workflow
1. The Boss reads the ticket and asks one specialist the most relevant question
   (`ask_specialist(agent, question, known_facts)`). The question and a few facts
   are passed, not the whole conversation or database records. The specialist
   looks up details itself through its own tools.
2. A specialist can ask another specialist (for example Inventory asks Accounting
   before recommending a purchase, Facilities asks Accounting about rent).
3. Customer Service is asked last, after facts are confirmed.
4. Specialists return a short structured finding (summary, verified facts,
   recommendation, blockers, approval needed, proposal and draft ids).
5. The Boss combines the findings, checks for contradictions and gaps, decides
   the outcome and calls `update_ticket_status`.

The Boss is not askable, so it stays the coordinator. Loops are blocked: an agent
cannot ask itself or an agent already in the request chain.

### Safety rules
- Payments are only proposed (`propose_payment`). No tool executes a payment, so
  nothing writes `payments` or changes a balance. A human must approve.
- A purchase order to a vendor with an open invoice is refused by the tool.
- A proposal larger than available cash (balance minus other pending proposals)
  is refused, so cash cannot go negative. No revenue is assumed.
- The shop date is always `desk.date_today`.
- Customer messages are saved as drafts. Nothing is emailed or sent.
- Agents may only state facts returned by tools.

### Model and Portkey configuration
All five agents share one model object built in `config.build_model()`:
- Model: `gpt-6-luna`, via Portkey (`https://api.portkey.ai/v1`), header
  `x-portkey-provider: openai`.
- Key: `PORTKEY_API_KEY`, read from the environment (`.env`). It is not stored in code.
- API: OpenAI **Responses** API (`OpenAIResponsesModel`). The first attempt used chat
  completions and Portkey returned a 400: "Function tools with reasoning_effort
  are not supported for gpt-6-luna ... use /v1/responses". The Responses API
  fixed it. The model name was not changed.
- Python environment: `.venv` (pydantic-ai 1.107, mcp 1.x). PydanticAI 1.x does
  not work with the system Python's mcp 2.x. The MCP server still runs on the system
  Python (as in `.mcp.json`).

### Limits on loops and tokens (per ticket run, shared by all agents)
- Max 10 agent runs, max delegation depth 3.
- Max 40 model requests, 40 tool calls and 150,000 total tokens (PydanticAI `UsageLimits`,
  shared through `usage=ctx.usage`).
- Each agent retries invalid output up to 2 times.

### Audit trail
`output/audit_trail.json` is append-only. Each step has a timestamp, ticket id,
agent, tool, short summary and status (`in_progress`, `delegated`, `finished`,
`needs_human_approval`, `error`). The file is re-read and appended to, so earlier
entries survive restarts. Customer drafts and ticket text are redacted. Delegation
and finish entries log counts and ids only.

### Testing done
- `mcp_server/test_tools.py`: 22/22 checks pass against the real database (tool
  outputs match SQL, the original database is untouched, and the rules in "Safety
  rules" hold, including refusal of a purchase order to vendor 1 and of a payment
  that would overdraw cash).
- Live run of tickets 101, 102 and 103 with gpt-6-luna through Portkey. Results:
  101 `needs_human_approval` (Inventory asked Accounting; invoice 501 payment
  proposed; draft saved), 102 `needs_human_approval` (Facilities asked Accounting;
  rent proposed; no Inventory or Customer Service call), 103 `needs_investigation`
  (only 8 of 20 hoodies; vendor restricted; cash short for the restock; draft
  saved). The balance stayed $3,400, `payments` stayed empty, and the two
  proposals total $3,240, within $3,400.

### Not tested / known limits
- The loop-guard and run-limit refusals are coded but not triggered in a live run.
- Executing an approved payment is not built yet (later problem).
- The agents' choices vary a little between runs, because they are language models.
  The tools enforce the hard rules.
- `output/audit_trail.json` also holds entries from the first test run, including
  one `error` entry from the chat-completions failure. They are kept because the log
  is append-only. The earliest entries (from the first run, before this was fixed)
  include free-text summaries that name a customer.

## Problem 6: Planning the three tickets (`output/desk_tickets.html`)

`output/desk_tickets.html` is a single page you open in a browser. It has one tab
each for tickets 101, 102 and 103, plus Cash and Reflection tabs that just say
"coming later". Each ticket tab shows the ticket's real fields, then two
separate sections:

- **Expected** (filled in now): our prediction, made before testing, of how the
  team should handle the ticket. It covers which agent the Boss calls first and
  why, the delegation steps and why work is passed between agents, and the MCP
  tools we expect to be used with what each should return. It also lists gaps,
  meaning things the plan needs that no current tool provides.
- **Actual** (blank on purpose): to be filled in after we run the agents, so we
  can compare it with Expected.

The Expected plans are predictions based on the ticket records, the database
and the ten MCP tools in `mcp_server/README.md`. They are not results from the
agent runs. In short, we predict: 101 starts with Inventory, then Accounting
(invoice 501), then Customer Service, ending in human approval; 102 starts with
Facilities, then Accounting (rent), with no Inventory or Customer Service call,
ending in human approval; 103 starts with Inventory, then Accounting (margin and
restock cost), then Customer Service, ending in needs investigation.

Gaps the plans point out for later: no tool to execute payments or place vendor
orders, no SKU-to-vendor link, no tool or policy for discounts or price
overrides, no way to reserve stock, and no way to reply to a landlord.
Nothing in the code changed for this problem.

## Problem 7: FastAPI backend (`backend/main.py`)

Run it from the `backend/` folder with the project's `.venv`:
`..\.venv\Scripts\python -m uvicorn main:app --reload --port 8000`
(or activate `.venv` first and use `uvicorn main:app --reload --port 8000`).
Install with `pip install -r requirements.txt` (repository root). Startup takes about 20 seconds
because it starts the MCP server. The API is a thin layer over what we already built:
`team.run_ticket` for the agents, and the MCP server (`team.mcp_server`) for every shop fact
and database change. There is no second agent system and no direct database code for shop
data. The only direct file work is the reset. CORS allows the React dev server
(`http://localhost:5173`).

### Routes (one line each)
- `GET /tickets`: all tickets (101-103) with `status`, a `resolved` true/false flag, and any pending payments for each.
- `POST /tickets/{ticket_id}/run`: runs the Boss agent team on that ticket and returns its decision; 404 unknown ticket, 409 if resolved or another run/reset is in progress, 502 if the agents fail.
- `GET /activity?limit=40&ticket_id=`: recent audit steps (agent, tool, status) plus what each agent said and which tools it used, with a `running` flag for polling.
- `POST /payments/{proposal_id}/approve` (body `{"approved_by": "name"}`): a human approves a pending payment or purchase; the money moves here and only here.
- `POST /tickets/{ticket_id}/resolve`: a human marks a ticket resolved; refused with 409 while a payment for it is pending (added in Problem 8 for the dashboard).
- `GET /cash`: checking balance, amount earmarked by pending proposals, amount available, and the pending proposals (their ids are what approve needs).
- `POST /reset`: restores `data/campus_customs_new.db` from the untouched original (opened read-only); refused with 409 while an agent run is in progress.

### How approval stays safe
The approve route calls a new MCP tool, `execute_payment`. Agents are not given this tool;
only the API calls it. Inside one transaction (`BEGIN IMMEDIATE`, rolled back on any problem)
it checks that: the proposal exists and is still `pending_approval`; the invoice is still open
at the same amount (or the lease rent matches, or the vendor has no unpaid invoice for a
purchase order); and the account balance covers the amount, so it can never go negative. Then
it writes one `payments` row, lowers `cash_accounts.balance`, marks an invoice `paid`, moves a
lease's `next_due` forward one month for rent, and marks the proposal `executed`.
A repeated or simultaneous approval hits the "already executed" check and gets a 409 with no
changes. Errors: 404 not found, 409 not pending / insufficient cash / busy, 422 invalid or
missing approver. `propose_payment` also now takes the write lock before checking cash.
Approving a payment does not change the ticket's status. Marking tickets resolved is left to
Problem 9, because paying invoice 501 does not by itself give the customer a tee.

### What's new in the MCP server (now 12 tools)
`list_tickets` (table `tickets`: every ticket whatever its status) and `execute_payment`
(reads `payment_proposals`, `invoices`, `leases`, `vendors`, `cash_accounts`, `desk`; writes
`payments`, `cash_accounts`, `invoices`, `leases`, `payment_proposals`). Both are used by the
API only.

### Agent messages for the dashboard
`output/agent_messages.json` (append-only) holds what each agent said when it finished
(summary, facts, recommendation) plus the tools it used. Text is capped and the customer's
name is replaced with `[customer]`. The audit trail still never holds agent text. The first
test runs, before the name scrub was fixed, left some entries in this file that say "Tauhid"
(a first name); they are kept because the file is append-only.

### Errors and privacy
Errors are short and fixed: for example "The model service rejected a request (HTTP 401)" or
"The agents hit their step or token limit". Raw exception text, provider response bodies,
API keys and customer text are not returned or logged (`team.safe_error`). The audit trail
contains one older `error` entry from before this fix that quotes a provider message
("Invalid API Key"); it holds no key, and it stays because the log is append-only.

### Testing
- `python mcp_server/test_tools.py`: 34/34, now including `execute_payment` (happy path,
  repeat, over-balance, restricted vendor, rent date moves, failures change nothing).
- `.venv\Scripts\python backend\test_api.py` (server running on port 8000): 32/32 against the
  real server with live agents: all six routes, 404/422/409 errors, activity answering during a
  run, a second run and a reset refused during a run, two simultaneous approvals giving one 200
  and one 409, balance 3400 -> 2560 -> 160 and never negative, reset restoring the working
  database, the original database byte-identical, and no API key in any response.
- A second server with a deliberately wrong key returned a clean 502 with no key, and
  released the busy lock.
- `backend/test_agents.py`: 12/12, all 19 model calls used `gpt-6-luna`.

### Not tested / known limits
- `--reload` restarting after a code change could not be verified here. In this environment a
  trivial FastAPI app does not restart under `--reload` either, so it is the test setup, not
  this code. The server starts correctly with `--reload`. If it hangs on a restart in your
  terminal, stop it with Ctrl+C and start it again.
- Runs are one at a time (an agent run holds a lock). A run takes a few seconds to a minute.
- The React dashboard is not built yet (Problem 8), so nothing here was tested from a browser.
- There is no route to reject a proposal. Pending proposals can only be approved.

## Problem 8: React dashboard (`frontend/`)

The dashboard is a React + Vite + TypeScript app that talks to the backend from Problem 7 at
`http://localhost:8000` (CORS already allows `http://localhost:5173`). It has no sample data;
everything comes from the real routes. The look and layout are explained in `output/design.md`.

Run it (two terminals):
- Backend, from `backend/`: `..\.venv\Scripts\python -m uvicorn main:app --port 8000`
- Dashboard, from `frontend/`: `npm install` (first time), then `npm run dev`, then open `http://localhost:5173`

### What each part of the screen uses
- Ticket cards and status counts: `GET /tickets`.
- Checking balance, reserved and free cash: `GET /cash` (refreshed after every approval).
- "Run agent team": `POST /tickets/{id}/run`. While it runs, `GET /activity` is polled every second
  for the agent boxes, the activity feed and the summaries. Otherwise it is polled every 4 seconds.
- "What each agent did": the `messages` from `GET /activity` (Boss decision first, one card per agent).
- "Approve" (asks for a second click to confirm): `POST /payments/{id}/approve` with the name in "Approving as".
- "Mark resolved": `POST /tickets/{id}/resolve` (new in this problem, see below).
- "Reset test data": `POST /reset`. The dashboard then ignores activity from before the reset.

### Backend change made for the dashboard
Added `POST /tickets/{ticket_id}/resolve`: a human closes a ticket. It returns 404 for an unknown
ticket and 409 if the ticket is already resolved, a payment for it is still pending, or a run is in
progress. It calls `update_ticket_status` through MCP (which now takes an optional `set_by` label,
default "Boss", used as "Human" here). The routes list in Problem 7 therefore has a seventh route.

### How "resolved" works
A ticket shows Resolved when the Boss's outcome is `resolved` (the backend sets the status), or when a
person clicks Mark resolved. A finished run does not mark a ticket resolved by itself when it ended as
`needs_human_approval` or `needs_investigation`, because marking it resolved then would be untrue.
In practice none of the three tickets ends as `resolved` straight after a run.

### Testing
`frontend/e2e.mjs` drives the real dashboard in Edge (Playwright) against the real backend with live
agents: 38/38 checks passed. It covers loading three tickets with status text and the balance, selecting a
ticket, starting a run and seeing the working state and live feed, summaries without duplicate agents,
approval needing two clicks, the balance refreshing ($3,400 to $2,560 to $160), marking tickets resolved,
a ticket the agents did not finish, the summary counts, reset from the UI, a backend-unreachable error
state with "Try again", and no sideways scrolling at 390px. `backend/test_api.py` is now 38/38
(it covers the resolve route) and `mcp_server/test_tools.py` is 34/34. `npx tsc -b` and `npm run build` pass.
Screenshots were checked by eye for the loaded, awaiting-approval and phone views.

### Found while testing
- The dashboard said "Payment approved" on a ticket left Awaiting approval with no payment. Fixed:
  the text now says no payment is waiting.
- Accounting appeared three times in the summaries when several agents asked it. Fixed: one card
  per agent.
- Agent outcomes vary between runs. On one run the Boss answered ticket 103 by asking only Accounting,
  skipped the Inventory check (only 8 of 20 hoodies), and called the outcome "needs human approval" with
  no payment to approve. The dashboard labels that case "Needs a human decision". This is an agent
  behaviour to look at in Problem 9 (for example by telling the Boss to check stock whenever a ticket
  asks for a quantity), not something the dashboard can fix. I did not change the agents' prompts.

### Not tested / limits
- Only Edge was tested, on Windows. No Firefox or Safari.
- Polling, not push: the feed can be up to a second behind. Each step is logged after it finishes,
  so the feed shows what an agent just did, not what it is about to do.
- Runs are one at a time (the Run button is disabled while another ticket runs).
- The dashboard can't reject a payment; there is no route for it.
- The backend's `--reload` restart was not testable here (see Problem 7); the dashboard tests used
  `uvicorn` without `--reload`.

## Problem 9: Running the three tickets (actual results)

Everything in this section comes from the real run on 2026-10-10 (shop date 2026-08-31, audit times in UTC).
It is backed by `data/campus_customs_new.db`, `output/audit_trail.json`, `output/agent_messages.json`,
`output/resolved_tickets.json`, `output/desk_tickets.html` (Actual and Cash tabs) and `output/resolved_board.html`.

### Result in one table
| Ticket | Final status (database) | Cash change | What happened |
|---|---|---|---|
| 101 Bulldog tee | **resolved** | −$848.00 | Invoice 501 ($840) and a $8 purchase order for 1 tee were approved and paid; customer draft 1 saved (not sent) |
| 102 Rent due | **resolved** | −$2,400.00 | Rent for the 2026-09-02 installment approved and paid; lease `next_due` moved to 2026-10-02 |
| 103 Bulk hoodie discount | **needs_investigation (NOT resolved)** | $0.00 | Only 8 of 20 hoodies; $264 restock vs $152 cash; no discount policy; customer draft 2 saved (not sent) |

Checking balance: **$3,400.00 → $152.00**. Ticket 103 could not be safely resolved; the reasons are below.

### Procedure
1. **Reset.** `python mcp_server/reset_db.py` copied `data/campus_customs.db` over `data/campus_customs_new.db`.
   Checked: the original's MD5 was `46effb90...` before and after (never written to), the working copy matched it, 3 tickets
   open, `payments` empty, invoice 501 open. **Starting checking balance: $3,400.00** (`cash_accounts`, read from the working database).
   Both the MCP server (`mcp_server/db.py`) and the backend use the working copy, and `GET /cash` returned $3,400.00 before any run.
   A "reset" marker was appended to the audit trail so the dashboard ignores older activity.
2. **Runs and approvals went through the React dashboard.** `frontend/drive.mjs` drives the real dashboard in Edge
   (Playwright): it clicks "Run agent team", then Approve and Confirm, and takes screenshots. No ticket status was set by hand,
   the database was not edited, and nothing bypassed MCP. Money moved only through the dashboard's approve button, which calls
   `POST /payments/{id}/approve` and the MCP tool `execute_payment`.
3. **Approvals.** I made the approval decisions on your instruction, so `payments.approved_by` says "Claude (acting for Vy)".
   Each approval was checked against the database first: the item exists and is still pending, the amount matches the invoice,
   lease or unit cost, and cash covers it.
4. **Verification.** Final statuses, balances and payments were read back from the database, not taken from what an agent said.

### Actual agent and tool flow (from the audit trail)
**Ticket 101** (6 runs, 2 approvals): run 1: Boss → Inventory → Accounting (proposal 1, invoice 501 $840); approval → $2,560.00.
Run 2: Boss → Inventory → Accounting (proposal 2, purchase order $8 for 1 tee); approval → $2,552.00. Runs 3 to 5 ended "needs investigation"
(see below). Run 6: Boss → Inventory → Accounting, then Boss → Customer Service (draft 1); Boss set the ticket `resolved`.
Tools used: Boss `get_ticket`, `update_ticket_status`; Inventory `get_ticket`, `get_inventory_status`, `get_vendor_status`, `estimate_restock`;
Accounting `get_ticket`, `get_accounting_status`, `get_vendor_status`, `propose_payment`; Customer Service `get_ticket`, `save_customer_draft`. Facilities was not called.

**Ticket 102** (3 runs, 1 approval): run 1: Boss → Facilities → Accounting (proposal 3, rent $2,400); approval → $152.00.
Run 2 ended "needs investigation" (see below). Run 3: Boss → Accounting → Facilities; Boss set `resolved`.
Tools: Boss `get_ticket`, `update_ticket_status`; Facilities `get_ticket`, `get_facilities_status`; Accounting `get_ticket`, `get_accounting_status`, `propose_payment`.
Inventory and Customer Service were not called, so the Boss did not call everyone.

**Ticket 103** (1 run): Boss → Inventory → Accounting; Boss → Accounting → Customer Service (a policy question); Boss → Customer Service (draft 2).
Tools: Boss `get_ticket`, `update_ticket_status`; Inventory `get_inventory_status`, `get_vendor_status`, `estimate_restock`; Accounting `get_accounting_status`, `get_ticket`;
Customer Service `get_ticket`, `get_inventory_status`, `save_customer_draft`. `propose_payment` was not used.

Across the three tickets there were 10 agent-team runs and 3 approvals. 202 audit entries were appended after the reset marker (818 in the file; the 615 earlier entries are untouched).

### Why ticket 103 is not resolved
- Stock: 8 hoodies (size M) of the 20 asked for; 12 short.
- Restock: 12 × $22 = **$264**. Checking had **$152**, so $112 short. There is no revenue, so no new cash can arrive, and cash may not go negative.
- All four needs together are $840 + $8 + $2,400 + $264 = $3,512, against the $3,400 the shop started with. Even spending all $152 on hoodies would buy only 6 (14 of 20).
- Vendor: by then vendor 1 was no longer restricted (invoice 501 was paid for ticket 101). The records do not say which vendor supplies hoodies.
- Discount: list $58, cost $22, so any price must stay above $22 (a discount below 62.1%). The database has no discount policy or approval authority, and no tool records a discount, so the agents did not invent one.
- What would be needed: a person decides the discount terms and what to offer (for example the 8 in stock), and either more cash or a smaller order. I saved nothing as "resolved" for it, and I did not approve anything for it.

### What went wrong on the way, and what I changed
Several runs ended "needs investigation" because the agents lacked information, not because of business rules. I fixed each cause and reran.
These changes affected the result, so they are listed here:
1. **`get_accounting_status` now returns `recent_payments`** (what was actually paid) and the Accounting prompt explains it. Before, agents could not tell that a proposal had been executed and kept calling it "unconfirmed" (101 run 3).
2. **Order rule stated in the Inventory, Accounting and Boss prompts:** there is no order system and agents never contact vendors, so an approved and paid `purchase_order` is the order placed, and stock stays unchanged until delivery (101 run 4). I also added the Boss rule from Problem 8: check stock first when a ticket asks for a quantity.
3. **`recent_payments` also shows each payment's `ticket_id` and `reason`** (item and quantity), because the `payments` table has no SKU; and the Boss prompt now says "resolved" for an order means the order is placed and a customer draft exists, not that goods arrived (101 run 5).
4. **Rent rule stated in the Facilities and Boss prompts:** after rent is paid the lease's `next_due` moves forward one month, which is expected and not a conflict; "resolved" for a rent notice means that installment is paid (102 run 2).
These are clarifications of how this system works, not changes to the safety rules. Tickets 101 and 102 only resolved after them, so a fresh run with the older prompts would likely stall. The supporting files were not changed in any way that affects the approval and cash rules.

### Cash reconciliation (checked against the database)
| Step | Change | Balance |
|---|---|---|
| After reset | | $3,400.00 |
| 101: pay invoice 501 (payment #1, proposal 1) | −$840.00 | $2,560.00 |
| 101: purchase order, vendor 1, 1 tee (payment #2, proposal 2) | −$8.00 | $2,552.00 (ticket 101 resolved) |
| 102: rent, lease 1 (payment #3, proposal 3) | −$2,400.00 | $152.00 (ticket 102 resolved) |
| 103: nothing approved or paid | $0.00 | $152.00 |

$3,400.00 − $840.00 − $8.00 − $2,400.00 = **$152.00**. `cash_accounts.balance` = 152.0; `payments` has 3 rows summing to $3,248.00; no proposals are pending.
A proposal never counted as a cash change until it was approved and executed. Cash was never negative.

### Verification and tests after the run
- `output/resolved_tickets.json` is valid JSON with entries for 101, 102, 103 (checked by parsing it).
- `output/desk_tickets.html`: all five tabs switch correctly in Edge, Actual sections are filled, the Expected sections are byte-identical to before (hash checked), the Cash tab shows $3,400.00 → $152.00.
- `output/resolved_board.html`: opens locally, 6 real screenshots embedded (no external paths), no sideways scroll on a phone. Files are also in `output/screenshots/`.
- `python mcp_server/test_tools.py`: 35/35 after the changes above (run on a backup, then the final working database was restored byte-for-byte and re-checked).
- **Not re-run after the prompt changes:** `backend/test_agents.py`, `backend/test_api.py` and `frontend/e2e.mjs`. They reset the working database and their expectations (for example which agents get called) may need small updates. The model check was last passed before the prompt edits.

### Known issues
- The Boss appends a note to the ticket on every run. Old notes ("proposal 2 is pending") became stale and confused later runs. A fix would be to keep only the latest note.
- Resolution of 101 and 102 depends on the prompt clarifications listed above.
- The audit trail and `agent_messages.json` still contain entries from earlier test runs (including some that name a customer's first name before that was scrubbed). They are kept because the files are append-only.
- Screenshots were taken at the moment each ticket finished; ticket 103 has no "resolved" screenshot because it was not resolved.

---

## Complete project reference (final state)

### Database (`data/campus_customs_new.db`, a working copy of the untouched `data/campus_customs.db`)
| Table | Fields | Used for |
|---|---|---|
| `desk` | `date_today`, `notes` | The shop's current date (2026-08-31). Always used instead of the real date |
| `cash_accounts` | `name`, `balance`, `date` | The `checking` account; the only money, since no revenue is modelled |
| `inventory` | `sku`, `name`, `size`, `qty`, `location` | Stock per SKU and size |
| `pricing` | `sku`, `unit_cost`, `list_price` | Cost and price, for margins and order costs |
| `vendors` | `id`, `name`, `specialty`, `lead_days` | Who can restock and how long it takes |
| `invoices` | `id`, `vendor_id`, `amount`, `due_date`, `status`, `description` | Vendor bills; an open invoice blocks new orders to that vendor |
| `leases` | `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes` | Rent; `next_due` moves forward a month when rent is paid |
| `payments` | `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by` | Ledger of executed payments (written only by `execute_payment`) |
| `tickets` | `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at` | The work items |
| `payment_proposals` (added) | `id`, `kind`, `ref_id`, `amount`, `account`, `reason`, `ticket_id`, `status`, `created_at` | Payments prepared by agents, waiting for a human (`pending_approval`, then `executed`) |
| `customer_drafts` (added) | `id`, `ticket_id`, `subject`, `body`, `status`, `created_at` | Customer messages, always `draft`, never sent |

### MCP tools (`mcp_server/server.py`, 13 tools; all shop facts and changes go through them)
| Tool | Tables | Who uses it |
|---|---|---|
| `get_inventory_status` | `inventory`, `pricing` | Inventory, Customer Service |
| `get_vendor_status` | `vendors`, `invoices` | Inventory, Accounting |
| `get_facilities_status` | `desk`, `cash_accounts`, `leases` | Facilities |
| `list_tickets` | `tickets` | API only |
| `list_open_tickets` | `tickets` | Boss |
| `get_ticket` | `tickets` | All five agents |
| `get_accounting_status` (includes `recent_payments`) | `cash_accounts`, `invoices`, `desk`, `pricing`, `payment_proposals`, `payments` | Accounting; API |
| `estimate_restock` | `vendors`, `pricing`, `invoices`, `desk` | Inventory |
| `propose_payment` (write) | writes `payment_proposals` | Accounting |
| `execute_payment` (write) | writes `payments`, `cash_accounts`, `invoices`, `leases`, `payment_proposals` | API approve route only; agents cannot use it |
| `save_customer_draft` (write) | writes `customer_drafts` | Customer Service |
| `list_customer_drafts` | `customer_drafts` | API only (the dashboard's draft panel) |
| `update_ticket_status` (write) | writes `tickets` (keeps only the latest Boss note) | Boss; API resolve route (as "Human") |

### Agents (`backend/team.py`, prompts in `backend/prompts/`; all five use `gpt-6-luna` through Portkey)
- **Boss**: reads the ticket, calls the most relevant specialist first, delegates follow-ups only when needed, checks for contradictions, decides `resolved` / `needs_human_approval` / `needs_investigation` and records it.
- **Inventory**: stock, shortages, restocking, vendor lead times and unpaid-invoice restrictions; asks Accounting before recommending a purchase.
- **Accounting**: cash, invoices, margins; checks available cash; prepares payments for human approval; confirms what has been paid.
- **Facilities**: lease and rent against `desk.date_today`; asks Accounting for payments, Inventory for stock effects.
- **Customer Service**: drafts customer messages from verified facts; drafts only.
Delegation: `ask_specialist` (any agent except the Boss can be asked; no loops; depth 3; 10 agent runs; 40 requests, 40 tool calls, 150,000 tokens per ticket).
Model: `gpt-6-luna`, Portkey `https://api.portkey.ai/v1`, OpenAI Responses API, key from `PORTKEY_API_KEY`.

### API routes (`backend/main.py`, run from `backend/`: `..\.venv\Scripts\python -m uvicorn main:app --port 8000`)
- `GET /tickets`: tickets with status, `resolved` flag and pending payments.
- `POST /tickets/{id}/run`: run the agent team on a ticket.
- `POST /tickets/{id}/resolve`: a human marks a ticket resolved (refused while a payment is pending).
- `GET /activity`: recent audit steps, what agents said, and a `running` flag.
- `POST /payments/{id}/approve`: a human approves; executes the payment in one transaction.
- `GET /cash`: checking balance, reserved, available, pending proposals.
- `GET /drafts`: the saved customer message drafts (optional `ticket_id`); they are never sent.
- `POST /reset`: restore the working database from the original (read-only source).

### React dashboard (`frontend/`, `npm run dev`, `http://localhost:5173`; see `output/design.md`)
Header with approver name and reset, summary band (balance and status counts), ticket list, and a workspace with a "Next step" line, Run button, approval panel (two clicks), a customer draft panel (the real draft text, labelled "Draft · not sent"), live agent boxes and feed, and per-agent summaries. `frontend/drive.mjs` drives it for the Problem 9 run; `frontend/e2e.mjs` is the browser test.

### Reset procedure
`python mcp_server/reset_db.py` (a plain copy of the original over the working copy), or the dashboard's "Reset test data" button / `POST /reset` (a read-only backup copy). Neither writes to `data/campus_customs.db`. Restart the backend afterward only if prompts or MCP code changed.

### Safety rules (enforced in the tools, not just the prompts)
- Agents only prepare payments (`propose_payment`); only a human's approval executes one (`execute_payment`, API only).
- Approval checks, in one transaction: proposal still pending, invoice/lease/vendor still valid, balance covers it (never negative); repeats do nothing.
- No purchase order to a vendor with an open invoice; no proposal above available cash (balance minus pending proposals).
- The shop date is always `desk.date_today`; no revenue is assumed.
- Customer messages are drafts only; no email or vendor contact; no API keys or customer details in errors or the audit trail.
- The original database is never written to.

### Files
`mcp_server/` (server, db, reset, tests, README), `backend/` (agents, API, prompts, audit, tests), `frontend/` (dashboard, tests, driver), `output/` (harness.md, design.md, desk_tickets.html, resolved_tickets.json, resolved_board.html, screenshots/, audit_trail.json, agent_messages.json, mcp_smoke.json), `AI_prompts.md`.

---

## Follow-up fixes after Problem 9

Three things were wrong or missing after the Problem 9 run. All three are fixed in the code.
The recorded results (tickets, payments, drafts, audit trail) were not changed.

1. **Customer drafts could not be read anywhere.** `save_customer_draft` wrote the text to `customer_drafts`, but no API route
   or dashboard screen showed it, even though drafts are meant to be reviewed on the dashboard. Added the MCP tool
   `list_customer_drafts` (API only, read-only), the route `GET /drafts`, and a "Customer draft" panel on each ticket.
   Tested against the real database: the panel shows draft 1 on ticket 101, draft 2 on ticket 103, and an empty state on
   ticket 102 (no customer there). The panel says "Draft · not sent". Nothing in the system can send a draft.
2. **`update_ticket_status` ignored its `set_by` label.** The parameter was added for the dashboard's "Mark resolved" but the
   note was still always written as "[Boss]". It now uses the label ("Human" for a person).
3. **Stale Boss notes.** The Boss added a new note on every run and the old ones (for example "proposal 2 awaits approval")
   stayed and confused later runs. Now only the latest "[Boss]" note is kept; the original ticket text and human notes stay.
   The notes already stored on tickets 101 to 103 were left as they are, because rewriting them would change the recorded run.

Tests: `python mcp_server/test_tools.py` is 39/39 (new checks for the draft tool, the note label and the single Boss note),
run on a backup with the final database restored afterwards. The API route and the dashboard panel were checked against the real
running backend and dashboard with read-only requests, and the database checksum was the same before and after.

Not changed and not re-run: `backend/test_agents.py`, `backend/test_api.py` and `frontend/e2e.mjs` were not re-run (they reset
the database), and no agent run was repeated. The saved drafts still have two small wording problems that the prompts have not been
changed for: draft 1 calls the product "the white CC tee" instead of Classic Bulldog Tee (`get_inventory_status` does not return
the product name), and it names the vendor and says "paid". The screenshots in `output/resolved_board.html` were taken before the draft
panel existed, so they do not show it.
