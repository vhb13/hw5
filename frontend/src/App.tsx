import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ApiError, api } from './api'
import { Header } from './components/Header'
import { SummaryBar } from './components/SummaryBar'
import { TicketList } from './components/TicketList'
import { Workspace } from './components/Workspace'
import { runView } from './derive'
import { OUTCOME_LABEL, money } from './labels'
import type { Activity, Cash, Draft, PendingPayment, Ticket } from './types'

type Notice = { kind: 'success' | 'error' | 'info'; text: string }

const errorText = (e: unknown) => (e instanceof ApiError ? e.message : 'Something went wrong. Please try again.')

export default function App() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null)
  const [cash, setCash] = useState<Cash | null>(null)
  const [activity, setActivity] = useState<Activity | null>(null)
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [run, setRun] = useState<{ ticketId: number; startedAt: number } | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [approver, setApprover] = useState(() => localStorage.getItem('approver') ?? '')
  const [approvingId, setApprovingId] = useState<number | null>(null)
  const [resolving, setResolving] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [flash, setFlash] = useState(false)
  const flashTimer = useRef<number | undefined>(undefined)

  const refresh = useCallback(async () => {
    try {
      const [t, c, a, d] = await Promise.all([api.tickets(), api.cash(), api.activity(), api.drafts()])
      setTickets(t)
      setCash(c)
      setActivity(a)
      setDrafts(d)
      setLoadError(null)
      setSelectedId((cur) => cur ?? t[0]?.id ?? null)
    } catch (e) {
      setLoadError(errorText(e))
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  // Follow the agents: poll the activity feed every second during a run, every few seconds otherwise
  // (so a run started elsewhere, or before a page reload, still shows up).
  useEffect(() => {
    const id = window.setInterval(
      async () => {
        try {
          setActivity(await api.activity())
        } catch {
          /* the next refresh will report it */
        }
      },
      run ? 1000 : 4000,
    )
    return () => window.clearInterval(id)
  }, [run])

  useEffect(() => () => window.clearTimeout(flashTimer.current), [])

  const changeApprover = (v: string) => {
    setApprover(v)
    localStorage.setItem('approver', v)
  }

  const selected = tickets?.find((t) => t.id === selectedId) ?? null
  const runStartedAt = run && selected && run.ticketId === selected.id ? run.startedAt : null
  const view = useMemo(
    () => (selected ? runView(activity, selected.id, runStartedAt) : { steps: [], messages: [], hasRun: false }),
    [activity, selected, runStartedAt],
  )

  const startRun = async (ticketId: number) => {
    setNotice(null)
    setRun({ ticketId, startedAt: Date.now() })
    try {
      const result = await api.runTicket(ticketId)
      setNotice({
        kind: 'success',
        text: `Ticket ${ticketId}: the team finished. Outcome: ${OUTCOME_LABEL[result.outcome] ?? result.outcome}.`,
      })
    } catch (e) {
      setNotice({ kind: 'error', text: `Ticket ${ticketId} could not be run. ${errorText(e)}` })
    } finally {
      setRun(null)
      await refresh()
    }
  }

  const approve = async (p: PendingPayment) => {
    setNotice(null)
    setApprovingId(p.id)
    const before = cash?.balance
    try {
      const r = await api.approve(p.id, approver.trim())
      setNotice({
        kind: 'success',
        text: `Payment approved: ${money(r.amount)} paid. Checking balance ${
          before !== undefined ? `${money(before)} → ` : ''
        }${money(r.new_balance)}.`,
      })
      setFlash(true)
      flashTimer.current = window.setTimeout(() => setFlash(false), 1600)
    } catch (e) {
      setNotice({ kind: 'error', text: `Payment was not made. ${errorText(e)}` })
    } finally {
      setApprovingId(null)
      await refresh()
    }
  }

  const resolve = async (ticketId: number) => {
    setNotice(null)
    setResolving(true)
    try {
      await api.resolve(ticketId)
      setNotice({ kind: 'success', text: `Ticket ${ticketId} marked resolved.` })
    } catch (e) {
      setNotice({ kind: 'error', text: `Could not mark it resolved. ${errorText(e)}` })
    } finally {
      setResolving(false)
      await refresh()
    }
  }

  const reset = async () => {
    setNotice(null)
    setResetting(true)
    try {
      await api.reset()
      setNotice({ kind: 'info', text: 'Test data reset. Tickets and cash are back to the start.' })
    } catch (e) {
      setNotice({ kind: 'error', text: `Reset failed. ${errorText(e)}` })
    } finally {
      setResetting(false)
      await refresh()
    }
  }

  return (
    <>
      <Header
        approver={approver}
        onApprover={changeApprover}
        onReset={reset}
        resetting={resetting}
        disabled={run !== null}
        date={cash?.as_of ?? null}
      />

      <div className="page">
        <SummaryBar cash={cash} tickets={tickets} flash={flash} />

        {notice && (
          <div className={`notice notice-${notice.kind}`} role={notice.kind === 'error' ? 'alert' : 'status'}>
            <span>{notice.text}</span>
            <button className="btn btn-quiet" onClick={() => setNotice(null)} aria-label="Dismiss message">
              Dismiss
            </button>
          </div>
        )}

        {loadError && !tickets ? (
          <div className="state-box" role="alert">
            <h2>The dashboard can’t load</h2>
            <p>{loadError}</p>
            <p className="muted">Start the backend, then try again: uvicorn main:app --port 8000 (from the backend folder).</p>
            <button className="btn btn-primary" onClick={() => void refresh()}>
              Try again
            </button>
          </div>
        ) : !tickets ? (
          <div className="state-box" role="status">
            <span className="spinner spinner-dark" aria-hidden="true" /> Loading tickets…
          </div>
        ) : tickets.length === 0 ? (
          <div className="state-box">
            <h2>No tickets</h2>
            <p className="muted">There are no tickets in the database. Use “Reset test data” to restore them.</p>
          </div>
        ) : (
          <div className="layout">
            {loadError && (
              <div className="notice notice-error layout-wide" role="alert">
                <span>Connection problem: {loadError}</span>
                <button className="btn btn-quiet" onClick={() => void refresh()}>
                  Retry
                </button>
              </div>
            )}
            <TicketList
              tickets={tickets}
              selectedId={selectedId}
              runningId={run?.ticketId ?? null}
              onSelect={setSelectedId}
            />
            {selected && (
              <Workspace
                key={selected.id}
                ticket={selected}
                view={view}
                drafts={drafts.filter((d) => d.ticket_id === selected.id)}
                running={run?.ticketId === selected.id}
                anotherRunning={run !== null && run.ticketId !== selected.id}
                approver={approver}
                approvingId={approvingId}
                resolving={resolving}
                onRun={() => void startRun(selected.id)}
                onApprove={(p) => void approve(p)}
                onResolve={() => void resolve(selected.id)}
              />
            )}
          </div>
        )}
      </div>
    </>
  )
}
