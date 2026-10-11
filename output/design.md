# Dashboard design

The dashboard (`frontend/`, React + Vite + TypeScript) is meant to feel like a calm, well-organized operations desk. The style is muted Bauhaus: flat colour, thin charcoal rules, strong type and a few geometric shapes. There are no gradients, no icon library and no decoration that doesn't carry meaning.

## Visual direction

- **Colour.** Warm off-white page (`#f4efe6`), charcoal text (`#25262b`), muted navy (`#2d4a6b`) as the one main accent, terracotta (`#b5573b`) for problems and mustard (`#c9962b`) for "needs you". Navy marks what is normal or done. Terracotta and mustard only ever appear when something needs attention, so they stand out.
- **Type.** A geometric sans (Futura / Century Gothic, falling back to system fonts). Headings and labels are small, uppercase and letter-spaced. Numbers such as the balance are large and bold.
- **Shapes.** The logo is a navy circle, terracotta square and mustard triangle. The same three shapes come back as the ticket status marks, so the Bauhaus idea does real work instead of just decorating.
- **Surfaces.** Cards have 1px charcoal borders and square corners. The selected ticket gets a hard offset shadow, which is the only "depth" in the design.

## Layout

1. **Header.** Logo and name on the left. On the right, an "Approving as" name field (recorded with each payment) and a quiet "Reset test data" button.
2. **Summary band.** One row: the checking balance (navy, the largest number on the page), then counts of Open, Awaiting approval, Needs investigation and Resolved tickets. The balance also says how much is reserved for pending payments.
3. **Ticket list (left).** Tickets 101, 102 and 103 as cards: id, subject, type and requester, and a status.
4. **Workspace (right).** For the selected ticket, top to bottom: the ticket and a **Next step** line, the big **Run agent team** button, the **approval panel** (only when a payment is pending), the **agent team and activity**, and **what each agent did**.

On screens under 960px the ticket list moves above the workspace, and the five agent boxes and summary cells reflow into fewer columns. At 390px wide there is no sideways scrolling.

## Easy to follow without hunting

- **A "Next step" sentence** sits above the buttons and changes with the ticket: "run the agent team", "review the payment below", "mark resolved", "Done". The most important button is always the large navy one.
- **Agent activity is live.** While a ticket runs, the page polls the backend every second. Five boxes (Boss, Inventory, Accounting, Facilities, Customer Service) show Waiting / Working / Done / Not needed, and the agent that acted most recently gets a mustard underline and a gently pulsing dot. Below them a plain-English feed lists each step ("Inventory checked stock and prices", "Inventory asked Accounting for help"). Agents the Boss didn't need are labelled "Not needed", which makes it clear the Boss doesn't call everyone.
- **Summaries are short.** "What each agent did" shows the Boss decision first (outcome, key facts, anything still open), then one card per agent with its summary, recommendation and the tools it used. An agent that was asked several times shows only its latest answer.
- **Drafts can be read.** A "Customer draft" panel shows the actual message the Customer Service agent wrote, labelled "Draft · not sent", because nothing in the system sends it and a person has to review it.
- **Money needs two clicks.** "Approve $840.00" turns into "Pay $840.00 as Vy? Confirm payment". The balance refreshes straight after, a short navy-to-mustard flash draws the eye to it, and a notice shows "$3,400.00 → $2,560.00".

## Status is never colour alone

Each ticket status has a shape and a word: hollow navy circle + "Open", mustard square + "Awaiting approval", terracotta triangle + "Needs investigation", filled navy circle + "Resolved". Agent states are words with a dot. Errors say what went wrong in a sentence, and focus rings are visible for keyboard use.

## Resolved tickets

A ticket is shown as Resolved only when the backend says so. This happens when the Boss decides the ticket is resolved, or when a person clicks **Mark resolved**. That button appears once nothing is waiting on a payment, and the backend refuses it while a payment is pending. The summary count and the ticket card update together. A resolved ticket's run button is disabled and its next step says "Done".

## Loading, empty and error states

A spinner while tickets load. A full-page message with a "Try again" button if the backend can't be reached (it says which address and how to start it). A "No tickets" message with a hint to reset. Failed runs, approvals and resets show a plain sentence in a terracotta notice. Animations are limited to the spinner, the pulsing dot and the balance flash, and all are turned off when the user prefers reduced motion.

## Why it should feel distinctive but still obvious

The look comes from a few strong choices (one navy accent, thin rules, three recurring shapes, big numbers) rather than many effects, so the page is memorable without being busy. The structure is deliberately ordinary: summary on top, a list on the left, the work on the right, one primary action per state. A first-time user should be able to read the Next step line, press the large button, and watch the agents work.
