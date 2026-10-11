import { AGENT_LABEL, OUTCOME_LABEL } from '../labels'
import type { AgentMessage } from '../types'

const text = (v: unknown): string => (typeof v === 'string' ? v : '')
const list = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [])

const toolTag = (t: string) => t.replace('ask_specialist -> ', 'asked ')

/** Boss decision first, then what each specialist reported. */
export function Summaries({ messages, paymentPending }: { messages: AgentMessage[]; paymentPending: boolean }) {
  if (messages.length === 0) return null
  const boss = [...messages].reverse().find((m) => m.agent === 'boss')
  // An agent can be asked several times in one run (by the Boss and by colleagues).
  // Show one card per agent: its latest report, with every tool it used.
  const byAgent = new Map<string, AgentMessage[]>()
  for (const m of messages.filter((m) => m.agent !== 'boss')) byAgent.set(m.agent, [...(byAgent.get(m.agent) ?? []), m])
  const others = [...byAgent.values()].map((ms) => ({
    last: ms[ms.length - 1],
    asked: ms.length,
    approval: ms.some((m) => m.status === 'needs_human_approval'),
    tools: [...new Set(ms.flatMap((m) => m.tools_used))],
  }))

  return (
    <section className="panel" aria-label="What each agent did">
      <h3>What each agent did</h3>

      {boss && (
        <article className="summary-card boss-card">
          <header>
            <b>Boss decision</b>
            <span className={`pill pill-${text(boss.said.outcome)}`}>
              {text(boss.said.outcome) === 'needs_human_approval' && !paymentPending
                ? 'Needs a human decision'
                : OUTCOME_LABEL[text(boss.said.outcome)] ?? text(boss.said.outcome)}
            </span>
          </header>
          <p>{text(boss.said.summary)}</p>
          {list(boss.said.key_facts).length > 0 && (
            <ul>
              {list(boss.said.key_facts).map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          )}
          {list(boss.said.contradictions_or_gaps).length > 0 && (
            <div className="gaps">
              <b>Still open:</b>
              <ul>
                {list(boss.said.contradictions_or_gaps).map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}
        </article>
      )}

      <div className="summary-grid">
        {others.map(({ last: m, asked, approval, tools }) => (
          <article className="summary-card" key={m.agent}>
            <header>
              <b>{AGENT_LABEL[m.agent] ?? m.agent}</b>
              <span className="pill">{approval ? 'Prepared a payment' : 'Finished'}</span>
            </header>
            <p>{text(m.said.summary)}</p>
            {text(m.said.recommendation) && (
              <p className="muted">
                <b>Recommends:</b> {text(m.said.recommendation)}
              </p>
            )}
            {asked > 1 && <p className="muted">Asked {asked} times during this run; showing the latest answer.</p>}
            {tools.length > 0 && (
              <div className="tags" aria-label="Tools used">
                {tools.map((t) => (
                  <span className="tag" key={t}>
                    {toolTag(t)}
                  </span>
                ))}
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
