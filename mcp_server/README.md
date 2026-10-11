# MCP Server

This is the MCP server the agents use to read and change the shop's database. It is the only
way the agents touch the data. Instead of each agent writing its own database queries, they all
call the same small set of "tools" exposed here, and the server does the actual work.

It connects to `data/campus_customs_new.db`, the working copy of the shop database, and never
the original `data/campus_customs.db`. To start over, run `python mcp_server/reset_db.py`,
which copies the original over the working copy.

## Tools (13)

Read-only lookups:

- **`get_inventory_status(sku, size=None)`**: stock on hand and pricing (unit cost, list price).
  Tables: `inventory`, `pricing`.
- **`get_vendor_status(vendor_id=None)`**: vendors, restock lead time, and open (unpaid) invoices.
  A vendor with an open invoice must not receive new orders. Tables: `vendors`, `invoices`.
- **`get_facilities_status()`**: the shop's date (`desk.date_today`), cash balance, and each
  lease's rent, due date and days until due. Tables: `desk`, `cash_accounts`, `leases`.
- **`list_tickets()`**: every ticket with all its fields, whatever its status. Table: `tickets`.
- **`list_customer_drafts(ticket_id=None)`**: the saved customer message drafts, so the dashboard can show them. Drafts are never sent. Table: `customer_drafts`.
- **`list_open_tickets()`**: ids, types, subjects of open tickets. Table: `tickets`.
- **`get_ticket(ticket_id)`**: one full ticket. Table: `tickets`.
- **`get_accounting_status(invoice_id=None, sku=None)`**: each cash account's balance, the
  amount already earmarked by pending proposals, and the amount still available; open invoices
  with days overdue; and the unit margin for a SKU. Tables: `cash_accounts`, `invoices`,
  `desk`, `pricing`, `payment_proposals`.
- **`estimate_restock(vendor_id, sku, qty)`**: estimated cost (unit cost x qty), earliest
  arrival date (shop date + lead days) and whether the vendor is restricted. Tables:
  `vendors`, `pricing`, `invoices`, `desk`.

Tools that write (working copy only):

- **`propose_payment(kind, ref_id, amount, reason, ticket_id, account)`**: prepares a payment
  for human approval. It never moves money and never touches `payments` or balances. It
  refuses: a wrong invoice or rent amount, a purchase order to a vendor with an open invoice,
  a duplicate pending proposal, and any amount above available cash (so no account goes
  negative). Writes `payment_proposals`. Reads `invoices`, `leases`, `vendors`, `cash_accounts`.
- **`execute_payment(proposal_id, approved_by)`**: executes one pending proposal after a human
  approved it. Used only by the backend's approve route; agents are not given it. In one
  transaction it checks that the proposal is still pending, the invoice, lease or vendor is
  still valid, and the balance covers it (so cash can't go negative), then writes `payments`,
  lowers `cash_accounts`, marks an invoice paid, moves a lease's `next_due` forward a month, and
  marks the proposal executed. A repeat does nothing. Tables: `payment_proposals`, `payments`,
  `cash_accounts`, `invoices`, `leases`, `vendors`, `desk`.
- **`save_customer_draft(ticket_id, subject, body)`**: saves a customer message as a draft for
  the dashboard. Nothing is sent. Writes `customer_drafts`. Reads `tickets`.
- **`update_ticket_status(ticket_id, status, note, set_by="Boss")`**: records the Boss's outcome (or a human's, when the dashboard passes `set_by="Human"`). The note is labelled with `set_by`; only the latest "[Boss]" note is kept, so old notes don't go stale
  (`resolved`, `awaiting_approval` or `needs_investigation`). Writes `tickets`.

`payment_proposals` and `customer_drafts` are two small tables the server creates itself in the
working copy the first time they are needed. The original shop tables are not changed.

## Who uses what

The five agents use ten of these tools (each agent only sees the ones it needs).
`list_tickets`, `list_customer_drafts` and `execute_payment` are for the FastAPI backend only.

## Checking it

`python mcp_server/test_tools.py` resets the working copy, calls every tool over the MCP
protocol, compares results with direct SQL, and checks the business rules above. It leaves the
working copy reset when it finishes.
