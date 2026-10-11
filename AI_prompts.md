# AI Prompts Log — Homework 5: Campus Customs Multi-Agent Operations

This file logs the prompts entered to Claude Code for each problem in the assignment.

## Problem 1: Vibe coder prompts

- "Create a file AI_prompts.md in the folder to keep track of the prompts entered to Claude Code for each problem. Create the following main headings for each problem, after which you'll log the prompts pertinent to each problem under:
Problem 1: Viber coder prompts
Problem 2: Study the Campus Custom database
Problem 3: Build the MCP server
Problem 4: Add the MCP server to vibe coder and test each tool
Problem 5: Build the agent team and grow the MCP tools
Problem 6: Plan the three tickets
Problem 7: Backend routes
Problem 8: Agent Dashboard
Problem 9: Resolve the tickets
Problem 10: Reflections
Problem 11: Submit to github"

## Problem 2: Study the Campus Custom database

- "I think the main thing here is to understand how the database is set up before we start building the rest of the site and agent.
Please open data/campus_customs.db and go through all the tables and their fields. Also look at the 3 open tickets and see how they connect to the other tables, so we understand how the data links together.
Make a copy of the original database called data/campus_customs_new.db. We'll use this new copy for the later problems that need to update the database, so dont modify the original one.
Then start updating output/harness.md. For each table, list its fields and add a short explanation of why that table matters for the agent. We'll keep adding to this file as we go through the other problems, so dont overwrite anything useful that's already there.
I'm not super familiar with database stuff, so keep the explanation simple and focus on what each table is for and how the agent might use it later."

## Problem 3: Build the MCP server

- "now lets do problem 3. I think this is where we start building the MCP server that the agent will use to access the database, so pls keep it simple and build on what we did in problem 2
Create an MCP server in mcp_server/ using FastMCP. It should connect to data/campus_customs_new.db, not the original database. We dont need to actually connect or run it yet for this problem, just get the server and tools set up.
For now, add 3 useful tools that we will probably need for the open tickets in the database. Please look at the actual tables and ticket details first so the tools match the data we have, rather than guessing what might be useful. Give the tools clear names and make sure they only return information that exists in the database, never inventing any data.
I'm not totally sure how best to structure the tools yet, so use your judgement but dont overcomplicate it. The idea is that every agent we build later will use tools from this MCP server, and we'll keep adding more tools in later problems.
Also update output/harness.md with a short expalnationa of the MCP server, the 3 tools, what each one does and why its useful for the tickets. Keep any existing notes from problem 2, we're going to keep building on this file."

- "Sorry also for problem 3, create mcp_server/README.md with a short explanation of what the MCP server is for, which database file it uses, and the 3 tools it provides. Keep it simple so someone can understand it without knowing much about MCP.
Dont overcomplicate things, we will add more tools and connect the agents later."

## Problem 4: Add the MCP server to vibe coder and test each tool

- "do problem 4. I think this step is about connecting the MCP server we built in problem 3 to Claude Code (or whichever vibe coder we're using) so it can actually call the tools and test them. I'm not totally sure about the connection setup, so pls use the simplest approach that works with my current project structure.
Please add the MCP server to this project so the vibe coder can access all 3 tools. Save the connection settings in a .mcp.json file at the project root, or use the correct local config format if the tool requires something different. Make sure it points to the server we already built in mcp_server/ and uses data/campus_customs_new.db, not the original database.
Once it's connected, test each of the 3 tools through the vibe coder itself, not just by calling the Python functions directly. For each tool, save evidence in output/mcp_smoke.json. Include the exact prompt you gave the vibe coder, the tool name it called, and the actual output it returned. The output needs to match the values in data/campus_customs_new.db, so pls double check that we're not just making up results.
Also update output/harness.md with a short note explaining how the MCP server was connected, how to start it if needed, and how each tool was tested.
Keep it simple and dont change the existing tools unless something is actually wrong."

## Problem 5: Build the agent team and grow the MCP tools

- "ok finally problem 5 now. We need to build the 5-agent team for Campus Customs using PydanticAI, building on the MCP server and tools we already created.

Please first inspect the existing project, database schema, open tickets, MCP tools and assignment requirements so we can build on what is already there. Keep the current structure and working code where possible.

I want 5 agents: Boss, Inventory, Accounting, Facilities, and Customer Service. I've decided on the responsibilities and workflow below, so please implement this design rather than coming up with a different architecture.

The Boss is the coordinator. It should read each ticket, identify the main issue, call the most relevant specialist first, and delegate follow-up work only when needed. It should combine the specialists' findings, check for contradictions or missing information, and decide whether the ticket can be resolved, needs human approval, or needs more investigation. It must not automatically call every agent for every ticket.

The Inventory agent handles stock levels, shortages, and restocking. It should check inventory records and vendor details, calculate whether a restock is needed, consider vendor lead times, and flag vendors with outstanding unpaid invoices. It should ask Accounting to check financial feasibility before recommending a purchase that commits shop money. It must not invent stock levels, promise unavailable items, or place orders with restricted vendors.

The Accounting agent handles cash balances, invoices, margins, and payment preparation. It should verify the relevant financial records before recommending a payment or purchase order, check that enough existing cash is available, and make sure the proposed payment would not leave any cash account negative. It can prepare a payment for human approval but must never execute a payment without that approval. The system does not model revenue, so agents must not assume new cash will arrive to cover a payment.

The Facilities agent handles shop space, leases, rent, and facility issues. It should check the relevant lease and rent records and use `desk.date_today` as the current date when assessing overdue items. If a facilities issue requires a payment decision, it should ask Accounting for help. If it affects stock or vendor deliveries, it should coordinate with Inventory.

The Customer Service agent turns confirmed findings into clear, friendly customer-facing responses. It should use facts verified by the other agents and the database, explain delays or limitations honestly, and keep all messages as drafts for review in the dashboard. It must never send emails or contact customers or vendors directly.

All five agents should have their own prompt files under `backend/prompts/`, with instructions specific to their responsibilities, tools, decision-making, delegation rules, and safety limits. Put shared data types in `backend/models.py` and agent implementation under `backend/`. Keep the structure understandable and avoid unnecessary complexity.

Implement the delegation rules so agents can ask each other for help when needed, but keep the Boss responsible for overall coordination and the final ticket outcome. Pass only the relevant ticket details and specialist findings between agents instead of repeatedly sending the entire conversation or database records.

All shop facts and database changes must go through the existing MCP server and `data/campus_customs_new.db`. Do not create a separate backend database-tool layer that bypasses MCP. Inspect the existing tools first, then add only the missing tools needed for these workflows. Verify tool results against the actual database and update `mcp_server/README.md` to match the tools we really have.

Use the model permitted by the assignment, with all agent calls routed through Portkey using `PORTKEY_API_KEY`. All five agents must use the same model configuration. Do not hardcode API keys. Check the actual assignment and current configuration before choosing the model rather than assuming a model name is valid.

Add an append-only audit trail at `output/audit_trail.json`. Record each agent-loop step with a timestamp, agent name, tool used if applicable, a short summary of arguments or results, and whether the agent finished, delegated, or needs human approval. Do not log passwords, private customer information, or large raw outputs. Existing audit entries must be preserved across runs.

Finally, update `output/harness.md` to document all five agents, their responsibilities, every MCP tool and the database tables it uses, the delegation workflow, safety rules, model configuration, and limits on agent loops and token use.

Please test the agent connections and MCP calls, and verify the important business rules against the actual database. If something is blocked or cannot be tested, explain that clearly instead of claiming it works."

- UPDATE / override of the Problem 5 prompt above (the old prompt is kept):
"ok lets do problem 5 now. We need to build the 5-agent team for Campus Customs using PydanticAI, building on the MCP server and tools we already made.

One important thing about the model setup: even though I'm using Claude Code to help me build this project, the agents inside the application must use `gpt-6-luna` through Portkey, exactly as required by the assignment. Please dont substitute Claude or another model just because we're using Claude Code. All 5 agents must use the same model and configuration, with `PORTKEY_API_KEY` loaded from the environment. Dont hardcode the key anywhere. Make sure the actual PydanticAI and Portkey configuration is correct for this model, and dont just put the model name in a comment or config without wiring it up properly.

Please first inspect the existing project, database schema, open tickets, MCP tools and current configuration so we can build on what is already there. Keep working code where possible.

I want 5 agents: Boss, Inventory, Accounting, Facilities, and Customer Service. I've decided on the responsibilities and workflow below, so please implement this design rather than coming up with a different architecture.

The Boss is the coordinator. It should read each ticket, identify the main issue, call the most relevant specialist first, and delegate follow-up work only when needed. It should combine the specialists' findings, check for contradictions or missing information, and decide whether the ticket can be resolved, needs human approval, or needs more investigation. It must not automatically call every agent for every ticket.

Inventory handles stock levels, shortages, and restocking. It should check the actual inventory records and vendor details, consider vendor lead times, and flag vendors with outstanding unpaid invoices. It should ask Accounting to check financial feasibility before recommending a purchase that commits shop money. It must not invent stock levels, promise unavailable items, or place orders with restricted vendors.

Accounting handles cash balances, invoices, margins, and payment preparation. It should verify the relevant financial records before recommending a payment or purchase order, check that enough existing cash is available, and make sure the proposed payment would not leave any cash account negative. It can prepare a payment for human approval but must never execute a payment without that approval. The system does not model revenue, so agents must not assume new cash will arrive to cover a payment.

Facilities handles shop space, leases, rent, and facility issues. It should check the relevant lease and rent records and use `desk.date_today` as the current date when assessing overdue items. If a facilities issue requires a payment decision, it should ask Accounting for help. If it affects stock or vendor deliveries, it should coordinate with Inventory.

Customer Service turns confirmed findings into clear, friendly customer-facing responses. It should use facts verified by the other agents and the database, explain delays or limitations honestly, and keep all messages as drafts for review in the dashboard. It must never send emails or contact customers or vendors directly.

Each agent needs its own detailed prompt under `backend/prompts/`, written in straightforward language and specific to its responsibilities, tools, decisions, delegation rules and safety limits. Put shared data types in `backend/models.py` and the agent code under `backend/`. Keep the structure clear and avoid unnecessary complexity.

Implement the delegation rules so agents can ask each other for help when needed, with the Boss responsible for overall coordination and the final ticket outcome. Pass only the relevant ticket details and findings between agents instead of repeatedly sending entire conversations or large database records.

All shop facts and database changes must go through the existing MCP server and `data/campus_customs_new.db`. Do not create a separate backend database-tool layer that bypasses MCP. Inspect the existing tools first, then add only the missing tools needed for the tickets. Verify tool results against the actual database and update `mcp_server/README.md` to match the tools we really have.

Add an append-only audit trail at `output/audit_trail.json`. Record each agent-loop step with a timestamp, agent name, tool used if applicable, a short summary of arguments or results, and whether the agent finished, delegated, or needs human approval. Dont log passwords, private customer information, or huge raw outputs. Existing audit entries must be preserved when the app restarts.

Finally, update `output/harness.md` to document all 5 agents, their responsibilities, every MCP tool and which database table it uses, the delegation workflow, safety rules, the exact model and Portkey configuration, and the limits on agent loops and token use.

Please test the actual model connection, agent delegation, and MCP calls where possible. If the specified model or Portkey configuration fails, report the exact issue instead of silently switching to another model. Keep everything consistent with the assignment and explain what works and anything that still needs fixing."


## Problem 6: Plan the three tickets

- "If all good then start Problem 6. Before changing anything, pls check the existing project and see what we already built in problems 2–5. I dont want us to rewrite working stuff or assume things about the database without checking first.

For this problem, I want to create `output/desk_tickets.html`. It should be a simple page I can open in my browser, with tabs for tickets 101, 102, 103, plus Cash and Reflection tabs for later. Cash and Reflection can just say coming later for now.

For each ticket, fill in the Expected section only and leave the Actual section empty for us to fill in after we run the agents. I want the Expected section to explain how we think the team should handle the ticket before testing what the agents actually do.

I've decided that each ticket plan should cover 3 things: which agent the Boss should call first and why, the expected delegation steps between agents and why they need to pass work to each other, and which MCP tools we expect them to use.

Please inspect the actual ticket records, database schema, existing MCP tools, `output/harness.md` and `mcp_server/README.md` before writing the plans. The plans need to be specific to tickets 101, 102 and 103, so dont invent ticket details or tools that dont exist.

Use your judgement to work out the expected workflow for each ticket. For example, start with the specialist best suited to the main issue, then only involve other agents if the ticket needs their input. Inventory should be involved for stock or restocking questions, Accounting for cash/invoices/payments, Facilities for leases or rent, and Customer Service when we need a customer-facing draft. The Boss should coordinate the work and decide the final outcome, not just call everyone automatically.

For each ticket, write the plan in straightforward student language. Explain the reasoning, not just a list of agent names. Include the actual MCP tool names that fit the ticket and what information we expect each tool to provide. If a tool we expected to use doesn't exist, dont make up a name for it. Note the gap so we can address it later.

Keep the page easy to read, with a separate tab for each ticket and the Expected and Actual sections clearly separated. The Actual sections should stay blank for now, since we'll compare them with the real agent runs later.

Once the page is done, update `output/harness.md` with a short note explaining what `desk_tickets.html` is for and that the Expected plans are our predictions, while the Actual sections will be completed after testing.

Please keep the existing project structure and working code intact. This problem is about documenting our expected ticket workflows, not implementing the full ticket-resolution system yet. Test that the HTML page opens correctly and make sure the tab navigation works."


## Problem 7: Backend routes

- "Let's get onto problem 7 now. This is where we need to connect the agent team we built to a FastAPI backend so the React dashboard can actually use it.
Before changing anything, pls check the existing code from problems 2–6 and build on what we already have. I dont want us to end up with a second agent system or duplicate database logic.
In backend/main.py, add the FastAPI routes the dashboard needs:
1. A route to return tickets 101, 102 and 103, including whether each ticket is open or resolved.
2. A route that takes a ticket ID and runs our existing agent team on that ticket.
3. A route to return recent agent activity, including what each agent said and which tools it used, so the dashboard can refresh and show what happened.
4. A route to approve a payment or purchase after a human clicks approve. The agents should only prepare the payment; this route should handle the actual approval and database updates.
5. A route to return the current checking account balance from cash_accounts.
6. A route to reset the working database to its original values so we can test the tickets again from a clean state.
Pls use the existing agent and MCP setup rather than reimplementing their logic inside the API routes. For the reset, use the untouched original database as the source and restore data/campus_customs_new.db from it. Never overwrite data/campus_customs.db.
For the approval route, be especially carefull with money. Check that the payment or purchase is actually pending approval, verify the available cash before executing it, and make sure the balance cant go negative. The database updates should be consistent, and the approval shouldnt be executed twice if the request is repeated. If something is invalid, return a clear error instead of silently changing the database.
Also make sure the API returns useful errors for invalid ticket IDs, missing records, and agent failures. Dont expose API keys or sensitive customer info in errors or logs.
The backend should run from the backend/ folder with:
uvicorn main:app --reload --port 8000
Finally, update output/harness.md with each route on one line, explaining its URL and what it does. Keep the documentation consistent with the routes that actually exist, and test the endpoints where possible. If anything cant be tested yet because another component isnt ready, pls say so instead of pretending it works."


## Problem 8: Agent Dashboard

- "ok lets do problem 8 now. I want to build the React dashboard in `frontend/` using the backend routes we made in problem 7. Please inspect the existing frontend + backend first and build on what we already have instead of creating duplicate routes or fake data.

For the design, I've decided to go with a muted Bauhaus-inspired style. I want it to look thoughtful and a bit distinctive, but still be really easy to understand the first time someone opens it. Think warm off-white background, dark charcoal text, muted navy/blue as the main accent, and small touches of terracotta or mustard for status and alerts. Use a clean grid, simple geometric shapes, thin borders, strong typography and mostly flat colors. No gradients, flashy animations, or lots of competing colors. The design should feel like a calm, well-organized operations desk, not a generic SaaS dashboard.

 I'd suggest a clear top header, a compact summary of the checking balance and ticket status, a ticket list where I can easily pick ticket 101, 102 or 103, and a main workspace showing the selected ticket, agent activity and any pending approval. Keep the most important actions obvious, especially running a ticket and approving a payment. Dont make the user hunt around to figure out what to click first.

The dashboard needs to support all of these things:

- Show all 3 tickets and whether each is open or resolved
- Let me select a ticket and start the agent team on it
- Show which agent is working and what it is doing while the ticket runs
- Show a short summary of what each agent did
- Mark the ticket resolved when the run finishes
- Let me approve a payment or purchase when human approval is needed
- Show the current checking balance and refresh it after an approved payment

Please connect the frontend to the FastAPI backend at `http://localhost:8000`, and make sure the backend allows requests from the Vite frontend at `http://localhost:5173` through CORS. Use the real routes from problem 7, not hardcoded sample results. If a route or feature isn't ready yet, tell me rather than faking it.

Make the navigation obvious and keep the interface readable at a glance. Use status text as well as color so people dont have to rely on color alone. Add sensible loading, empty and error states, and make sure the layout still works on a smaller screen. Keep animations subtle and only use them if they help show that something is happening.

Finally, write `output/design.md` explaining the dashboard's visual direction, layout, color choices, how we made agent activity and resolved tickets easy to follow, and why the design should feel distinctive but still intuitive. Keep it short and specific to what we actually implemented.

After building it, run the frontend and test the main flows against the backend: loading tickets, starting an agent run, viewing activity, approving a pending payment, and refreshing the checking balance. Fix any obvious issues you find, and be honest about anything that can't be tested yet."


## Problem 9: Resolve the tickets

- "k lets do problem 9 now. before running the agents, review the existing code and everything we built in previous problems, especially the MCP tools, all five agent prompts and their implementation, the API routes, the React dashboard, `output/desk_tickets.html`, `output/harness.md`, and `output/audit_trail.json`. follow the assignment requirements and use the actual database records and tool outputs. dont invent results or assume a ticket is resolved just because the UI says so.

first, reset `data/campus_customs_new.db` to the original clean state by copying `data/campus_customs.db` into it. **never modify `data/campus_customs.db` itself.** record the starting checking balance from `cash_accounts` in the working database before doing anything else. make sure the reset actually worked and the working database is the one connected to the MCP server and backend.

then run all three tickets on the React dashboard: 101, 102, and 103. run each ticket through the actual agent workflow and continue until every ticket is resolved, following the assignment's approval and safety rules. dont fake agent runs, directly update ticket statuses to make the board look resolved, or bypass MCP to make database changes. agents should do the work through the tools and API we built; any payment or purchase that requires human approval must go through the dashboard's approval flow. if an approval is required, make the decision based on the available facts, the current cash balance, the ticket requirements, and the safety rules. dont approve something if the funds or supporting information are insufficient. if you cant safely resolve a ticket, explain exactly why rather than forcing it through.

while running the tickets, pay attention to what actually happens: which agent starts, which other agents get called, what each agent contributes, which MCP tools are used, what gets delegated, what decisions are made, and whether any human approval was needed. verify the final status and outcome from the actual backend/database, not just from what the agent claims. keep the existing append-only `output/audit_trail.json` and append the real events from these runs; dont erase earlier entries or log secrets, huge raw outputs, or private information.

once all three tickets have been processed, open `output/desk_tickets.html` from problem 6 and update the Actual section on each ticket tab with the real results from this run. include which agents worked, the delegation sequence, what each agent did, and which MCP tools were actually used. **keep the Expected section unchanged** so the two can be compared. on the Cash tab, itemize:
- the starting checking balance immediately after the reset
- for each ticket, how the checking balance changed when it was resolved, including the specific payment or purchase, the dollar amount, and why the money changed
- the ending checking balance, verified against `cash_accounts` in `data/campus_customs_new.db`

show the math clearly from start to finish and make sure the figures reconcile exactly with the working database. dont assume every resolved ticket changes cash, and dont count a proposed payment or purchase as an actual cash change unless it was really approved and executed.

also create `output/resolved_tickets.json`. include one entry for each of tickets 101, 102, and 103, with the ticket id, final status, short outcome, agents that contributed and what each one did, and any human approvals that occurred. use the actual run results, not expected plans or guesses. keep the JSON valid and easy to read.

create `output/resolved_board.html` as a standalone HTML page that i can open directly in a browser. it should contain a screenshot of the actual React dashboard showing all three resolved tickets, with a screenshot for each ticket (101, 102, and 103). use real screenshots captured from the running React board after each ticket is resolved. dont make up screenshots, create fake UI images, or just write a description instead of capturing the actual board. if the dashboard only shows the final state after all three tickets are resolved, capture that real final state and include it for each ticket with a clear label, unless you can capture the board at each individual ticket's resolved state during the run. make sure the HTML opens locally and the screenshots are embedded or referenced using paths that work when i open the file. if the environment does not support capturing real screenshots, tell me clearly and document the limitation rather than pretending the file contains them.

finally, update `output/harness.md` so it covers the complete project and the actual results of problem 9. make sure it includes the database tables and fields, the MCP tools, all five agents and their responsibilities, API routes, the React dashboard, the reset procedure, the safety rules, the three ticket outcomes, the actual agent/tool flows, and the cash reconciliation. keep existing useful notes and append or revise sections without deleting earlier work. verify every deliverable exists, check the JSON is valid, confirm the cash math matches the database, and report any issues honestly. dont claim a task succeeded unless you actually tested it."


## Problem 10: Reflections

- "Include the write-up below in the Reflection tab."

Write-up placed in the Reflection tab of output/desk_tickets.html (drafted by Claude Code from the Problem 10 instructions, copied here verbatim from the tab):

### Reflection

Campus Customs is a team of five agents (Boss, Inventory, Accounting, Facilities and Customer Service) that handles the shop's tickets, and I made the main design decisions myself. I decided what each agent is responsible for, that the Boss should not call every agent on every ticket, that any specialist can ask another one for help, that all shop data has to go through a single MCP server, that the audit trail only grows and never gets rewritten, that the dashboard should have a muted Bauhaus look, and that the agents run on gpt-6-luna through Portkey. I also set the safety rules: no payment without a human approval, cash can never go negative, and customer messages stay as drafts. Claude Code wrote the code, the MCP tools, the agent prompts, the API and the dashboard from my instructions, and it ran and tested everything.

I ran the three tickets on 2026-10-10 with the shop date at 2026-08-31. Checking started at $3,400.00 and finished at $152.00, tickets 101 and 102 ended as "resolved", and ticket 103 ended as "needs_investigation". Everything below comes from the three ticket tabs, the Cash tab, "resolved_tickets.json", the audit trail, "harness.md" and the code. The three payments ($840.00, $8.00 and $2,400.00) were approved on the dashboard by Claude Code, because I gave it a rule to approve only when the facts, the cash balance and the safety rules supported it, and the "payments.approved_by" column says "Claude (acting for Vy)". Approvals are particularly important in a system like this, so in a real shop I would click them myself.

### 1. How would I evaluate the agents on each ticket, and why?

I would not grade an agent by what it says, because all of them sound sure of themselves even when they are wrong. For each ticket I look at whether the database supports the final status, whether money only moved through an approval, whether the numbers the agents gave match the tool results, how many runs and steps the ticket took, and whether the customer draft is honest. The audit trail has steps and timestamps but no token counts, so I can only compare steps and seconds and I cannot say anything about the real token cost.

#### Ticket 101 (Bulldog tee)

The outcome is real, because in the database invoice 501 has the status "paid", the "payments" table has #1 for $840.00 (the invoice) and #2 for $8.00 (a purchase order to vendor 1), the ticket is "resolved", and customer draft 1 has the status "draft". Cash went from $3,400.00 to $2,560.00 and then to $2,552.00. Accounting contributed the most, since it prepared both payments with "propose_payment", while Inventory found the real blocker in the first run by using "get_vendor_status" and "estimate_restock" and seeing that vendor 1 was restricted by invoice 501. The first run went from Boss to Inventory to Accounting, which is the chain I wanted, so the delegation there was useful. The Boss mostly passed questions along and wrote the status, and Customer Service only showed up in run 6.

After the first run it went badly. The ticket took 6 runs, 130 audit steps and about 273 seconds of agent time (15, 97, 40, 43, 44 and 34 seconds), and runs 3, 4 and 5, which together took about 127 seconds, ended as "needs_investigation" even though the payment had already been made. In run 2 alone the Boss asked Accounting twice and Inventory twice. This was a gap in my design more than a failure of the agents, because "get_accounting_status" only showed pending proposals, so nobody could see that proposal 2 had been executed or what the $8.00 had bought. Claude Code added "recent_payments" to that tool and clarified some prompt rules while it followed my instruction to keep going without forcing anything, and only after that did the ticket resolve. I still need to go through those four changes myself before I submit, because the ticket resolved partly after we fixed the system while watching it fail, which is a bit like teaching to the test.

There is also a difference between what was said and what was done. Draft 1 says "We've placed and paid for an order for one tee with Bulldog Print Co", but what the system actually did was write one row in "payments" (#2, $8.00). Nothing was sent to Bulldog, because we never contact vendors on purpose, and the quantity for tee size S in "inventory" is still 0. "Order placed" is just a rule I wrote into the prompts. In the same way the Boss marked the ticket as resolved even though the customer has no tee yet, because the rule says resolved means the order is paid and a draft is saved. I think that is defendable, but it is a definition and not a fact. The draft also calls the product "the white CC tee" instead of the Classic Bulldog Tee, because "get_inventory_status" does not return the product name, and that is still not fixed.

#### Ticket 102 (rent)

This was the best of the three. Run 1 took 12 audit steps and 25 seconds, going from Boss to Facilities and then to Accounting. Facilities read lease 1 with "get_facilities_status" ($2,400.00, next due 2026-09-02, which is two days after the shop date), Accounting made proposal 3 with "propose_payment", and Inventory and Customer Service were not called, which is what I wanted. After the approval, cash went from $2,552.00 to $152.00, and the database shows payment #3, the lease "next_due" at 2026-10-02 and the ticket as "resolved".

Accounting did the most work again, while Facilities mostly confirmed a date the ticket already told us, which is useful as a check but not much work. Run 2 took 23 steps and 51 seconds and ended as "needs_investigation", because after the payment the lease date moved forward a month and the agents thought the ticket and the lease disagreed. Facilities cannot see payments and Accounting cannot see leases, so the question went back and forth five times. Run 3 took 11 steps and fixed it, but only after a prompt rule about "next_due" moving was added. Nobody replied to the landlord either, which is by design since there is no tool for it, but it is still a loose end.

#### Ticket 103 (hoodie discount)

This ticket was not resolved, and I think that was the right result. It took one run of 23 steps and 53 seconds, going from Boss to Inventory first, then Accounting, then Customer Service, and ending with a draft. The numbers match the database: 8 of the 20 size M hoodies are in stock, 12 more hoodies at $22.00 come to $264.00 according to "estimate_restock", only $152.00 was available so the shop was $112.00 short, and a margin of $36.00 (62.1%) means any price has to stay above $22.00. Nothing was proposed or paid, the status stayed at "needs_investigation", and cash never went negative, so the team did not force the ticket through.

There were weak points as well. Accounting asked Customer Service about the discount policy, which was a wasted step because Customer Service owns no policy and the database has none. Nobody pointed out that $152.00 would still buy 6 hoodies ($132.00), which would have let us offer 14 of the 20, and I only worked that out afterwards. The good behavior here also depends on one sentence I added to the Boss prompt about checking stock first, because in an earlier test run the Boss skipped Inventory completely and called the outcome "needs human approval" when there was no payment. I have only seen it work correctly on one final run, so I would not call it reliable yet.

### 2. How did Actual compare to the Expected plan on each ticket?

#### Ticket 101

Several parts of my prediction were right: Inventory went first, Inventory asked Accounting, the invoice 501 proposal needed a human approval, Customer Service came last with a careful draft, Facilities was not called, and all eight tools I listed were used ("get_ticket", "get_inventory_status", "get_vendor_status", "estimate_restock", "get_accounting_status", "propose_payment", "save_customer_draft" and "update_ticket_status"). What I got wrong was expecting one approval and a ticket that would stay open until the tee arrived. In reality there were two approvals, $840.00 and then the $8.00 purchase order, which could only be proposed after invoice 501 was paid. I actually wrote that down in the gaps list but did not count it as a second approval. There were also six runs, Customer Service only appeared in run 6, and the Boss resolved the ticket even though the tee has not arrived.

#### Ticket 102

Run 1 was almost exactly the plan, with Facilities first and then Accounting, no Inventory, no Customer Service, and the five tools I predicted ("get_ticket", "get_facilities_status", "get_accounting_status", "propose_payment" and "update_ticket_status"). I predicted $160 would be left if ticket 101 went first, and the actual figure was $152.00, with the $8.00 difference coming from the purchase order I forgot to count. What I did not predict at all were the extra runs after the approval. I treated the approval as the end of the ticket, but the agents had to be run again to notice that it was paid, and the moving "next_due" confused them.

#### Ticket 103

The prediction was right that Inventory would go first and Accounting second, that the restock would cost $264.00 with a margin of $36.00, that Customer Service would save a draft, that "propose_payment" would not be used, and that the outcome would be needs investigation. It was wrong about the vendor and the cash, because I said vendor 1 would still be blocked by the unpaid invoice and that cash would be $160. By the time ticket 103 ran, invoice 501 had been paid for ticket 101, so vendor 1 was fine and the real blocker was cash, at $152.00 against $264.00. I also did not expect Accounting to ask Customer Service anything.

Overall, who gets called was almost exactly what I predicted, which is not surprising because I decided the tool lists and the prompts that force that shape (Facilities cannot call "propose_payment" and Customer Service has no cash tools). What I got wrong was the shared state. The three tickets share one cash balance and one vendor status, so the order of the tickets effects the result, and I wrote the plans as if they were mostly independent. I also underestimated how much the agents need to verify what has already happened.

### 3. What would have been simpler as one agent with tools?

Ticket 102 is the clearest example, because the whole job is five tool calls: "get_ticket", "get_facilities_status", "get_accounting_status", "propose_payment" and "update_ticket_status". One agent holding those tools could do it in about five steps, while run 1 took 12 audit steps with two delegations. The bigger waste was run 2, which used five delegations and 23 steps to answer "was it paid and why did the date move", something a single agent would see immediately by calling "get_accounting_status" (which has "recent_payments") and "get_facilities_status" together. In my design the split of information caused the confusion, since Facilities only had the lease and Accounting only had the money, and that was my choice when I divided up the tools.

The middle of ticket 101 is similar. Inventory asking Accounting whether the shop can afford $8.00 is mostly a pass-through, and in runs 2 to 5 the agents kept asking each other the same questions. One agent with "get_vendor_status", "get_accounting_status" and "propose_payment" could have gone from "vendor blocked by invoice 501" to "propose the $840.00 payment" without any handoff.

I never ran a one-agent version, so this is reasoning and not a measurement. The hard rules (no purchase order to a vendor with an open invoice, no proposal bigger than the available cash, and payments only executed through the approval route) are enforced inside the MCP tools, so a single agent would be just as safe on those. What separate agents add is smaller tool lists and focused prompts, so Inventory cannot spend money and Customer Service cannot touch payments. The best example is the customer writing, because neither draft mentions our cash balance or the unpaid invoice (draft 1 does say we paid for an order, which is a bit more than the customer needs). A single agent that holds "save_customer_draft" and has just read $152.00 and invoice 501 could easily leak internal things into the message. A single agent could also skip a check, like the Boss skipping the stock check on ticket 103 in my earlier test, but more agents did not remove that risk, a prompt rule did.

My answer is that routine tickets that stay in one area, like 102 and the payment part of 101, would be simpler with one agent. I would keep Customer Service separate, and probably the Boss's final status decision too, so that whoever writes to the customer is not the one handling the money.

### 4. Three new problems the current team could solve

For all three problems the ticket or invoice would have to exist as a row in the database first, because we have no tool that creates tickets or invoices, so I am assuming someone adds them.

#### A. A student club wants 30 Yale Caps

The club orders 30 caps ("CC-HAT-BLUE", one size). The Boss would ask Inventory first, and "get_inventory_status" shows 40 in stock, so the order can be filled. Accounting would then call "get_accounting_status" with the SKU to get the cost of $6.00, the list price of $22.00 and the margin of $16.00 (72.7%), so the Boss knows the lowest sensible price, and Customer Service would write the reply with "save_customer_draft". No money moves, so no approval is needed. The limit is that we still have no discount policy, the same hole as in ticket 103, so the team could give a price floor but could not set a discount.

#### B. A customer orders mugs and we have none

Someone wants 10 Crest Mugs ("CC-MUG-CREST") and the quantity is 0. Inventory would find vendor 2, Elm City Gifts (mugs and small goods, a 3 day lead time and no open invoice), with "get_vendor_status", and "estimate_restock" would give 10 x $3.50 = $35.00 with an earliest arrival of 2026-09-03 if it is ordered on the shop date. Inventory would then ask Accounting, which checks "get_accounting_status" and prepares a purchase order with "propose_payment". A person approves it on the dashboard ("execute_payment"), and Customer Service drafts the reply with a conditional date. With the $152.00 we have now, up to 43 mugs would be affordable ($150.50). The limit is that it only counts as "ordered" because of our own rule, the same as in ticket 101.

#### C. A vendor bill goes overdue and blocks restocking

Say Elm City Gifts has an open invoice for $120.00 that is overdue (this is hypothetical, because no such invoice exists in our database). The Boss would start with Accounting this time, which we did not see in the three tickets. "get_vendor_status" shows the open invoice and "get_accounting_status" shows how many days overdue it is and whether the cash covers it. Accounting prepares the payment with "propose_payment", a person approves it, and Inventory then sees through "get_vendor_status" that the vendor can be ordered from again, which unlocks problem B. The limit is that the team can prepare and check this, but only if the invoice row already exists.

### 5. Three new problems the current team could not solve

#### A. Really ordering stock and tracking the delivery

In ticket 101 our "order" is only the $8.00 row in "payments". Nothing contacts Bulldog Print Co, "estimate_restock" is just date arithmetic (the shop date plus the lead days), and the tee size S quantity is still 0 because nothing records a delivery. The agents even got stuck for three runs asking for a confirmation that does not exist, and vendor 3, QuickShip CT (a local courier), sits in the "vendors" table without any workflow using it. To solve this I would add an orders table (SKU, quantity, vendor and status), a Procurement and Receiving agent, and tools like "place_vendor_order" (a draft that a person approves before it is sent), "track_shipment" and "record_receipt", which would raise "inventory.qty". Today the team only recommends and pays on paper, and it does not carry the order out in the real world.

#### B. Moving real money, or refunding a customer

"execute_payment" only edits our SQLite file, with one row in "payments" and a lower "cash_accounts.balance", so the move from $3,400.00 to $152.00 is a number in a database and not a bank. There is no connection to a bank or card system, and a refund would also need to know what the customer paid, but there are no orders or sales tables and the shop models no revenue at all, which is also why ticket 103 ended $112.00 short with no way to fix it. I would add a Payments agent with a bank or Stripe tool (for transfers and refunds, with an idempotency key so a double click cannot pay twice), a sales and orders table, and a reconciliation tool that compares the bank with "cash_accounts". Accounting would keep preparing proposals, and a separate, tightly limited step would do the real transfer after a person approves it.

#### C. Handling customer emails from start to finish

The tickets came already inside the database (from data.zip), the "tickets" table has no email address column, and nothing reads an inbox. Customer Service saves drafts into "customer_drafts", and they can now be read on the dashboard (a "GET /drafts" route and a draft panel were added after we saw that nobody could read them before), but nothing sends them, and for the landlord email on ticket 102 there is not even a draft, since Customer Service is only meant for customers. I would add an Inbox agent with a "read_inbox" tool that turns emails into tickets and stores the sender's address, and a "send_email" tool that only works after a person approves a specific draft. Right now the team writes a suggestion and never talks to a customer.

#### What I am not sure about

I did not run a single-agent version, so my answer to question 3 is reasoning and not a measurement. The audit trail has no token counts. With only ten team runs, and one run of ticket 103 on the final prompts, I cannot say how stable the good results are, because the agents do not behave the same way every time.

## Problem 11: Submit to github

- "before doing anything for problem 11, please read the assignment instructions below carefully. do not start this problem yet. the assignment specifically says not to do it until i ask in my own words what i want done. for now, just understand the requirements and wait for my next message.

when i give you the go-ahead, help me publish our completed Campus Customs project to a public GitHub repository so the graders can clone it and run the app. follow these requirements:

inspect the entire project and compare the actual folder structure with the expected layout in the assignment screenshot that i will send you separately. check which files and folders are present, missing, or named differently. dont assume the project is ready just because earlier problems were completed.

make sure the repository includes the required project files, including both data/campus_customs.db (the original database) and data/campus_customs_new.db (the working copy). preserve the original database and do not accidentally overwrite it with the working copy.

never commit a real .env file or any API keys, credentials, tokens, or other secrets. check .gitignore carefully, make sure .env is excluded, and include .env.example with placeholder values only. also check that secrets have not already been tracked by Git or included in earlier commits. if any real secret was exposed, flag it and explain the appropriate cleanup instead of ignoring it.

prepare a clear README.md explaining how to set up and run the project from a clean clone. it must explain:

how to copy the original database to data/campus_customs_new.db when we need a clean run

how to configure environment variables using .env.example without exposing real credentials

how to start the MCP server

how to start the FastAPI backend

how to start the React/Vite dashboard

how to reset the working database before running all three tickets

any required dependencies, setup commands, and relevant ports

verify these instructions against the actual code and configuration. dont invent commands or assume ports if the project uses different ones.

preserve all the assignment deliverables, including the agent prompts, backend, frontend, MCP server, requirements, configuration files, and relevant files in output/. make sure output/github_url.txt will contain the final public repository URL.

when i authorize you to proceed, check the Git status and existing remote configuration first. do not overwrite an unrelated repository or push to an existing remote without checking what it is. if a GitHub repository needs to be created, explain what is required and use an available authenticated GitHub workflow if one is connected. if you cannot create or push the repository directly, tell me exactly what action i need to take and give me the correct commands.

before publishing, verify the expected file layout, check that no secrets or unnecessary generated files are included, and make sure the README is accurate. dont delete useful project work just to make the layout match the screenshot.

after i authorize the work and the repository is actually published, save the real public GitHub URL in output/github_url.txt. do not invent a URL or claim the repository is public until you have verified it.

for now, do not make any changes, run git push, create a repository, or publish anything. just wait for me to send the folder-layout screenshot and then my explicit instruction to begin."

- "go ahead"

## Ad hoc prompts

Prompts that don't fit neatly under a single numbered problem above.

- "We will not use portkey by the way, we'll use claude code so you can ignore that. Create a section in the AI_prompts.md for ad hoc prompts like this one."

- "We are building Campus Customs Multi-Agent Operations, a multi-agent AI system that manages the day-to-day operations of a campus shop. The goal is to build a working system in which AI agents collaborate to resolve operational tickets, update a shop database, and request human approval for actions that require it.

The system has five agents. The Boss agent reads incoming tickets, determines which agents should handle them, delegates tasks, coordinates their work, and makes final decisions. The Inventory agent checks stock by SKU, identifies shortages, and determines which vendors can restock products. The Accounting agent monitors cash, invoices, and margins, and prepares payments or purchase orders. The Facilities agent manages shop space, leases, and rent. The Customer Service agent drafts messages to customers. All agents can communicate with and delegate tasks to any other agent when they need help.

The application must include an MCP server that exposes the necessary tools to the agents, a FastAPI backend to manage the application and agent workflows, and a React dashboard where a human can monitor agent activity, review ticket progress, and approve payments before execution.

A file named `data.zip` has already been added to the project folder. Locate this file and unzip it to obtain the original shop database, expected at `data/campus_customs.db`. Inspect the existing project structure and database schema before making changes. Create a separate working copy named `data/campus_customs_new.db`, and configure both the MCP server and backend to use this working copy. Never modify the original database, as we need it to reset the system and rerun tests. Verify that the extracted database and working copy exist and contain the expected tables.

The database contains tables for tickets, inventory, pricing, vendors, leases, rent, cash accounts, payments, and invoices. Agents must use the actual database records and update the relevant tables as tickets are resolved. Follow these business rules strictly: use `desk.date_today` as the shop's current date when checking overdue items; use vendor lead times when estimating restocking; do not place orders with vendors that have outstanding unpaid invoices; require human approval before executing any payment; never allow cash balances to become negative; and update the relevant database tables whenever a payment is made. The assignment does not model revenue, so no new cash enters the system. All payments must therefore be covered by existing cash balances. Customer communications must remain drafts on the dashboard; do not send emails or contact real vendors.

We will develop this project incrementally. The final deliverable must be a working implementation submitted through a public GitHub repository."
