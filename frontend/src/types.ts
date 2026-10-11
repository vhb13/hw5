// Shapes returned by the FastAPI backend (backend/main.py). No sample data lives in the frontend.

export interface PendingPayment {
  id: number
  kind: string
  ref_id: number
  amount: number
  account: string
  ticket_id: number | null
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  notes: string | null
  created_at: string
  resolved: boolean
  pending_payments: PendingPayment[]
}

export interface Cash {
  account: string
  balance: number
  pending_proposed: number
  available: number
  as_of: string
  pending_proposals: PendingPayment[]
}

export interface Step {
  time: string
  ticket_id: number
  agent: string
  tool: string | null
  summary: string
  status: string
}

export interface AgentMessage {
  time: string
  ticket_id: number
  agent: string
  status: string
  said: Record<string, unknown>
  tools_used: string[]
}

export interface Activity {
  running: boolean
  steps: Step[]
  messages: AgentMessage[]
}

export interface ApproveResult {
  payment_id: number
  proposal_id: number
  kind: string
  amount: number
  new_balance: number
}

export interface Draft {
  id: number
  ticket_id: number
  subject: string
  body: string
  status: string
  created_at: string
  sent: boolean
}
