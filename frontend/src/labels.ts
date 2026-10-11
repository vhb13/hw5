import type { PendingPayment, Step } from './types'

export const AGENTS = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service'] as const

export const AGENT_LABEL: Record<string, string> = {
  boss: 'Boss',
  inventory: 'Inventory',
  accounting: 'Accounting',
  facilities: 'Facilities',
  customer_service: 'Customer Service',
  human_approval: 'You',
  system: 'System',
}

export const AGENT_ROLE: Record<string, string> = {
  boss: 'Coordinates and decides',
  inventory: 'Stock and restocking',
  accounting: 'Cash, invoices, payments',
  facilities: 'Lease and rent',
  customer_service: 'Drafts customer replies',
}

export const STATUS_LABEL: Record<string, string> = {
  open: 'Open',
  awaiting_approval: 'Awaiting approval',
  needs_investigation: 'Needs investigation',
  resolved: 'Resolved',
}

export const OUTCOME_LABEL: Record<string, string> = {
  resolved: 'Resolved',
  needs_human_approval: 'Needs your approval',
  needs_investigation: 'Needs investigation',
}

export const TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price override',
}

const TOOL_PHRASE: Record<string, string> = {
  get_ticket: 'read the ticket',
  list_tickets: 'listed tickets',
  get_inventory_status: 'checked stock and prices',
  get_vendor_status: 'checked vendors and their invoices',
  estimate_restock: 'estimated a restock',
  get_facilities_status: 'checked the lease and today’s date',
  get_accounting_status: 'checked cash and invoices',
  propose_payment: 'prepared a payment for approval',
  save_customer_draft: 'saved a draft customer message',
  update_ticket_status: 'recorded the ticket outcome',
  execute_payment: 'paid an approved payment',
}

/** One plain-English phrase for an audit step, e.g. "checked stock and prices". */
export function describeStep(step: Step): string {
  if (step.tool === 'ask_specialist') {
    const who = /asked (\w+)/.exec(step.summary)?.[1]
    if (step.summary.startsWith('refused')) return 'tried to ask for help but was stopped by a rule'
    return who ? `asked ${AGENT_LABEL[who] ?? who} for help` : 'asked a colleague for help'
  }
  if (step.tool && TOOL_PHRASE[step.tool]) return TOOL_PHRASE[step.tool]
  if (step.tool) return `used ${step.tool}`
  if (step.status === 'finished') return 'finished its part'
  if (step.status === 'needs_human_approval') return 'finished: a payment needs approval'
  if (step.status === 'error') return 'hit an error'
  return step.summary
}

export function describePayment(p: PendingPayment): string {
  if (p.kind === 'invoice') return `Pay vendor invoice #${p.ref_id}`
  if (p.kind === 'rent') return `Pay rent for lease #${p.ref_id}`
  if (p.kind === 'purchase_order') return `Place a purchase order with vendor #${p.ref_id}`
  return `Payment (${p.kind})`
}

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
