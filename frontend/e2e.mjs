// End-to-end test of the dashboard in a real browser (Edge) against the real backend.
// Needs: backend on :8000, `npm run dev` on :5173.   Run: node e2e.mjs
// Uses live agents (gpt-6-luna via Portkey) for three ticket runs, and ends with a UI reset.
import { chromium } from 'playwright-core'
import { mkdirSync } from 'node:fs'

const URL = 'http://localhost:5173'
const SHOTS = process.env.SHOTS ?? './e2e-shots'
mkdirSync(SHOTS, { recursive: true })

const results = []
const check = (name, ok, detail = '') => {
  results.push(ok)
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? `  [${detail}]` : ''}`)
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
const consoleErrors = []
page.on('console', (m) => m.type() === 'error' && consoleErrors.push(m.text()))
page.on('pageerror', (e) => consoleErrors.push(String(e)))

const text = (sel) => page.locator(sel).first().innerText()
const balance = async () => (await text('[data-testid=balance]')).trim()
const card = (id) => page.locator('.ticket-card', { hasText: `Ticket ${id}` })

// Start clean through the real API.
await fetch('http://localhost:8000/reset', { method: 'POST' })

// ---- 1. loading ----
await page.goto(URL)
await page.waitForSelector('.ticket-card')
check('three tickets listed', (await page.locator('.ticket-card').count()) === 3)
check('every ticket shows status text "Open"', (await page.locator('.ticket-card .status-open').count()) === 3)
check('balance loaded from backend: $3,400.00', (await balance()) === '$3,400.00', await balance())
check('first ticket selected, next step says run the team',
  (await text('.next-step')).includes('run the agent team'))
check('run button is obvious', await page.getByRole('button', { name: 'Run agent team' }).isEnabled())
await page.screenshot({ path: `${SHOTS}/1-loaded.png`, fullPage: true })

// ---- 2. run ticket 101 and watch it ----
await page.getByPlaceholder('Your name').fill('Vy')
await page.getByRole('button', { name: 'Run agent team' }).click()
await page.getByText('Agents working…').waitFor({ timeout: 5000 })
check('button switches to "Agents working…" and the card says Running', (await card(101).textContent()).includes('Running'))
await page.waitForSelector('.feed li:not(.feed-live)', { timeout: 60000 })
const seenWorking = await page.locator('.agent-working').count()
check('live activity feed shows steps during the run', (await page.locator('.feed li').count()) >= 2)
check('an agent is shown as Working during the run', seenWorking >= 1, `${seenWorking} working`)
await page.screenshot({ path: `${SHOTS}/2-running.png`, fullPage: true })
await page.waitForSelector('.notice-success', { timeout: 240000 })
check('notice reports the finished run', (await text('.notice')).includes('Needs your approval'), await text('.notice'))
check('ticket 101 now Awaiting approval (text)', (await card(101).textContent()).includes('Awaiting approval'))
check('approval panel shows the $840 invoice payment', (await text('[aria-label="Approval needed"]')).includes('$840.00'))
check('boss decision card present', (await page.locator('.boss-card').count()) === 1)
check('one summary card per agent that took part (no duplicates)', await page.evaluate(() => { const n = [...document.querySelectorAll('.summary-card:not(.boss-card) header b')].map((e) => e.textContent); return n.length >= 2 && new Set(n).size === n.length }))
check('summary cards list tools used', (await page.locator('.summary-card .tag').count()) >= 2)
check('customer name not shown in agent summaries', !(await text('[aria-label="What each agent did"]')).includes('Zaman'))
check('balance unchanged until approval', (await balance()) === '$3,400.00')
await page.screenshot({ path: `${SHOTS}/3-awaiting-approval.png`, fullPage: true })

// ---- 3. approve (two clicks) ----
await page.getByRole('button', { name: /^Approve \$840/ }).click()
check('approval asks for confirmation first', await page.getByRole('button', { name: 'Confirm payment' }).isVisible())
check('balance still unchanged before confirming', (await balance()) === '$3,400.00')
await page.getByRole('button', { name: 'Confirm payment' }).click()
await page.waitForFunction(() => document.querySelector('[data-testid=balance]')?.textContent === '$2,560.00', null, { timeout: 15000 })
check('balance refreshed to $2,560.00 after approval', (await balance()) === '$2,560.00')
check('success notice shows old and new balance', (await text('.notice')).includes('$3,400.00 → $2,560.00'), await text('.notice'))
check('approval panel gone after payment', (await page.locator('[aria-label="Approval needed"]').count()) === 0)

// ---- 4. mark resolved ----
await page.getByRole('button', { name: 'Mark resolved' }).click()
await page.waitForFunction(() => document.querySelector('.ticket-card .status-resolved'), null, { timeout: 15000 })
check('ticket 101 shows Resolved (text)', (await card(101).textContent()).includes('Resolved'))
check('run button disabled and next step says done for a resolved ticket',
  (await page.getByRole('button', { name: /Run agent team/ }).isDisabled()) && (await text('.next-step')).includes('Done'))

// ---- 5. ticket 102: run, approve rent ----
await card(102).click()
await page.getByRole('button', { name: 'Run agent team' }).click()
await page.waitForSelector('.notice-success', { timeout: 240000 })
check('ticket 102 asks for the $2,400 rent approval', (await text('[aria-label="Approval needed"]')).includes('$2,400.00'))
const idle = await page.locator('.agent-not_needed').count()
check('agents not needed are labelled "Not needed" (Boss did not call everyone)', idle >= 2, `${idle} not needed`)
await page.getByRole('button', { name: /^Approve \$2,400/ }).click()
await page.getByRole('button', { name: 'Confirm payment' }).click()
await page.waitForFunction(() => document.querySelector('[data-testid=balance]')?.textContent === '$160.00', null, { timeout: 15000 })
check('balance refreshed to $160.00', (await balance()) === '$160.00')
await page.getByRole('button', { name: 'Mark resolved' }).click()
await page.waitForFunction(() => document.querySelectorAll('.ticket-card .status-resolved').length === 2, null, { timeout: 15000 })
check('two tickets resolved', true)

// ---- 6. ticket 103: the agents' outcome varies run to run, so test the dashboard, not the model ----
await card(103).click()
await page.getByRole('button', { name: 'Run agent team' }).click()
await page.waitForSelector('.notice-success', { timeout: 240000 })
const t103 = await card(103).textContent()
check('ticket 103 left "Open" and shows a status in text', !t103.includes('Open') && /Awaiting approval|Needs investigation|Resolved/.test(t103), t103.slice(-24))
check('no approval panel for 103 (no payment proposed)', (await page.locator('[aria-label="Approval needed"]').count()) === 0)
check('next-step text never claims a payment was approved when none exists', !(await text('.next-step')).includes('Payment approved'))
await page.screenshot({ path: `${SHOTS}/4-ticket-103.png`, fullPage: true })
const sum = (await page.locator('.summary').textContent()).replace(/\s+/g, ' ')
check('summary counts: 0 open, 2 resolved', sum.includes('Open0') && sum.includes('Resolved2'), sum)

// ---- 7. reset from the UI ----
await page.getByRole('button', { name: 'Reset test data' }).click()
await page.getByRole('button', { name: 'Yes, reset' }).click()
await page.waitForFunction(() => document.querySelector('[data-testid=balance]')?.textContent === '$3,400.00', null, { timeout: 15000 })
check('reset restores balance and all tickets Open', (await page.locator('.ticket-card .status-open').count()) === 3)
await card(101).click()
check('after reset the old run is not shown for ticket 101', (await page.locator('.summary-card').count()) === 0)

// ---- 8. error + empty states ----
await page.route('**/tickets', (r) => r.abort())
await page.reload()
await page.getByRole('alert').first().waitFor()
check('load error state explains the problem and offers Try again',
  (await page.getByText('Can’t reach the backend', { exact: false }).count()) + (await page.getByText("Can't reach the backend").count()) >= 1 &&
  (await page.getByRole('button', { name: 'Try again' }).count()) === 1)
await page.screenshot({ path: `${SHOTS}/5-error.png` })
await page.unroute('**/tickets')
await page.getByRole('button', { name: 'Try again' }).click()
await page.waitForSelector('.ticket-card')
check('Try again recovers', (await page.locator('.ticket-card').count()) === 3)

// ---- 9. small screen ----
await page.setViewportSize({ width: 390, height: 800 })
await page.reload()
await page.waitForSelector('.ticket-card')
const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
check('no horizontal scrolling at 390px wide', overflow <= 1, `overflow ${overflow}px`)
check('run button still reachable on a phone', await page.getByRole('button', { name: 'Run agent team' }).isVisible())
await page.screenshot({ path: `${SHOTS}/6-mobile.png`, fullPage: true })

check('no browser console errors', consoleErrors.filter((e) => !/Failed to load resource|ERR_FAILED|net::/.test(e)).length === 0,
  consoleErrors.slice(0, 2).join(' | '))

await browser.close()
console.log(`\n${results.filter(Boolean).length}/${results.length} passed`)
process.exit(results.every(Boolean) ? 0 : 1)
