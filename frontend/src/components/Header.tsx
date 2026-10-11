import { useState } from 'react'

interface Props {
  approver: string
  onApprover: (v: string) => void
  onReset: () => void
  resetting: boolean
  disabled: boolean
  date: string | null
}

export function Header({ approver, onApprover, onReset, resetting, disabled, date }: Props) {
  const [confirming, setConfirming] = useState(false)

  return (
    <header className="header">
      <div className="brand">
        <span className="logo" aria-hidden="true">
          <i className="logo-circle" />
          <i className="logo-square" />
          <i className="logo-triangle" />
        </span>
        <div>
          <h1>Campus Customs</h1>
          <p className="brand-sub">Operations desk{date ? ` · shop date ${date}` : ''}</p>
        </div>
      </div>

      <div className="header-tools">
        <label className="approver">
          <span>Approving as</span>
          <input
            value={approver}
            onChange={(e) => onApprover(e.target.value)}
            placeholder="Your name"
            maxLength={80}
            aria-describedby="approver-hint"
          />
        </label>
        <span id="approver-hint" className="sr-only">
          Your name is recorded with every payment you approve.
        </span>

        {confirming ? (
          <span className="confirm-inline" role="group" aria-label="Confirm reset">
            <span>Reset all tickets and cash to the start?</span>
            <button
              className="btn btn-danger"
              disabled={resetting}
              onClick={() => {
                setConfirming(false)
                onReset()
              }}
            >
              Yes, reset
            </button>
            <button className="btn btn-quiet" onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </span>
        ) : (
          <button
            className="btn btn-quiet"
            disabled={disabled || resetting}
            onClick={() => setConfirming(true)}
            title="Restores the working database from the original, so tickets can be tested again"
          >
            {resetting ? 'Resetting…' : 'Reset test data'}
          </button>
        )}
      </div>
    </header>
  )
}
