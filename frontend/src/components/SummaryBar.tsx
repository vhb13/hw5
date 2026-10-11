import { STATUS_LABEL, money } from '../labels'
import type { Cash, Ticket } from '../types'

interface Props {
  cash: Cash | null
  tickets: Ticket[] | null
  flash: boolean // balance just changed
}

export function SummaryBar({ cash, tickets, flash }: Props) {
  const count = (status: string) => (tickets ? tickets.filter((t) => t.status === status).length : null)

  return (
    <section className="summary" aria-label="Summary">
      <div className={`summary-cell summary-balance${flash ? ' flash' : ''}`}>
        <span className="eyebrow">Checking balance</span>
        <strong className="big" data-testid="balance">
          {cash ? money(cash.balance) : '…'}
        </strong>
        <span className="muted">
          {cash
            ? cash.pending_proposed > 0
              ? `${money(cash.pending_proposed)} reserved for pending payments · ${money(cash.available)} free`
              : 'Nothing reserved for pending payments'
            : 'Loading'}
        </span>
      </div>

      {(['open', 'awaiting_approval', 'needs_investigation', 'resolved'] as const).map((s) => (
        <div className="summary-cell" key={s}>
          <span className="eyebrow">{STATUS_LABEL[s]}</span>
          <strong className="big">{count(s) ?? '…'}</strong>
          <span className="muted">{count(s) === 1 ? 'ticket' : 'tickets'}</span>
        </div>
      ))}
    </section>
  )
}
