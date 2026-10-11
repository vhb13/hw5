import type { Draft } from '../types'

/**
 * Customer messages written by the Customer Service agent. They are saved as drafts only:
 * the system has no way to send them, so this panel is where a person reads and reviews them.
 */
export function DraftPanel({ drafts }: { drafts: Draft[] }) {
  return (
    <section className="panel" aria-label="Customer drafts">
      <h3>Customer draft</h3>
      {drafts.length === 0 ? (
        <p className="empty">No customer message has been drafted for this ticket.</p>
      ) : (
        drafts.map((d) => (
          <article className="draft" key={d.id}>
            <header>
              <b>{d.subject}</b>
              <span className="pill">Draft · not sent</span>
            </header>
            <p className="draft-body">{d.body}</p>
            <p className="muted">Draft #{d.id}. Nothing is emailed; a person must review and send it themselves.</p>
          </article>
        ))
      )}
    </section>
  )
}
