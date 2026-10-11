// Drives the REAL React dashboard (http://localhost:5173) in Edge, one step per command.
//   node drive.mjs run <ticketId> [shotName]       click "Run agent team", wait for it, screenshot
//   node drive.mjs approve <ticketId> <proposalId> click Approve then Confirm on that payment
//   node drive.mjs resolve <ticketId> [shotName]   click "Mark resolved", screenshot
//   node drive.mjs shot <ticketId> <shotName>      screenshot with that ticket selected
// Screenshots go to ../output/screenshots/. Nothing here touches the database directly:
// every change happens through the dashboard buttons and the backend routes behind them.
import { chromium } from 'playwright-core'
import { mkdirSync } from 'node:fs'

const [cmd, ...args] = process.argv.slice(2)
const URL = 'http://localhost:5173'
const API = 'http://localhost:8000'
const APPROVER = 'Claude (acting for Vy)'
const SHOTS = '../output/screenshots'
mkdirSync(SHOTS, { recursive: true })

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
await page.goto(URL)
await page.waitForSelector('.ticket-card')
await page.getByPlaceholder('Your name').fill(APPROVER)

const select = async (id) => {
  await page.locator('.ticket-card', { hasText: `Ticket ${id}` }).click()
  await page.waitForSelector(`main[aria-label="Ticket ${id}"]`)
}
const shot = async (name) => {
  await page.waitForTimeout(600) // let polling settle
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true })
  console.log(`screenshot: output/screenshots/${name}.png`)
}
const get = async (path) => (await fetch(API + path)).json()
const status = async () => {
  const t = await get('/tickets')
  const c = await get('/cash')
  console.log('tickets:', t.map((x) => `${x.id}=${x.status}${x.pending_payments.length ? ` (pending ${x.pending_payments.map((p) => `#${p.id} ${p.kind} ${p.ref_id} $${p.amount}`).join(', ')})` : ''}`).join(' | '))
  console.log(`checking balance: $${c.balance} (reserved $${c.pending_proposed}, free $${c.available})`)
}

if (cmd === 'run') {
  const [id, name] = args
  await select(id)
  const t0 = Date.now()
  await page.getByRole('button', { name: /Run agent team/ }).click()
  await page.getByText('Agents working…').waitFor({ timeout: 10000 })
  const notice = page.locator('.notice-success, .notice-error').first()
  await notice.waitFor({ timeout: 280000 })
  console.log(`run finished in ${Math.round((Date.now() - t0) / 1000)}s. Notice: ${(await notice.innerText()).split('\n')[0]}`)
  await status()
  if (name) await shot(name)
} else if (cmd === 'approve') {
  const [id, proposalId] = args
  await select(id)
  const c = await get('/cash')
  const p = c.pending_proposals.find((x) => String(x.id) === proposalId)
  if (!p) throw new Error(`proposal ${proposalId} is not pending`)
  const amount = p.amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
  const row = page.locator('.payment', { hasText: amount })
  await row.getByRole('button', { name: new RegExp(`^Approve ${amount.replace('$', '\\$')}`) }).click()
  await row.getByRole('button', { name: 'Confirm payment' }).click()
  const notice = page.locator('.notice-success, .notice-error').first()
  await notice.waitFor({ timeout: 20000 })
  console.log('notice:', (await notice.innerText()).split('\n')[0])
  await status()
} else if (cmd === 'resolve') {
  const [id, name] = args
  await select(id)
  await page.getByRole('button', { name: 'Mark resolved' }).click()
  await page.waitForFunction((i) => [...document.querySelectorAll('.ticket-card')].some((c) => c.textContent.includes(`Ticket ${i}`) && c.textContent.includes('Resolved')), id, { timeout: 15000 })
  await status()
  if (name) await shot(name)
} else if (cmd === 'shot') {
  const [id, name] = args
  await select(id)
  await shot(name)
} else {
  console.log('unknown command')
}
await browser.close()
