import { STATUS_LABEL, TYPE_LABEL } from '../labels'
import type { Ticket } from '../types'

interface Props {
  tickets: Ticket[]
  selectedId: number | null
  runningId: number | null
  onSelect: (id: number) => void
}

/** The shape next to each status is a second cue, so colour is never the only signal. */
export function StatusMark({ status }: { status: string }) {
  return <i className={`mark mark-${status}`} aria-hidden="true" />
}

export function TicketList({ tickets, selectedId, runningId, onSelect }: Props) {
  return (
    <nav className="tickets" aria-label="Tickets">
      <h2 className="eyebrow">Tickets</h2>
      <ul>
        {tickets.map((t) => {
          const selected = t.id === selectedId
          return (
            <li key={t.id}>
              <button
                className={`ticket-card${selected ? ' selected' : ''}`}
                aria-current={selected ? 'true' : undefined}
                onClick={() => onSelect(t.id)}
              >
                <StatusMark status={t.status} />
                <span className="ticket-main">
                  <span className="ticket-id">Ticket {t.id}</span>
                  <span className="ticket-subject">{t.subject}</span>
                  <span className="ticket-meta">
                    {TYPE_LABEL[t.type] ?? t.type} · {t.requester}
                  </span>
                </span>
                <span className={`status-text status-${t.status}`}>
                  {runningId === t.id ? 'Running…' : STATUS_LABEL[t.status] ?? t.status}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
