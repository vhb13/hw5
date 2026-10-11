import type { RunView } from '../derive'
import { STATUS_LABEL, TYPE_LABEL } from '../labels'
import type { Draft, PendingPayment, Ticket } from '../types'
import { AgentTeam } from './AgentTeam'
import { ApprovalPanel } from './ApprovalPanel'
import { StatusMark } from './TicketList'
import { DraftPanel } from './DraftPanel'
import { Summaries } from './Summaries'

interface Props {
  ticket: Ticket
  view: RunView
  drafts: Draft[]
  running: boolean // this ticket is running now
  anotherRunning: boolean // a different ticket is running
  approver: string
  approvingId: number | null
  resolving: boolean
  onRun: () => void
  onApprove: (p: PendingPayment) => void
  onResolve: () => void
}

function nextStep(t: Ticket, running: boolean, anotherRunning: boolean): string {
  if (t.resolved) return 'Done. This ticket is resolved.'
  if (running) return 'The agent team is working on this ticket. Follow along in the activity feed below.'
  if (anotherRunning) return 'Another ticket is running. Wait for it to finish, then run this one.'
  if (t.pending_payments.length > 0) return 'Next: review the payment below and approve it if it looks right.'
  if (t.status === 'open') return 'Next: run the agent team on this ticket.'
  if (t.status === 'awaiting_approval')
    return 'No payment is waiting on you now. Read the Boss’s notes below, then mark this ticket resolved if nothing else is needed, or run it again.'
  return 'The team could not finish this on its own. Read the Boss’s notes below, then run it again or mark it resolved.'
}

function requestLine(t: Ticket): string {
  const parts: string[] = []
  if (t.qty && t.sku) parts.push(`${t.qty} × ${t.sku}${t.size ? `, size ${t.size}` : ''}`)
  if (t.invoice_id) parts.push(`invoice #${t.invoice_id}`)
  if (t.lease_id) parts.push(`lease #${t.lease_id}`)
  return parts.join(' · ')
}

export function Workspace(p: Props) {
  const { ticket: t } = p
  const canRun = !t.resolved && !p.running && !p.anotherRunning
  const canResolve = !t.resolved && t.status !== 'open' && t.pending_payments.length === 0 && !p.running

  return (
    <main className="workspace" aria-label={`Ticket ${t.id}`}>
      <section className="panel ticket-head">
        <div className="ticket-title">
          <StatusMark status={t.status} />
          <div>
            <span className="eyebrow">
              Ticket {t.id} · {TYPE_LABEL[t.type] ?? t.type}
            </span>
            <h2>{t.subject}</h2>
          </div>
          <span className={`status-text status-${t.status}`}>{STATUS_LABEL[t.status] ?? t.status}</span>
        </div>
        <dl className="facts">
          <dt>From</dt>
          <dd>{t.requester}</dd>
          {requestLine(t) && (
            <>
              <dt>Details</dt>
              <dd>{requestLine(t)}</dd>
            </>
          )}
          {t.notes && (
            <>
              <dt>Notes</dt>
              <dd className="notes">{t.notes}</dd>
            </>
          )}
        </dl>

        <div className="next-step" role="status">
          <i className="next-arrow" aria-hidden="true" />
          <span>{nextStep(t, p.running, p.anotherRunning)}</span>
        </div>

        <div className="actions">
          <button className="btn btn-primary btn-large" disabled={!canRun} onClick={p.onRun}>
            {p.running ? (
              <>
                <span className="spinner" aria-hidden="true" /> Agents working…
              </>
            ) : t.status === 'open' ? (
              'Run agent team'
            ) : (
              'Run agent team again'
            )}
          </button>
          {canResolve && (
            <button className="btn btn-secondary" disabled={p.resolving} onClick={p.onResolve}>
              {p.resolving ? 'Saving…' : 'Mark resolved'}
            </button>
          )}
        </div>
      </section>

      <ApprovalPanel
        payments={t.pending_payments}
        approver={p.approver}
        approvingId={p.approvingId}
        onApprove={p.onApprove}
      />

      <DraftPanel drafts={p.drafts} />

      <AgentTeam view={p.view} running={p.running} />
      <Summaries messages={p.view.messages} paymentPending={t.pending_payments.length > 0} />
    </main>
  )
}
