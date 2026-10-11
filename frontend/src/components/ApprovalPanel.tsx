import { useState } from 'react'
import { describePayment, money } from '../labels'
import type { PendingPayment } from '../types'

interface Props {
  payments: PendingPayment[]
  approver: string
  approvingId: number | null
  onApprove: (p: PendingPayment) => void
}

/** Money only moves after two clicks: Approve, then Confirm. */
export function ApprovalPanel({ payments, approver, approvingId, onApprove }: Props) {
  const [confirmId, setConfirmId] = useState<number | null>(null)
  if (payments.length === 0) return null
  const hasName = approver.trim().length > 0

  return (
    <section className="panel panel-alert" aria-label="Approval needed">
      <h3>
        <i className="mark mark-awaiting_approval" aria-hidden="true" /> Your approval is needed
      </h3>
      <p className="muted">
        The agents only prepared {payments.length === 1 ? 'this payment' : 'these payments'}. Nothing is paid until
        you approve.
      </p>
      <ul className="payments">
        {payments.map((p) => {
          const confirming = confirmId === p.id
          const busy = approvingId === p.id
          return (
            <li key={p.id} className="payment">
              <div>
                <strong>{describePayment(p)}</strong>
                <div className="muted">
                  {money(p.amount)} from the {p.account} account
                </div>
              </div>
              {confirming ? (
                <div className="confirm-inline" role="group" aria-label="Confirm payment">
                  <span>
                    Pay {money(p.amount)} as <b>{approver.trim()}</b>?
                  </span>
                  <button
                    className="btn btn-primary"
                    disabled={busy}
                    onClick={() => {
                      setConfirmId(null)
                      onApprove(p)
                    }}
                  >
                    Confirm payment
                  </button>
                  <button className="btn btn-quiet" onClick={() => setConfirmId(null)}>
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  className="btn btn-primary"
                  disabled={busy || !hasName}
                  onClick={() => setConfirmId(p.id)}
                  title={hasName ? undefined : 'Enter your name at the top of the page first'}
                >
                  {busy ? 'Paying…' : `Approve ${money(p.amount)}`}
                </button>
              )}
            </li>
          )
        })}
      </ul>
      {!hasName && <p className="hint">Enter your name under “Approving as” at the top to enable approval.</p>}
    </section>
  )
}
