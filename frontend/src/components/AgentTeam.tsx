import { AGENTS, AGENT_LABEL, AGENT_ROLE, describeStep } from '../labels'
import type { AgentState, RunView } from '../derive'
import { agentStates } from '../derive'

const STATE_TEXT: Record<AgentState, string> = {
  waiting: 'Waiting',
  working: 'Working',
  done: 'Done',
  not_needed: 'Not needed',
  error: 'Error',
}

const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

interface Props {
  view: RunView
  running: boolean
}

export function AgentTeam({ view, running }: Props) {
  const states = agentStates(view, running)
  const latest = view.steps[view.steps.length - 1]

  return (
    <section className="panel" aria-label="Agent team">
      <h3>Agent team</h3>
      <ul className="agents">
        {AGENTS.map((a) => {
          const mine = view.steps.filter((s) => s.agent === a)
          const last = mine[mine.length - 1]
          const state = states[a]
          const isNow = running && latest?.agent === a
          return (
            <li key={a} className={`agent agent-${state}${isNow ? ' now' : ''}`}>
              <span className="agent-name">{AGENT_LABEL[a]}</span>
              <span className="agent-role">{AGENT_ROLE[a]}</span>
              <span className="agent-state">
                <i className="agent-dot" aria-hidden="true" />
                {STATE_TEXT[state]}
              </span>
              {last && <span className="agent-last">Last: {describeStep(last)}</span>}
            </li>
          )
        })}
      </ul>

      <h4>Activity</h4>
      {view.steps.length === 0 ? (
        <p className="empty">{running ? 'Starting up… the first step appears in a moment.' : 'No activity yet for this ticket.'}</p>
      ) : (
        <ol className="feed" aria-live="polite">
          {view.steps.map((s, i) => (
            <li key={`${s.time}-${i}`} className={s.status === 'error' ? 'feed-error' : undefined}>
              <time>{time(s.time)}</time>
              <b>{AGENT_LABEL[s.agent] ?? s.agent}</b> {describeStep(s)}
            </li>
          ))}
          {running && <li className="feed-live">Working…</li>}
        </ol>
      )}
    </section>
  )
}
